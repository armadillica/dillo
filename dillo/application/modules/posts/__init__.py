import os
import datetime
import requests
from PIL import Image
from werkzeug import secure_filename
from flask import render_template
from flask import Blueprint
from flask import redirect
from flask import url_for
from flask import jsonify
from sqlalchemy import desc
from flask import abort
from flask import request
from werkzeug.contrib.atom import AtomFeed
from micawber.exceptions import ProviderException
from micawber.exceptions import ProviderNotFoundException
from flask.ext.security import login_required
from flask.ext.security import current_user

from application import app
from application import db
from application import imgur_client
from application import registry
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
from application.modules.notifications import notification_subscribe
from application.modules.users.model import Role
from application.helpers import encode_id
from application.helpers import decode_id
from application.helpers import slugify
from application.helpers import bleach_input
from application.helpers import check_url
from application.helpers import delete_redis_cache_keys
from application.helpers import delete_redis_cache_post
from application.helpers import computed_user_roles
from application.helpers.imaging import generate_local_thumbnails

posts = Blueprint('posts', __name__)


@posts.route('/p/')
@posts.route('/p/<int:page>')
def index(page=1):
    categories = Category.query.all()
    roles = computed_user_roles()
    posts_list = Post.query\
        .filter_by(status='published') \
        .join(Category) \
        .filter(Category.roles.any(Role.id.in_(roles))) \
        .join(PostRating)\
        .order_by(desc(PostRating.hot))\
        .paginate(page, per_page=20)
    user_string_id = 'ANONYMOUS'
    if current_user.is_authenticated():
        user_string_id = current_user.string_id
    return render_template('posts/index.html',
                           title='index',
                           categories=categories,
                           category_url='',  # used for caching index
                           user_string_id=user_string_id,
                           page=str(page),
                           posts=posts_list)


@posts.route('/p/<category>')
@posts.route('/p/<category>/<int:page>')
def index_category(category, page=1):
    category = Category.query\
        .filter_by(url=category).first_or_404()
    categories = Category.query.all()
    roles = computed_user_roles()
    user_string_id = 'ANONYMOUS'
    if current_user.is_authenticated():
        user_string_id = current_user.string_id
    posts_category = Post.query\
        .filter_by(status='published')\
        .join(Category)\
        .join(PostRating)\
        .filter(Category.url == category.url) \
        .filter(Category.roles.any(Role.id.in_(roles))) \
        .order_by(desc(PostRating.hot))\
        .paginate(page, per_page=20)\

    return render_template('posts/index.html',
        title='index_category',
        categories=categories,
        category_url=category.url, #used for caching index
        category=category,
        user_string_id=user_string_id,
        page=str(page),
        posts=posts_category)


@posts.route('/p/<category>/<uuid>/')
@posts.route('/p/<category>/<uuid>/<slug>')
def view(category, uuid, slug=None):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    categories = Category.query.all()
    user_string_id = 'ANONYMOUS'
    if current_user.is_authenticated():
        user_string_id = current_user.string_id

    # Aggressive redirect if the URL does not have a slug
    if not slug:
        return redirect(url_for('posts.view',
            category=category,
            uuid=uuid,
            slug=post.slug))
    #post.comments.sort(key=lambda comment: comment.confidence, reverse=True)

    oembed = None
    # If the content is a link, we try to pass it through micawber to do
    # some nice embedding
    if post.post_type_id == 1:
        try:
            oembed = registry.request(post.content)
            # Keep in mind that oembed can be of different types:
            # - photo
            # - video
            # - link
            # - etc
        except (ProviderNotFoundException, ProviderException):
            # If the link is not an OEmbed provider, we move on
            pass
        else:
            # For any other error (e.g. video was unpublished) we also pass
            pass

    form = CommentForm()
    if current_user.is_anonymous():
        current_user.is_owner = False
    elif current_user.is_authenticated() and post.user.id == current_user.id:
        current_user.is_owner = True
    return render_template('posts/view.html',
        title='view',
        post=post,
        oembed=oembed,
        form=form,
        categories=categories,
        user_string_id=user_string_id,
        picture=post.thumbnail('m'))


