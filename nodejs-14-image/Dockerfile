# SPDX-License-Identifier: MIT
#!BuildTag: bci/nodejs:14
#!BuildTag: bci/nodejs:14-%RELEASE%
#!BuildTag: bci/node:14
#!BuildTag: bci/node:14-%RELEASE%
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.nodejs
LABEL org.opencontainers.image.title="SLE BCI Node.js 14 Container Image"
LABEL org.opencontainers.image.description="Node.js 14 development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="14"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/nodejs:14-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends nodejs14 npm14 git-core update-alternatives distribution-release; zypper -n clean; rm -rf /var/log/*
ENV NODE_VERSION="14"

