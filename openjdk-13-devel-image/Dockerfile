# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/bci/openjdk-devel:13
#!BuildTag: opensuse/bci/openjdk-devel:13-%RELEASE%

FROM opensuse/bci/openjdk:13

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.bci.openjdk.devel
LABEL org.opencontainers.image.title="openSUSE Tumbleweed BCI OpenJDK 13 Development Container Image"
LABEL org.opencontainers.image.description="Java 13 Development environment based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="13"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/bci/openjdk-devel:13-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends java-13-openjdk-devel git-core maven; zypper -n clean; rm -rf /var/log/*
ENV JAVA_BINDIR="/usr/lib64/jvm/java/bin"
ENV JAVA_HOME="/usr/lib64/jvm/java"
ENV JAVA_ROOT="/usr/lib64/jvm/java"
ENV JAVA_VERSION="13"

CMD ["/usr/bin/jshell"]
