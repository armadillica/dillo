import os
import json
from werkzeug import secure_filename
from flask import render_template
from flask import Blueprint
from flask import redirect
from flask import url_for

from flask.ext.security import login_required
from flask.ext.security import current_user

from application import app
from application import db
from application import imgur_client

from application.modules.posts.model import Category
from application.modules.posts.model import Post
from application.modules.posts.model import PostRating
from application.modules.posts.model import UserPostRating
from application.modules.posts.model import Category
from application.modules.posts.model import PostType
from application.modules.posts.model import Comment
from application.modules.posts.model import CommentRating
from application.modules.posts.model import UserCommentRating
from application.modules.posts.forms import PostForm
from application.modules.posts.forms import CommentForm
from application.helpers import encode_id
from application.helpers import decode_id
from application.helpers import slugify

posts = Blueprint('posts', __name__)


@posts.route('/posts/')
def index():
    posts = Post.query.all()
    posts.sort(key=lambda p: p.hot, reverse=True)
    return render_template('posts/index.html',
        title='index',
        posts=posts)


@posts.route('/<category>')
def index_category(category):
    posts = Post.query.join(Category).filter(Category.name == category).all()
    posts.sort(key=lambda p: p.hot, reverse=True)
    return render_template('posts/index.html',
        title='index_category',
        category=category,
        posts=posts)


@posts.route('/posts/<category>/<uuid>/', defaults={'slug': None})
@posts.route('/posts/<category>/<uuid>/<slug>')
def view(category, uuid, slug):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    # Aggressive redirect if the URL does not have a slug
    if not slug:
        return redirect(url_for('posts.view', 
            category=category,
            uuid=uuid,
            slug=post.slug))
    post.comments.sort(key=lambda comment: comment.confidence, reverse=True)
    form = CommentForm()
    return render_template('posts/view.html',
        rating=post.rating.positive - post.rating.negative,
        title='view',
        post=post,
        form=form,
        picture=post.thumbnail('m'))


@posts.route('/posts/submit', methods=['GET', 'POST'])
@login_required
def submit():
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.post_type_id.choices = [(t.id, t.name) for t in PostType.query.all()]
    if form.validate_on_submit():
        post = Post(
            user_id=current_user.id,
            category_id=form.category_id.data,
            post_type_id=form.post_type_id.data,
            title=form.title.data,
            slug=slugify(form.title.data),
            content=form.content.data)
        db.session.add(post)
        db.session.commit()
        post.uuid = encode_id(post.id)
        db.session.commit()
        post_rating = PostRating(
            post_id=post.id,
            positive=0,
            negative=0
            )
        db.session.add(post_rating)
        if form.picture.data:
            filename = secure_filename(form.picture.data.filename)
            filepath = '/tmp/' + filename
            form.picture.data.save(filepath)
            image = imgur_client.upload_from_path(filepath, config=None, anon=True)
            post.picture = image['id']
            post.picture_deletehash = image['deletehash']
            os.remove(filepath)
        db.session.commit()

        return redirect(url_for('posts.view', category=post.category.url, uuid=post.uuid))

    return render_template('posts/submit.html',
        title='submit',
        form=form)


@posts.route('/posts/<uuid>/rate/<int:rating>')
@login_required
def rate(uuid, rating):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    # Check if post has been rated
    user_post_rating = UserPostRating.query\
        .filter_by(post_id=post.id, user_id=current_user.id).first()
    # If a rating exists, we update the the user post record and the post record accordingly
    if user_post_rating:
        if user_post_rating.is_positive != rating:
            user_post_rating.is_positive = rating
            if user_post_rating.is_positive:
                post.rating.positive += 1
                post.rating.negative -= 1
            else:
                post.rating.negative += 1
                post.rating.positive -= 1
            db.session.commit()
        else:
            # Remove existing vote
            if user_post_rating.is_positive:
                post.rating.positive -= 1
            else:
                post.rating.negative -= 1
            db.session.delete(user_post_rating)
            db.session.commit()
            return 'None'
    else:
        user_post_rating = UserPostRating(
            user_id=current_user.id,
            post_id=post.id,
            is_positive=rating)
        if user_post_rating.is_positive:
            post.rating.positive += 1
        else:
            post.rating.negative += 1
        db.session.add(user_post_rating)
        db.session.commit()

    return str(user_post_rating.is_positive)
