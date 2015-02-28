import os
import json
import datetime
from werkzeug import secure_filename
from flask import render_template
from flask import Blueprint
from flask import redirect
from flask import url_for
from flask import jsonify
from sqlalchemy import desc
from flask import abort
from flask import request

from flask.ext.security import login_required
from flask.ext.security import current_user

from application import app
from application import db
from application import imgur_client
from application import cache

from application.modules.posts.model import Category
from application.modules.posts.model import Post
from application.modules.posts.model import PostRating
from application.modules.posts.model import UserPostRating
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
@posts.route('/posts/<int:page>')
@cache.memoize(timeout=60)
def index(page=1):
    #posts = Post.query.all()
    #posts.sort(key=lambda p: p.hot, reverse=True)
    posts = Post.query\
        .join(PostRating)\
        .order_by(desc(PostRating.hot))\
        .paginate(page, per_page=10)
    return render_template('posts/index.html',
        title='index',
        posts=posts)


@posts.route('/<category>')
@posts.route('/<category>/<int:page>')
@cache.memoize(timeout=60)
def index_category(category, page=1):
    category = Category.query.filter_by(name=category).first_or_404()

    posts = Post.query\
        .join(Category)\
        .join(PostRating)\
        .filter(Category.name == category)\
        .order_by(desc(PostRating.hot))\
        .paginate(page, per_page=10)
    return render_template('posts/index.html',
        title='index_category',
        category=category.name,
        posts=posts)


@posts.route('/posts/<category>/<uuid>/')
@posts.route('/posts/<category>/<uuid>/<slug>')
def view(category, uuid, slug=None):
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
    current_user.is_owner = False
    if post.user.id == current_user.id and current_user.is_authenticated():
        current_user.is_owner = True
    return render_template('posts/view.html',
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
        content = form.content.data
        # If the post is a link
        if form.post_type_id.data == 1:
            content = form.url.data
        if not content:
            return abort(400)

        post = Post(
            user_id=current_user.id,
            category_id=form.category_id.data,
            post_type_id=form.post_type_id.data,
            title=form.title.data,
            slug=slugify(form.title.data),
            content=content)
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
        post.update_hot()
        if form.picture.data:
            filename = secure_filename(form.picture.data.filename)
            filepath = '/tmp/' + filename
            form.picture.data.save(filepath)
            image = imgur_client.upload_from_path(filepath, config=None, anon=True)
            post.picture = image['id']
            post.picture_deletehash = image['deletehash']
            os.remove(filepath)
        db.session.commit()

        return jsonify(
            post_url=url_for('posts.view',
                category=post.category.url, uuid=post.uuid))

        return redirect(url_for('posts.view',
            category=post.category.url, uuid=post.uuid))

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
    # If a rating exists, we update the the user post record and the post
    # record accordingly
    if user_post_rating:
        if user_post_rating.is_positive != rating:
            user_post_rating.is_positive = rating
            if user_post_rating.is_positive:
                post.rating.positive += 1
                post.rating.negative -= 1
                post.user.karma.positive += 5
                post.user.karma.negative -= 5
            else:
                post.rating.negative += 1
                post.rating.positive -= 1
                post.user.karma.negative += 5
                post.user.karma.positive -= 5
            db.session.commit()
        else:
            # Remove existing vote
            if user_post_rating.is_positive:
                post.rating.positive -= 1
                post.user.karma.positive -= 5
            else:
                post.rating.negative -= 1
                post.user.karma.negative -= 5
            db.session.delete(user_post_rating)
            db.session.commit()
            post.update_hot()
            post.user.update_karma()
            return jsonify(rating=None, rating_delta=post.rating_delta)
    else:
        # if the post has not bee rated, create rating
        user_post_rating = UserPostRating(
            user_id=current_user.id,
            post_id=post.id,
            is_positive=rating)
        if user_post_rating.is_positive:
            post.rating.positive += 1
            post.user.karma.positive += 5
        else:
            post.rating.negative += 1
            post.user.karma.negative += 5
        db.session.add(user_post_rating)
        db.session.commit()
    post.update_hot()
    post.user.update_karma()

    return jsonify(rating=str(user_post_rating.is_positive),
        rating_delta=post.rating_delta)


@posts.route('/posts/<uuid>/flag')
@login_required
def flag(uuid):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    # Get post
    user_post_rating = UserPostRating.query\
        .filter_by(post_id=post.id, user_id=current_user.id).first()
    # Check if user flagged the post
    if user_post_rating:
        # If the post was previously flagged
        if user_post_rating.is_flagged == True:
            user_post_rating.is_flagged = 0
            post.user.karma.negative += 5
        else:
            user_post_rating.is_flagged = 1
            post.user.karma.negative -= 5
    else:
        user_post_rating = UserPostRating(
            user_id=current_user.id,
            post_id=post.id,
            is_flagged=True)
        post.user.karma.negative += 5
        db.session.add(user_post_rating)

    # Commit changes so far
    db.session.commit()

    # Check if the post has been flagged multiple times, currently 
    # the value is hardcoded to 5
    flags = UserPostRating.query\
        .filter_by(post_id=post.id, is_flagged=True)\
        .all()
    if len(flags) > 5:
        post.status = 'flagged'
    post.user.update_karma()

    return jsonify(is_flagged=user_post_rating.is_flagged)


@posts.route('/posts/<uuid>/edit', methods = ['POST'])
@login_required
def edit(uuid):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    if post.user.id == current_user.id:
        post.content = request.form['content']
        post.status = 'edited'
        post.edit_date = datetime.datetime.now()
        db.session.commit()
        return 'ok'
    else:
        return abort(400)

