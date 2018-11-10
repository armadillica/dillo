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

# Support for a handful of properties that are defined on a per-project basis
# The properties should follow the Cerberus pattern, and will be appended to the
# dyn_schema of the dillo_post node type for the project specified when running
# ./manage.py dillo attach_post_additional_properties

# This allows to introduce subtle variations in the schema depending on which
# project we are in. These differences should be accounted for when designing
# templates or forms.

# Using this feature requires Mongo 3.6 (for data migration actually). If you are
# using an older version and you upgrade, you will be required to run
# db.adminCommand( { setFeatureCompatibilityVersion: "3.6" } ).
POST_ADDITIONAL_PROPERTIES = {}
