# Dillo
Welcome to the Dillo codebase! Dillo is a free and open web platform created to
support crowd-driven content.

Originally developed for the news website [Blender.Today](http://blender.today),
it is now available as an unbranded site for anyone to power their own community!

We warmly welcome feedback, suggestions and pull requests.


## Quick install with Docker
Keep in mind that the current installation insturctions are valid only for testing.
A production docker image will be available soon. In order to use the docker
image you need [Docker](https://www.docker.com/)

Once installed, you can simply run:

```
docker run --entrypoint="bash" -ti --name dillo_dev -p 5000:5000 \
-v <YOUR_DILLO_CHECKOUT_PATH>:/data/git/dillo armadillica/dillo_dev
```

This will download the `dillo_dev` image on your system and log you into the
container. At that point you should run:

```
./setup.sh
```

and follow the instructions. Once the procedure is complete, run:

```
./manage.sh runserver
```

At this point Dillo is running and you can see it in your web browser.


## Development installation
Dillo is a Flask application, and follows most of the typical install conventions.
At this moment we don't provide specific instructions for online deployment, since
our main focus is to create a Docker file and Docker image for easy installs.

### Dependencies
- MySQL (on Linux make sure you have `libmysqlclient-dev`)
- Python 2.7 (on Linux make sure you have `python-dev`)
- virtualenv
- Nodejs (in particular we use `npm`)

### Flask in the virtualenvironment
```
mkdir ~/venvs
virtualenv ~/venvs/dillo
. ~/venvs/dillo/bin activate
pip install -r requirements.txt
```

### Gulp
```
npm install -g gulp
npm install
gulp
```

### Database
Set up a MySQL database where you will install dillo. No schema is needed, just
the database.

### Config
The `config.py.sample` must be duplicated into a `config.py`, and edited with
proper values.

### Manage
Before running the site for the first time, run the following
```
. ~/venvs/dillo/bin/activate && python manage.py db upgrade
```

```
. ~/venvs/dillo/bin/activate && python manage.py setup
```

Once the setup is complete, the site can be started with:

```
. ~/venvs/dillo/bin/activate && python manage.py runserver
```

If you find any issues feel free to report them in the issue tracker. Thanks!
Dillo is licensed as [GPL2](https://www.gnu.org/licenses/gpl-2.0.txt).
