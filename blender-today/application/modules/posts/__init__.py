from flask import render_template
from flask import Blueprint
from flask import redirect
from flask import url_for

from flask.ext.security import login_required
from flask.ext.security import current_user

from application import app
from application import db

from application.modules.posts.model import Post
from application.modules.posts.model import Category
from application.modules.posts.model import Comment
from application.modules.posts.forms import PostForm
from application.modules.posts.forms import CommentForm
from application.helpers import encode_id
from application.helpers import decode_id
from application.helpers import slugify

posts = Blueprint('posts', __name__)


@posts.route('/posts/')
def index():
    posts = Post.query.all()
    return render_template('posts/index.html', 
        posts=posts)


@posts.route('/<category>/<uuid>')
def view(category, uuid):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    form = CommentForm()
    return render_template('posts/view.html',
        post=post,
        form=form)


@posts.route('/posts/submit', methods=['GET', 'POST'])
@login_required
def submit():
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        post = Post(
            user_id=current_user.id,
            category_id=form.category_id.data,
            title=form.title.data,
            slug=slugify(form.title.data),
            content=form.content.data)
        db.session.add(post)
        db.session.commit()
        post.uuid = encode_id(post.id)
        db.session.commit()
        return redirect(url_for('posts.view', category=post.category.url, uuid=post.uuid))

    return render_template('posts/submit.html',
        form=form,
        title='submit')


@posts.route('/comments/<int:post_id>/submit', methods=['POST'])
@login_required
def comment(post_id):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        comment = Comment(
            user_id=current_user.id,
            post_id=post.id,
            content=form.content.data)
        db.session.add(comment)
        db.session.commit()
        comment.uuid = encode_id(comment.id)
        db.session.commit()
        return redirect(url_for('posts.view', category=post.category.url, uuid=post.uuid))

    return redirect(url_for('posts.view', category=post.category.url, uuid=post.uuid))
