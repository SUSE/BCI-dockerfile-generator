# SPDX-License-Identifier: MIT
#!BuildTag: suse/alertmanager:%%alertmanager_version%%
#!BuildTag: suse/alertmanager:%%alertmanager_version%%-%RELEASE%
#!BuildName: suse-alertmanager-%%alertmanager_version%%
#!BuildVersion: 15.6
FROM suse/sle15:15.6

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.alertmanager
LABEL org.opencontainers.image.title="SLE Alertmanager"
LABEL org.opencontainers.image.description="Alertmanager container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%alertmanager_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/alertmanager:%%alertmanager_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends golang-github-prometheus-alertmanager; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/bin/prometheus-alertmanager"]
EXPOSE 9093

VOLUME /var/lib/prometheus/alertmanager
