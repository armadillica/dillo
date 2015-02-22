import datetime
from application import app
from application import db
from application import imgur_client

from application.modules.users.model import User
from application.helpers import pretty_date
from application.helpers.sorting import hot
from application.helpers.sorting import confidence


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(6), unique=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer(), db.ForeignKey('category.id'), nullable=False)
    post_type_id = db.Column(db.Integer(), db.ForeignKey('post_type.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    picture = db.Column(db.String(80))
    picture_deletehash = db.Column(db.String(80))
    creation_date = db.Column(db.DateTime(), default=datetime.datetime.now)
    edit_date = db.Column(db.DateTime())

    user = db.relationship('User', backref=db.backref('post'), uselist=False)
    category = db.relationship('Category', uselist=False)
    post_type = db.relationship('PostType', uselist=False)
    rating = db.relationship('PostRating', cascade='all,delete', uselist=False)

    def __str__(self):
        return str(self.title)

    @property
    def user_rating(self):
        return UserPostRating.query\
            .filter_by(post_id=self.id, user_id=self.user.id)\
            .first()

    @property
    def pretty_creation_date(self):
        return pretty_date(self.creation_date)

    def thumbnail(self, size): #s, m, l, h
        if self.picture:
            picture = imgur_client.get_image(self.picture)
            return picture.link.replace(self.picture, self.picture + size)
        else:
            return None

    @property
    def rating_delta(self):
        return self.rating.positive - self.rating.negative

    @property
    def hot(self):
        return hot(self.rating.positive, self.rating.negative, self.creation_date)

    def update_hot(self):
        self.rating.hot = hot(self.rating.positive, self.rating.negative, self.creation_date)
        db.session.commit()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(128), nullable=False)
    order = db.Column(db.Integer)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent = db.relationship('Category', 
        remote_side=[id], backref=db.backref('children', order_by=order))

    def __str__(self):
        return str(self.name)


class PostType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(128), nullable=False)

    def __str__(self):
        return str(self.name)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer(), db.ForeignKey('post.id'), nullable=False)
    uuid = db.Column(db.String(6), unique=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime(), default=datetime.datetime.now)
    edit_date = db.Column(db.DateTime())
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    parent = db.relationship('Comment', 
        remote_side=[id], backref=db.backref('children', order_by=creation_date))
    user = db.relationship('User', backref=db.backref('comments'))
    post = db.relationship('Post', backref=db.backref('comments', cascade='all,delete'))
    rating = db.relationship('CommentRating', cascade='all,delete', uselist=False)

    def __str__(self):
        return str(self.uuid)

    @property
    def user_rating(self):
        return UserCommentRating.query\
            .filter_by(comment_id=self.id, user_id=self.user.id)\
            .first()

    @property
    def pretty_creation_date(self):
        return pretty_date(self.creation_date)

    @property
    def rating_delta(self):
        return self.rating.positive - self.rating.negative

    @property
    def confidence(self):
        return confidence(self.rating.positive, self.rating.negative)


class CommentRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer(), db.ForeignKey('comment.id'), nullable=False)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)


class UserCommentRating(db.Model):
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), primary_key=True)
    comment_id = db.Column(db.Integer(), db.ForeignKey('comment.id'), primary_key=True)
    is_positive = db.Column(db.Boolean())


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
