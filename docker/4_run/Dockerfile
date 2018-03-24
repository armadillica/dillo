FROM armadillica/pillar_py:3.6
LABEL maintainer Francesco Siddi <francesco@blender.studio>

RUN apt-get update && apt-get install -qyy \
-o APT::Install-Recommends=false -o APT::Install-Suggests=false \
git \
apache2 \
libapache2-mod-xsendfile \
libjpeg8 \
libtiff5 \
ffmpeg \
rsyslog logrotate \
nano vim-tiny curl \
&& rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/vim.tiny /usr/bin/vim

ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2
ENV APACHE_PID_FILE /var/run/apache2.pid
ENV APACHE_RUN_DIR /var/run/apache2
ENV APACHE_LOCK_DIR /var/lock/apache2

RUN mkdir -p $APACHE_RUN_DIR $APACHE_LOCK_DIR $APACHE_LOG_DIR

ADD wheelhouse /data/wheelhouse
RUN pip3 install --no-index --find-links=/data/wheelhouse -r /data/wheelhouse/requirements.txt

VOLUME /data/config
VOLUME /data/storage
VOLUME /var/log

ENV USE_X_SENDFILE True

EXPOSE 80
EXPOSE 5000

ADD apache/wsgi-py36.* /etc/apache2/mods-available/
RUN a2enmod rewrite && a2enmod wsgi-py36

ADD apache/apache2.conf /etc/apache2/apache2.conf
ADD apache/000-default.conf /etc/apache2/sites-available/000-default.conf
ADD apache/logrotate.conf /etc/logrotate.d/apache2
ADD *.sh /

# Remove some empty top-level directories we won't use anyway.
RUN rmdir /media /home 2>/dev/null || true

# This file includes some useful commands to have in the shell history
# for easy access.
ADD bash_history /root/.bash_history

ENTRYPOINT /docker-entrypoint.sh

# Add the most-changing files as last step for faster rebuilds.
ADD config_local.py /data/git/dillo/
ADD deploy /data/git
RUN python3 -c "import re, secrets; \
f = open('/data/git/dillo/config_local.py', 'a'); \
h = re.sub(r'[_.~-]', '', secrets.token_urlsafe())[:8]; \
print(f'STATIC_FILE_HASH = {h!r}', file=f)"
