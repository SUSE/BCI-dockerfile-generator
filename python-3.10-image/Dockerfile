# SPDX-License-Identifier: MIT
#!BuildTag: bci/python:3.10
#!BuildTag: bci/python:latest
#!BuildTag: bci/python:3.10-%RELEASE%
#!BuildTag: bci/python:3
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.python
LABEL org.opencontainers.image.title="SLE BCI Python 3.10 Container Image"
LABEL org.opencontainers.image.description="Python 3.10 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="3.10"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/python:3.10-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends python310 python310-pip curl git-core; zypper -n clean; rm -rf /var/log/*
ENV PYTHON_VERSION="%%py310_ver%%"
ENV PIP_VERSION="%%pip_ver%%"

RUN set -euo pipefail; ln -s /usr/bin/python3.10 /usr/local/bin/python3; \
    ln -s /usr/bin/pydoc3.10 /usr/local/bin/pydoc
