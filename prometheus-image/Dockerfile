# SPDX-License-Identifier: MIT
#!BuildTag: suse/prometheus:%%prometheus_version%%
#!BuildTag: suse/prometheus:%%prometheus_version%%-%RELEASE%

FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.prometheus
LABEL org.opencontainers.image.title="SLE Prometheus Container Image"
LABEL org.opencontainers.image.description="Prometheus based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%prometheus_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/prometheus:%%prometheus_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends golang-github-prometheus-prometheus; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/bin/prometheus"]
EXPOSE 9090

VOLUME /var/lib/prometheus
