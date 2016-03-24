import os
import datetime
from flask import url_for
from flask import abort
from flask.ext.security import current_user
from application import app
from application import db
from application import imgur_client
from application import cache
from application.helpers import pretty_date
from application.helpers import computed_user_roles
from application.helpers.sorting import hot
from application.helpers.sorting import confidence


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(6))
    user_id = db.Column(db.Integer(),db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(
        db.Integer(),db.ForeignKey('category.id'), nullable=False)
    post_type_id = db.Column(
        db.Integer(), db.ForeignKey('post_type.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    picture = db.Column(db.String(80))
    picture_deletehash = db.Column(db.String(80))
    creation_date = db.Column(db.DateTime(), default=datetime.datetime.now)
    edit_date = db.Column(db.DateTime())
    status = db.Column(db.String(12), default='published')

    user = db.relationship('User', backref=db.backref('posts'), uselist=False)
    category = db.relationship('Category', uselist=False)
    post_type = db.relationship('PostType', uselist=False)
    rating = db.relationship('PostRating', cascade='all,delete', uselist=False)
    properties = db.relationship('PostProperties', cascade='all,delete')

    def __unicode__(self):
        return unicode(self.title) or u''

    @property
    def user_rating(self):
        if current_user.is_authenticated():
            return UserPostRating.query\
                .filter_by(post_id=self.id, user_id=current_user.id)\
                .first()
        else:
            return False

    @property
    def comments_count(self):
        return Comment.query\
            .filter_by(post_id=self.id)\
            .filter_by(status='published')\
            .count()

    @property
    def pretty_creation_date(self):
        return pretty_date(self.creation_date)

    @property
    def pretty_edit_date(self):
        return pretty_date(self.edit_date)

    @staticmethod
    @cache.memoize(timeout=3600*24)
    def get_picture_link(picture_id):
        picture = imgur_client.get_image(picture_id)
        return picture.link

    def thumbnail(self, size): #s, m, l, h
        if self.picture:
            if imgur_client:
                if not self.picture.startswith('_'):
                    # Automatic migration for previous Imgur integration, where
                    # only the image id was being served. We build the full link
                    # and save it.
                    if not self.picture.startswith('http'):
                        picture_link = Post.get_picture_link(self.picture)
                        self.picture = picture_link
                        db.session.commit()
                    root, ext = os.path.splitext(self.picture)
                    return "{0}{1}{2}".format(root, size, ext)

            if app.config['USE_UPLOADS_LOCAL_STORAGE']:
                local_storage_path = app.config['UPLOADS_LOCAL_STORAGE_PATH']
                local_picture = "{0}_{1}.jpg".format(self.uuid, size)
                local_picture = os.path.join(local_picture[:2], local_picture)
                local_file_path = os.path.join(local_storage_path, local_picture)
                if not os.path.isfile(local_file_path):
                    return None
                filename = os.path.join('storage', local_picture)
                full_link = url_for('static', filename=filename, _external=True)
                return full_link
            else:
                return None
        else:
            return None

    @property
    def original_image(self):
        if self.picture:
            if imgur_client:
                if not self.picture.startswith('_'):
                    if not self.picture.startswith('http'):
                        self.picture = Post.get_picture_link(self.picture)
                        db.session.commit()
                    return self.picture
            if app.config['USE_UPLOADS_LOCAL_STORAGE']:
                local_storage_path = app.config['UPLOADS_LOCAL_STORAGE_PATH']
                local_picture = "{0}.jpg".format(self.uuid)
                local_picture = os.path.join(local_picture[:2], local_picture)
                local_file_path = os.path.join(local_storage_path, local_picture)
                if not os.path.isfile(local_file_path):
                    return None
                filename = os.path.join('storage', local_picture)
                full_link = url_for('static', filename=filename, _external=True)
                return full_link
            else:
                return None

        else:
            return None

    @property
    def rating_delta(self):
        return self.rating.positive - self.rating.negative

    @property
    def hot(self):
        return hot(self.rating.positive, self.rating.negative, self.creation_date)

    def update_hot(self):
        self.rating.hot = hot(
            self.rating.positive, self.rating.negative, self.creation_date)
        db.session.commit()

    @property
    def comments_first_level(self):
        comments = [comment for comment in self.comments if not comment.parent_id]
        comments.sort(key=lambda comment: comment.confidence, reverse=True)
        return comments

    @property
    def is_featured(self):
        """If a submission is popular (gets many upvotes), this flag allows us
        to style it properly in the UI.
        """
        if self.rating_delta >= 12:
            if self.picture:
                return True
        return False

    def check_permissions(self):
        """Check if at least one computed user roles match the post category
        roles.
        """
        if [r.id for r in self.category.roles if r.id in computed_user_roles()]:
            return True
        else:
            abort(403)


categories_roles = db.Table('categories_roles',
    db.Column('category_id', db.Integer(), db.ForeignKey('category.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(128), nullable=False)
    order = db.Column(db.Integer)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent = db.relationship(
        'Category', remote_side=[id], backref=db.backref(
            'children', order_by=order))
    roles = db.relationship(
        'Role', secondary=categories_roles, backref='categories')

    def __str__(self):
        return str(self.name)


class PostType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(128), nullable=False)

    def __str__(self):
        return str(self.name)


class Comment(db.Model):
    """The comment model.
    Besides the similarties with the post model, it features the parent_id row,
    which allows nested comments. While nesting can be unlimited, we allow only
    one level of nesting.

    Comment status can be:
    - published (the default)
    - deleted
    - flagged
    - pinned
    - edited (maybe - we will not preserve history)

    In general the edit date refers to when the current status was assigned.
    """
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer(), db.ForeignKey('post.id'), nullable=False)
    uuid = db.Column(db.String(6))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime(), default=datetime.datetime.now)
    edit_date = db.Column(db.DateTime())
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    status = db.Column(db.String(12), default='published')

    parent = db.relationship(
        'Comment', remote_side=[id], backref=db.backref(
            'children', order_by=creation_date))
    user = db.relationship('User', backref=db.backref('comments'))
    post = db.relationship(
        'Post', backref=db.backref('comments', cascade='all,delete'))
    rating = db.relationship(
        'CommentRating', cascade='all,delete', uselist=False)

    def __str__(self):
        return str(self.uuid)

    @property
    def user_rating(self):
        if current_user.is_authenticated():
            return UserCommentRating.query\
                .filter_by(comment_id=self.id, user_id=current_user.id)\
                .first()
        else:
            return False

    @property
    def pretty_creation_date(self):
        return pretty_date(self.creation_date)

    @property
    def pretty_edit_date(self):
        return pretty_date(self.edit_date)

    @property
    def rating_delta(self):
        return self.rating.positive - self.rating.negative

    @property
    def confidence(self):
        return confidence(self.rating.positive, self.rating.negative)


class CommentRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer(),
        db.ForeignKey('comment.id'), nullable=False)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)


class UserCommentRating(db.Model):
    user_id = db.Column(
        db.Integer(), db.ForeignKey('user.id'), primary_key=True)
    comment_id = db.Column(
        db.Integer(), db.ForeignKey('comment.id'), primary_key=True)
    is_positive = db.Column(db.Boolean())
    is_flagged = db.Column(db.Boolean())


class PostRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer(), db.ForeignKey('post.id'), nullable=False)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)
    hot = db.Column(db.Float)


class UserPostRating(db.Model):
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), primary_key=True)
    post_id = db.Column(db.Integer(), db.ForeignKey('post.id'), primary_key=True)
    is_positive = db.Column(db.Boolean())
    is_flagged = db.Column(db.Boolean())


class PostProperties(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer(), db.ForeignKey('post.id'), nullable=False)
    field_type = db.Column(
        db.String(18), nullable=False)
    # tweet_id, #gplus_id, #gallery_image
    value = db.Column(db.String(256), nullable=False)
    order = db.Column(db.Integer())
