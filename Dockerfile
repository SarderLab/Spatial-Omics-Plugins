FROM python:3.12-slim

LABEL maintainer="Sarder Lab <anish.tatke@ufl.edu>"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git curl wget ca-certificates unzip \
    build-essential cmake autoconf automake libtool pkg-config \
    libssl-dev libexpat1-dev libcurl4-openssl-dev \
    libxml2-dev libxslt1-dev \
    ffmpeg libsm6 libxext6 \
    gdal-bin libgdal-dev libpq-dev \
    libmemcached-dev memcached \
    graphviz && \
    rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /
# Make Python3 the default and install pip.  Whichever is done last determines
# the default python version for pip.

#
RUN which  python && \
    python --version

RUN apt-get update && \
    apt-get install -y --no-install-recommends memcached && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV build_path=/build
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

ENV plugin_path=/opt/Spatial-Omics-Plugins
RUN mkdir -p ${plugin_path}

COPY . $plugin_path
WORKDIR $plugin_path

# Installing packages in setup.py
# Make sure to add links for large-image whls
RUN pip install --upgrade pip

RUN pip install --upgrade --ignore-installed --no-cache-dir pip setuptools wheel && \
    pip install . --find-links https://girder.github.io/large_image_wheels && \
    rm -rf /root/.cache/pip/*

# Show what was installed
RUN python --version && pip --version && pip freeze

# Defining entrypoint
WORKDIR $plugin_path
LABEL entry_path="$plugin_path/SpatialAggregation/cli"

RUN pip list

# Testing entrypoint
WORKDIR $plugin_path/SpatialAggregation/cli
RUN python -m slicer_cli_web.cli_list_entrypoint --list_cli
RUN python -m slicer_cli_web.cli_list_entrypoint Aggregate --help

ENV PYTHONUNBUFFERED=TRUE

ENTRYPOINT ["/bin/bash", "docker-entrypoint.sh"]