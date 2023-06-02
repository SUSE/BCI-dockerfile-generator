# SPDX-License-Identifier: Apache-2.0
#!BuildTag: suse/grafana:%%grafana_version%%
#!BuildTag: suse/grafana:%%grafana_version%%-%RELEASE%
#!BuildTag: suse/grafana:latest
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.grafana
LABEL org.opencontainers.image.title="SLE Grafana Container Image"
LABEL org.opencontainers.image.description="Grafana based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%grafana_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/grafana:%%grafana_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends grafana; zypper -n clean; rm -rf /var/log/*
ENV GF_PATHS_DATA="/var/lib/grafana"
ENV GF_PATHS_HOME="/usr/share/grafana"
ENV GF_PATHS_LOGS="/var/log/grafana"
ENV GF_PATHS_PLUGINS="/var/lib/grafana/plugins"
ENV GF_PATHS_PROVISIONING="/etc/grafana/provisioning"

ENTRYPOINT ["/run.sh"]
EXPOSE 3000
COPY run.sh /run.sh
RUN set -euo pipefail; chmod +x /run.sh
        
VOLUME /var/lib/grafana
