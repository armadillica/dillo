# Everyone is allowed to rate. We determine validity of vote elsewhere.
ROLES_FOR_COMMENT_VOTING = set()

# This list generate the selection menu when creating or editing a post.
POST_CATEGORIES = ['Artwork', 'Community', 'Development', 'Add-Ons', 'Education', 'Tutorials',
                   'Resources']

# Used for redirecting to the default community when visiting /c/
DEFAULT_COMMUNITY = 'main'

GOOGLE_ANALYTICS_TRACKING_ID = ''
GOOGLE_SITE_VERIFICATION = ''

SETTINGS_TWITTER_USERNAME = ''

ALGOLIA_INDEX_NODES_REPLICAS = {
    'created': '_by_created_desc',
    'rating': '_by_rating_desc',
}
