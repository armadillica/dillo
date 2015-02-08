import datetime
from application import app
from application import db

from application.modules.users.model import User
from application.helpers import pretty_date


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


class UserPostRating(db.Model):
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), primary_key=True)
    post_id = db.Column(db.Integer(), db.ForeignKey('post.id'), primary_key=True)
    is_positive = db.Column(db.Boolean())
