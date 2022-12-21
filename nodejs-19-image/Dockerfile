# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/bci/nodejs:19
#!BuildTag: opensuse/bci/nodejs:19-%RELEASE%
#!BuildTag: opensuse/bci/nodejs:latest
#!BuildTag: opensuse/bci/node:19
#!BuildTag: opensuse/bci/node:19-%RELEASE%
#!BuildTag: opensuse/bci/node:latest

FROM opensuse/tumbleweed:latest

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.bci.nodejs
LABEL org.opencontainers.image.title="openSUSE Tumbleweed BCI Node.js 19 Container Image"
LABEL org.opencontainers.image.description="Node.js 19 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="19"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/bci/nodejs:19-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends nodejs19 npm19 git-core update-alternatives distribution-release; zypper -n clean; rm -rf /var/log/*
ENV NODE_VERSION="19"

