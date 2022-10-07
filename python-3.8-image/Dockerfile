# SPDX-License-Identifier: MIT
#!BuildTag: bci/python:3.8
#!BuildTag: bci/python:3.8-%RELEASE%
#!BuildTag: bci/python:3

FROM opensuse/tumbleweed:latest

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.python
LABEL org.opencontainers.image.title="SLE BCI Python 3.8 Container Image"
LABEL org.opencontainers.image.description="Python 3.8 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="3.8"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/python:3.8-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends python38 python38-pip curl git-core python38-wheel; zypper -n clean; rm -rf /var/log/*
ENV PYTHON_VERSION="%%py38_ver%%"
ENV PIP_VERSION="%%pip_ver%%"

