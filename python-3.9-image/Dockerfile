# SPDX-License-Identifier: MIT
#!BuildTag: bci/python:3.9
#!BuildTag: bci/python:3.9-%RELEASE%
#!BuildTag: bci/python:3

FROM opensuse/tumbleweed:latest

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.python
LABEL org.opencontainers.image.title="SLE BCI Python 3.9 Container Image"
LABEL org.opencontainers.image.description="Python 3.9 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="3.9"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/python:3.9-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends python39 python39-pip curl git-core python39-wheel; zypper -n clean; rm -rf /var/log/*
ENV PYTHON_VERSION="%%py39_ver%%"
ENV PIP_VERSION="%%pip_ver%%"

RUN set -euo pipefail; ln -s /usr/bin/python3.9 /usr/local/bin/python3; \
    ln -s /usr/bin/pydoc3.9 /usr/local/bin/pydoc
