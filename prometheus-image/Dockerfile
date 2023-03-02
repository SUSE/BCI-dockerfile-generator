# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/prometheus:%%prometheus_version%%
#!BuildTag: opensuse/prometheus:%%prometheus_version%%-%RELEASE%
#!BuildTag: opensuse/prometheus:latest

FROM opensuse/tumbleweed:latest

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.application.prometheus
LABEL org.opencontainers.image.title="openSUSE Tumbleweed Prometheus Container Image"
LABEL org.opencontainers.image.description="Prometheus based on the openSUSE Tumbleweed Base Container Image."
LABEL org.opencontainers.image.version="%%prometheus_version%%"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/prometheus:%%prometheus_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends golang-github-prometheus-prometheus; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/bin/prometheus"]
VOLUME /var/lib/prometheus
EXPOSE 9090
