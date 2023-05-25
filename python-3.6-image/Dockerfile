# SPDX-License-Identifier: MIT
#!BuildTag: bci/python:3.6
#!BuildTag: bci/python:3.6-%RELEASE%
#!BuildTag: bci/python:3
#!BuildTag: bci/python:3-%RELEASE%
#!BuildVersion: 15.4.3.6
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.python
LABEL org.opencontainers.image.title="SLE BCI Python 3.6 Container Image"
LABEL org.opencontainers.image.description="Python 3.6 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="3.6"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/python:3.6-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends python3-devel python3 python3-pip curl git-core python3-wheel; zypper -n clean; rm -rf /var/log/*
ENV PYTHON_VERSION="%%py36_ver%%"
ENV PIP_VERSION="%%pip_ver%%"

