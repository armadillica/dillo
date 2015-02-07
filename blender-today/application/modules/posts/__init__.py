from flask import render_template
from flask import Blueprint

from application import app
from application import db

from application.modules.posts.model import Post

posts = Blueprint('posts', __name__)

# Views
@posts.route('/<uuid>')
def view(uuid):
    post = Post.query.filter_by(uuid=uuid).one()
    return render_template('posts/view.html', 
        content=post.content,
        title=post.title)
