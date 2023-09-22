# SPDX-License-Identifier: MIT
#!BuildTag: bci/nodejs:20
#!BuildTag: bci/nodejs:20-%RELEASE%
#!BuildTag: bci/node:20
#!BuildTag: bci/node:20-%RELEASE%
#!BuildName: bci-nodejs-20
#!BuildVersion: 15.6.20
FROM suse/sle15:15.6

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.nodejs
LABEL org.opencontainers.image.title="SLE BCI Node.js 20 development"
LABEL org.opencontainers.image.description="Node.js 20 development container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="20"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/nodejs:20-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.supportlevel.until="2026-04-30"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends nodejs20 npm20 git-core update-alternatives; zypper -n clean; rm -rf /var/log/*
ENV NODE_VERSION="20"

