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
from application.modules.posts.forms import PostForm

posts = Blueprint('posts', __name__)


@posts.route('/posts/')
def index():
    posts = Post.query.all()
    return render_template('posts/index.html', 
        posts=posts)


@posts.route('/<uuid>')
def view(uuid):
    post = Post.query.filter_by(uuid=uuid).one()
    return render_template('posts/view.html', 
        post=post)


@posts.route('/posts/submit', methods=['GET', 'POST'])
@login_required
def submit():
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        post = Post(
            uuid='a',
            user_id=current_user.id,
            category_id=form.category_id.data,
            title=form.title.data,
            slug='asd',
            content=form.content.data)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('posts.view', uuid=post.uuid))

    return render_template('posts/submit.html',
        form=form,
        title='submit')
