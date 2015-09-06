# Dillo
Welcome to the Dillo codebase! Dillo is a free and open web platform created to
support crowd-driven content.

Originally developed for the news website [Blender.Today](http://blender.today),
it is now available as an unbranded site for anyone to power their own community!

We warmly welcome feedback, suggestions and pull requests.


## Development installation
Dillo is a Flask application, and follows most of the typical install conventions.
At this moment we don't provide specific instructions for online deployment, since
our main focus is to create a Docker file and Docker image for easy installs.

### Flask in the virtualenvironment
```
mkdir ~/venvs
virtualenv ~/venvs/dillo
. ~/venvs/dillo/bin activate
pip install -r requirements.txt
```

### Gulp
```
npm install
gulp
```

### Config
The `config.py.sample` must be duplicated into a `config.py`, and edited with
proper values.

### Manage
Before running the site for the first time, run the following
```
. ~/venvs/dillo/bin activate && python manage.py db upgrade
```

```
. ~/venvs/dillo/bin activate && python manage.py setup
```

Once the setup is complete, the site can be started with:

```
. ~/venvs/dillo/bin activate && python manage.py runserver
```

If you find any issues feel free to report them in the issue tracker. Thanks!
Dillo is licensed as [GPL2](https://www.gnu.org/licenses/gpl-2.0.txt).
