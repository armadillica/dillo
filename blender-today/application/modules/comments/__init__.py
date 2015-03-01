import datetime
from flask import render_template
from flask import Blueprint
from flask import redirect
from flask import url_for
from flask import jsonify
from flask import abort

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


@comments.route('/<int:post_id>/')
@login_required
def index(post_id):
    post = Post.query.get_or_404(post_id)
    comments = []
    for comment in post.first_level_comments():
        comments.append({
            'uuid' : comment.uuid,
            'user_id' : comment.user.id
            })
    #comments = [comment for comment in post.first_level_comments()]
    return jsonify(comments=comments)

@comments.route('/<int:post_id>/submit', methods=['POST'])
@login_required
def submit(post_id):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        parent_id = form.parent_id.data
        if not parent_id:
            parent_id = None
        else:
            parent_id = int(form.parent_id.data)
        comment = Comment(
            user_id=current_user.id,
            post_id=post.id,
            parent_id=parent_id,
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
    return jsonify(comment=dict(
        user_name="{0} {1}".format(
            comment.user.first_name, comment.user.last_name),
        gravatar=comment.user.gravatar(),
        content=comment.content,
        comment_id=comment.id,
        parent_id=comment.parent_id,
        post_uuid=post.uuid,
        creation_date=comment.pretty_creation_date,
        ))
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
                comment.user.karma.positive += 1
                comment.user.karma.negative -= 1
            else:
                comment.rating.negative += 1
                comment.rating.positive -= 1
                comment.user.karma.negative += 1
                comment.user.karma.positive -= 1
            db.session.commit()
        else:
            # Remove existing rate
            if user_comment_rating.is_positive:
                comment.rating.positive -= 1
                comment.user.karma.positive -= 1
            else:
                comment.rating.negative -= 1
                comment.user.karma.negative -= 1
            db.session.delete(user_comment_rating)
            db.session.commit()
            comment.user.update_karma()
            return jsonify(rating=None,
                rating_delta=comment.rating_delta)
    else:
        user_comment_rating = UserCommentRating(
            user_id=current_user.id,
            comment_id=comment.id,
            is_positive=rating)
        if user_comment_rating.is_positive:
            comment.rating.positive += 1
            comment.user.karma.positive += 1
        else:
            comment.rating.negative += 1
            comment.user.karma.positive += 1
        db.session.add(user_comment_rating)
        db.session.commit()
        comment.user.update_karma()

    return jsonify(rating=str(user_comment_rating.is_positive),
        rating_delta=comment.rating_delta)


@comments.route('/<int:comment_id>/flag')
@login_required
def flag(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    # Get comment
    user_comment_rating = UserCommentRating.query\
        .filter_by(comment_id=comment.id, user_id=current_user.id).first()
    # Check if user rated the comment
    if user_comment_rating:
        # If the comment was previously flagged
        if user_comment_rating.is_flagged == True:
            user_comment_rating.is_flagged = 0
            comment.user.karma.negative += 5
        else:
            user_comment_rating.is_flagged = 1
            comment.user.karma.negative -= 5
    else:
        user_comment_rating = UserCommentRating(
            user_id=current_user.id,
            comment_id=comment.id,
            is_flagged=True)
        comment.user.karma.negative += 5
        db.session.add(user_comment_rating)

    # Commit changes so far
    db.session.commit()

    # Check if the comment has been flagged multiple times, currently 
    # the value is hardcoded to 5
    flags = UserCommentRating.query\
        .filter_by(comment_id=comment.id, is_flagged=True)\
        .all()
    if len(flags) > 5:
        comment.status = 'flagged'
    comment.user.update_karma()

    return jsonify(is_flagged=user_comment_rating.is_flagged)


@comments.route('/<int:comment_id>/edit', methods=['POST'])
@login_required
def edit(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user.id == comment.user.id:
        comment.content = request.form['content']
        comment.status = 'edited'
        comment.edit_date = datetime.datetime.now()
        db.session.commit()
        return jsonify(status='edited')
    else:
        return abort(403)


@comments.route('/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user.id == comment.user.id:
        comment.status = 'deleted'
        comment.edited = datetime.datetime.now
        db.session.commit()
        return jsonify(status='deleted')
    else:
        return abort(403)
