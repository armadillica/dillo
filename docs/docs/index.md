# Dillo Development Docs

## Installation

```bash
git clone git://git.blender.org/pillar.git
git clone git://git.blender.org/pillar-python-sdk.git
git clone git@github.com:armadillica/dillo.git
cd dillo
pip install -r requirements-dev.txt
```

Make a config local and add your categories to it:
```
# This list generate the selection menu when creating or editing a post.
POST_CATEGORIES = ['Artwork', 'Tutorials', 'Resources', 'Sneak Peek']
```

Setup [Algolia](https://www.algolia.com):

Create an account in their site, and add your Algolia API Keys and setup to the `config_local.py

```
ALGOLIA_USER = '1QFJ16Q4TZ' # Application ID
ALGOLIA_PUBLIC_KEY = '039c5c1d0efe9d25d06c00f55a541963' # Search-Only API Key
ALGOLIA_API_KEY = '1389947be424f13fbecedabb13ef1710' # Admin API Key
ALGOLIA_INDEX_USERS = 'dev_UsersYourName'
ALGOLIA_INDEX_NODES = 'dev_NodesYourName'
```

Create the default project, which will be the host for various communities.

```
python manage.py dillo setup_db <admin_email>
```

Create a project and initialize it as a community
TODO check how to create a new project.

```
python manage.py dillo setup_for_dillo today
```

Configure your nodes index with:

```
python manage.py dillo index_nodes_update_settings
```

## How to run it (FIXME)

```bash
python manage.py runserver
```

Now open a web-browser of your preference and visit:
```text
http://dillo.local:5000/
```

## Project layout

    docs/                   # Documentation folder
        ...                 # Documentation files
    gulpfile.js             # Gulp setup file (for web interface)
    LICENSE.txt             # GPL license
    package.json            # Required NPM packages list (used by node)
    pistacchio/             # Extension source code
        __init__.py         #
        cli.py              # ?
        eve_settings.py     # ?
        routes.py           # ?
        setup.py            # ?
        static/             # ?
            ...             # ?
        templates/          # ?
            ...             # ?
    readme.md               # Introductory document
    requirements.txt        # Python requirements (pip install -r requirements.txt)
    manage.py               # The entry point of the program
    src/                    # Web interface
        ...                 # Web interface files
    tests/                  # Unit testing
        ...                 # Proper test files

## Indexing
Explain how we use the Nodes index from the config, but perform indexing in our own hook.
Mention that we extend the indexing process by defining index replicas for returning sorted
results.

## Tags (TODO)
See config

## Post Additional Properties
This feature allows the support of 'custom' properties within a dillo_post Node Type.
We define a `POST_ADDITIONAL_PROPERTIES` dict in `config_local.py` and Dillo takes care
of the rest. For example:

    POST_ADDITIONAL_PROPERTIES = {
        'status_dev': {
            'schema':  {
                'type': 'string',
                'default': 'Unknown',
                'allowed': ['Unknown', 'In Development']
            },
            'indexing': {
                'searchable': True,
                'faceting': 'searchable'
            },
            'projects': ['rcs'],
            'label': 'Dev. Status',
        }
    }

In this case: 

* `status_dev` is the key added to `dyn_schema` of `dillo_post`
* `indexing` extends the indexing settings when running `index_nodes_update_settings`
* `projects` defines to which project we should apply this additional properties
* `label` is the UI representation of the key


### Usage

Additional properties should be applied as follows:

* Define the additional properties in `POST_ADDITIONAL_PROPERTIES`
* `./manage.py dillo attach_post_additional_properties`
* `./manage.py dillo index_nodes_update_settings`

### Integration details

There are a few places where additional properties are handled:

* `index.pug`, where we dynamically add Instant Search widgets
* `dillo/api/posts/hooks.py`, where we define the indexing behaviour
* `cli.py`, where we configure the Nodes index

Additional Properties should be displayed only in the context where we expect them to
be. For this reason, the main posts index (which aggregates posts from all projects)
does not feature them as filters.
