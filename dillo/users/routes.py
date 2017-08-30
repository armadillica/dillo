import logging

from flask import abort, current_app, render_template

from pillarsdk import Node
from pillar.web.users.routes import blueprint
from pillar.web import system_util
from pillar.web.utils import get_file

log = logging.getLogger(__name__)


@blueprint.route('/u/<username>')
def users_view(username):
    """View public user page.

    Use direct db call to retrieve the user and then use the api to query the paginated list of all
    published dillo_posts from the user.

    """
    users_coll = current_app.db('users')
    user = users_coll.find_one(
        {'username': username}, projection={'username': 1, 'full_name': 1, '_created': 1})
    if user is None:
        return abort(404)
    api = system_util.pillar_api()
    posts = Node.all({
        'where': {'user': str(user['_id']), 'node_type': 'dillo_post', 'properties.status': 'published'},
        'sort': '-_created',
    }, api=api)

    for post in posts['_items']:
        if post.picture:
            post.picture = get_file(post.picture, api=api)

    return render_template('dillo/user.html', user=user, posts=posts)
