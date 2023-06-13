# SPDX-License-Identifier: MIT
#!BuildTag: bci/openjdk:17
#!BuildTag: bci/openjdk:17-%RELEASE%

FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.openjdk
LABEL org.opencontainers.image.title="SLE BCI OpenJDK 17 Runtime Container Image"
LABEL org.opencontainers.image.description="Java 17 runtime based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="17"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/openjdk:17-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends java-17-openjdk; zypper -n clean; rm -rf /var/log/*
ENV JAVA_BINDIR="/usr/lib64/jvm/java-17-openjdk-17/bin"
ENV JAVA_HOME="/usr/lib64/jvm/java-17-openjdk-17"
ENV JAVA_ROOT="/usr/lib64/jvm/java-17-openjdk-17"
ENV JAVA_VERSION="17"

RUN set -euo pipefail; [ -d $JAVA_HOME ]; [ -d $JAVA_BINDIR ]; [ -f "$JAVA_BINDIR/java" ] && [ -x "$JAVA_BINDIR/java" ]
