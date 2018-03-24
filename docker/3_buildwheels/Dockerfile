FROM armadillica/pillar_py:3.6
LABEL maintainer Sybren A. Stüvel <sybren@blender.studio>

RUN apt-get update && apt-get install -qy \
    git \
    build-essential \
    checkinstall \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev

ENV WHEELHOUSE=/data/wheelhouse
ENV PIP_WHEEL_DIR=/data/wheelhouse
ENV PIP_FIND_LINKS=/data/wheelhouse
RUN mkdir -p $WHEELHOUSE

VOLUME /data/wheelhouse
