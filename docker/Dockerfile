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
npm

RUN mkdir /data
RUN mkdir /data/www
RUN mkdir /data/www/dillo
RUN mkdir /data/dev
RUN mkdir /data/dev/dillo

# A dillo.env file, containing the private env variables is required
ADD dillo.env /dillo.env
RUN set -a && . /dillo.env && git clone https://$DILLO_TOKEN@github.com/armadillica/dillo.git /data/www/dillo

RUN pip install virtualenv
RUN virtualenv /data/venv
RUN . /data/venv/bin/activate && pip install -r /data/www/dillo/requirements.txt

VOLUME /data/dev/dillo

EXPOSE 5000

ADD runserver.sh /runserver.sh

ENTRYPOINT ["bash", "/runserver.sh"]
# CMD ["runserver"]
