# SPDX-License-Identifier: MIT
#!BuildTag: bci/python:3.11
#!BuildTag: bci/python:3.11-%RELEASE%
#!BuildTag: bci/python:3
#!BuildTag: bci/python:3-%RELEASE%
#!BuildTag: bci/python:latest
#!BuildVersion: 15.5.3.11
FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.python
LABEL org.opencontainers.image.title="SLE BCI Python 3.11 Container Image"
LABEL org.opencontainers.image.description="Python 3.11 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="3.11"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/python:3.11-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.supportlevel.until="2027-12-31"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends python311-devel python311 python311-pip curl git-core; zypper -n clean; rm -rf /var/log/*
ENV PYTHON_VERSION="%%py311_ver%%"
ENV PIP_VERSION="%%pip_ver%%"

RUN set -euo pipefail; ln -s /usr/bin/python3.11 /usr/local/bin/python3; \
    ln -s /usr/bin/pydoc3.11 /usr/local/bin/pydoc
