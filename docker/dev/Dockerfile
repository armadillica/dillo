FROM ubuntu
MAINTAINER Francesco Siddi <francesco@dillo.space>

# Update aptitude with new repo
RUN apt-get update

RUN apt-get update && apt-get install -y \
python \
python-dev \
python-pip \
git \
nano \
zlib1g-dev \
libjpeg-dev \
libmysqlclient-dev \
nodejs \
nodejs-legacy \
npm

RUN mkdir -p /data/git/dillo

RUN pip install virtualenv \
&& virtualenv /data/venv

ENV PIP_PACKAGES_VERSION = 1
ADD requirements.txt /requirements.txt

RUN . /data/venv/bin/activate && pip install -r /requirements.txt

VOLUME /data/git/dillo

EXPOSE 5000

ADD manage.sh /manage.sh
ADD setup.sh /setup.sh

ENTRYPOINT ["bash", "/manage.sh"]
