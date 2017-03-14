# Pistacchio - Pillar Sample Extension

This is a *vanilla* extension of the Pillar framework. Pistacchio works as a 
standalone application to illustrate how to expand Pillar for new extensions.
Please note that extentions can not expose endpoints outside of their scope (in
the case of this application, the '/pistacchio' endpoint) and should be
initialized within a pillar-based application.

If you are interested in adding different endpoints, like for example '/about',
you should simply create an application, not an extension. To learn more about
pillar-based applications and extensions, please check out the Pillar docs.

## Features

* Basic Pillar extension
* Unit testing
* Documentation

## How to set it up

```bash
git clone git://git.blender.org/pillar-server.git
cd pillar-server
pip install -e .
pip install -r requirements.txt
# setup pillar-server
# refer to pillar-server documentation
cd ..
git clone git://git.blender.org/pillar-pistacchio.git pistacchio
cd pistacchio
# Install any local requirements
pip install -r requirements.txt
# Initialize the project with a default project and email address
python manage.py setup setup_db email@example.com
```

## How to run it

```bash
python manage.py runserver
```

Now open a web-browser of your preference and visit:
```text
http://127.0.0.1:5000/pistacchio
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

