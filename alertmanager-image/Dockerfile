# SPDX-License-Identifier: MIT
#!BuildTag: suse/alertmanager:%%alertmanager_version%%
#!BuildTag: suse/alertmanager:latest
#!BuildTag: suse/alertmanager:%%alertmanager_version%%-%RELEASE%

FROM opensuse/tumbleweed:latest

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.alertmanager
LABEL org.opencontainers.image.title="SLE Alertmanager Container Image"
LABEL org.opencontainers.image.description="Alertmanager based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%alertmanager_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/suse/alertmanager:%%alertmanager_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends golang-github-prometheus-alertmanager; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/bin/prometheus-alertmanager"]
VOLUME /var/lib/prometheus/alertmanager
EXPOSE 9093
