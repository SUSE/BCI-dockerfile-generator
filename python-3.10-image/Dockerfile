# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/bci/python:3.10
#!BuildTag: opensuse/bci/python:latest
#!BuildTag: opensuse/bci/python:3.10-%RELEASE%
#!BuildTag: opensuse/bci/python:3

FROM opensuse/tumbleweed:latest

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.bci.python
LABEL org.opencontainers.image.title="openSUSE Tumbleweed BCI Python 3.10 Container Image"
LABEL org.opencontainers.image.description="Python 3.10 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="3.10"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/bci/python:3.10-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends python310-devel python310-pip curl git-core python310-wheel; zypper -n clean; rm -rf /var/log/*
ENV PYTHON_VERSION="%%py310_ver%%"
ENV PIP_VERSION="%%pip_ver%%"

