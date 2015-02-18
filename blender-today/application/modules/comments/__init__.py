from flask import render_template
from flask import Blueprint
from flask import redirect
from flask import url_for
from flask import jsonify

from flask.ext.security import login_required
from flask.ext.security import current_user

from application import app
from application import db

from application.modules.posts.model import Post
from application.modules.posts.model import Comment
from application.modules.posts.model import CommentRating
from application.modules.posts.model import UserCommentRating
from application.modules.posts.forms import CommentForm
from application.helpers import encode_id
from application.helpers import decode_id

comments = Blueprint('comments', __name__)

@comments.route('/<int:post_id>/submit', methods=['POST'])
@login_required
def submit(post_id):
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
        comment_rating = CommentRating(
            comment_id=comment.id,
            positive=0,
            negative=0
            )
        db.session.add(comment_rating)
        db.session.commit()
        return redirect(url_for('posts.view',
            category=post.category.url, 
            uuid=post.uuid))

    return redirect(url_for('posts.view',
        category=post.category.url,
        uuid=post.uuid))


@comments.route('/<int:comment_id>/rate/<int:rating>')
@login_required
def rate(comment_id, rating):
    comment = Comment.query.get_or_404(comment_id)
    # Check if comment has been rated
    user_comment_rating = UserCommentRating.query\
        .filter_by(comment_id=comment.id, user_id=current_user.id).first()
    # If a rating exists, we update the the user comment record and the comment
    # record accordingly
    if user_comment_rating:
        if user_comment_rating.is_positive != rating:
            user_comment_rating.is_positive = rating
            if user_comment_rating.is_positive:
                comment.rating.positive += 1
                comment.rating.negative -= 1
            else:
                comment.rating.negative += 1
                comment.rating.positive -= 1
            db.session.commit()
        else:
            # Remove existing rate
            if user_comment_rating.is_positive:
                comment.rating.positive -= 1
            else:
                comment.rating.negative -= 1
            db.session.delete(user_comment_rating)
            db.session.commit()
            return jsonify(rating=None,
                rating_delta=comment.rating_delta)
    else:
        user_comment_rating = UserCommentRating(
            user_id=current_user.id,
            comment_id=comment.id,
            is_positive=rating)
        if user_comment_rating.is_positive:
            comment.rating.positive += 1
        else:
            comment.rating.negative += 1
        db.session.add(user_comment_rating)
        db.session.commit()

    return jsonify(rating=str(user_comment_rating.is_positive),
        rating_delta=comment.rating_delta)

