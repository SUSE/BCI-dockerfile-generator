# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/bci/openjdk-devel:15
#!BuildTag: opensuse/bci/openjdk-devel:15-%RELEASE%

FROM opensuse/bci/openjdk:15

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.bci.openjdk.devel
LABEL org.opencontainers.image.title="openSUSE Tumbleweed BCI OpenJDK 15 Development Container Image"
LABEL org.opencontainers.image.description="Java 15 Development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="15"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/bci/openjdk-devel:15-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL org.opensuse.lifecycle-url="https://en.opensuse.org/Lifetime"
LABEL org.opensuse.release-stage="released"

# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends java-15-openjdk-devel git-core maven; zypper -n clean; rm -rf /var/log/*
ENV JAVA_BINDIR="/usr/lib64/jvm/java-15-openjdk-15/bin"
ENV JAVA_HOME="/usr/lib64/jvm/java-15-openjdk-15"
ENV JAVA_ROOT="/usr/lib64/jvm/java-15-openjdk-15"
ENV JAVA_VERSION="15"

CMD ["/usr/bin/jshell"]
RUN set -euo pipefail; [ -d $JAVA_HOME ]; [ -d $JAVA_BINDIR ]; [ -f "$JAVA_BINDIR/java" ] && [ -x "$JAVA_BINDIR/java" ]