@posts.route('/p/submit', methods=['POST'])
@login_required
def submit():
    form = PostForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        content = form.content.data
        # If the post is a link (is 1), we cast this because it's coming from
        # a hidden field
        post_type_id = int(form.post_type_id.data)
        if post_type_id == 1:
            content = form.url.data
            if not check_url(content):
                return abort(404)
        else:
            # Clean the content
            content = bleach_input(content)
        if not content:
            return abort(400)

        post = Post(
            user_id=current_user.id,
            category_id=form.category_id.data,
            post_type_id=post_type_id,
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
        if form.picture.data or form.picture_remote.data:
            if form.picture.data:
                # If the user uploads an image from the form
                filename = secure_filename(form.picture.data.filename)
                filepath = '/tmp/' + filename
                form.picture.data.save(filepath)
            else:
                # If the url is retrieved via embedly
                filename = secure_filename(form.picture_remote.data)
                filepath = '/tmp/' + filename
                with open(filepath, 'wb') as handle:
                    response = requests.get(form.picture_remote.data, stream=True)
                    for block in response.iter_content(1024):
                        if not block:
                            break
                        handle.write(block)

            # In both cases we get the image now saved in temp and upload it
            # to Imgur
            if imgur_client:
                image = imgur_client.upload_from_path(filepath, config=None, anon=True)
            else:
                image = dict(link=None, deletehash=None)

            if app.config['USE_UPLOADS_LOCAL_STORAGE']:
                # Use the post UUID as a name for the local image.
                # If Imgur is not available save it in the database with a _ to
                # imply that the file is available only locally.
                if not image['link']:
                    image['link'] = '_' + post.uuid
                image_name = post.uuid + '.jpg'
                # The root of the local storage path
                local_storage_path = app.config['UPLOADS_LOCAL_STORAGE_PATH']
                # Get the first 2 chars of the image name to make a subfolder
                storage_folder = os.path.join(local_storage_path, image_name[:2])
                # Check if the subfolder exists
                if not os.path.exists(storage_folder):
                    # Make it if it does not
                    os.mkdir(storage_folder)
                # Build the full path to store the image
                storage_filepath = os.path.join(storage_folder, image_name)
                # Copy from temp to the storage path
                im = Image.open(filepath)
                im.save(storage_filepath, "JPEG")
                # Make all the thumbnails
                generate_local_thumbnails(storage_filepath)
            post.picture = image['link']
            post.picture_deletehash = image['deletehash']
            os.remove(filepath)
        db.session.commit()

        # Subscribe owner to updates for this post (mainly comments)
        notification_subscribe(current_user.id, 1, post.id)

        # Clear all the caches
        delete_redis_cache_keys('post_list')
        delete_redis_cache_keys('post_list', post.category.url)

        return jsonify(
            post_url=url_for('posts.view',
            category=post.category.url,
            uuid=post.uuid,
            slug=post.slug))
    else:
        return abort(400, '{"message" : "form validation error"}')

    #     return redirect(url_for('posts.view',
    #         category=post.category.url, uuid=post.uuid))

    # return render_template('posts/submit.html',
    #     title='submit',
    #     form=form)


@posts.route('/p/<uuid>/rate/<int:rating>')
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
            delete_redis_cache_keys('post_list')
            delete_redis_cache_keys('post_list', post.category.url)
            delete_redis_cache_post(post.uuid)

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

    delete_redis_cache_keys('post_list')
    delete_redis_cache_keys('post_list', post.category.url)
    delete_redis_cache_post(post.uuid)

    return jsonify(rating=str(user_post_rating.is_positive),
        rating_delta=post.rating_delta)


@posts.route('/p/<uuid>/flag')
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

    # Clear all the caches
    delete_redis_cache_keys('post_list')
    delete_redis_cache_keys('post_list', post.category.url)
    delete_redis_cache_post(post.uuid)

    return jsonify(is_flagged=user_post_rating.is_flagged)


@posts.route('/p/<uuid>/edit', methods=['POST'])
@login_required
def edit(uuid):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    if (post.user.id == current_user.id) or (current_user.has_role('admin')):
        post.title = request.form['title']
        post.status = 'published'
        post.edit_date = datetime.datetime.now()

        if post.post_type.url == 'text':
            post.content = bleach_input(request.form['content'])

        db.session.commit()

        # Clear all the caches
        delete_redis_cache_keys('post_list')
        delete_redis_cache_keys('post_list', post.category.url)
        delete_redis_cache_post(post.uuid)

        return jsonify(status='published')
    else:
        return abort(403)


@posts.route('/p/<uuid>/delete', methods=['POST'])
@login_required
def delete(uuid):
    post_id = decode_id(uuid)
    post = Post.query.get_or_404(post_id)
    if (post.user.id == current_user.id) or (current_user.has_role('admin')):
        post.status = 'deleted'
        post.edit_date = datetime.datetime.now()
        db.session.commit()
        # Clear all the caches
        delete_redis_cache_keys('post_list')
        delete_redis_cache_keys('post_list', post.category.url)
        delete_redis_cache_post(post.uuid)
        return jsonify(status='deleted')
    else:
        return abort(403)


@posts.route('/p/feed/latest.atom')
@cache.cached(60*5)
def feed():
    feed = AtomFeed("{0} - Posts".format(app.config['SETTINGS_TITLE']),
                    feed_url=request.url, url=request.url_root)
    posts = Post.query\
        .filter_by(status='published')\
        .order_by(desc(Post.creation_date))\
        .limit(15)\
        .all()
    for post in posts:
        author = ''
        if post.user:
            author = post.user.username

        updated = post.edit_date if post.edit_date else post.creation_date

        feed.add(post.title, unicode(post.content),
                 content_type='html',
                 author=author,
                 url=url_for('posts.view',
                    category=post.category.url,
                    uuid=post.uuid,
                    slug=post.slug,
                    _external=True),
                 updated=updated,
                 published=post.creation_date)
    return feed.get_response()
