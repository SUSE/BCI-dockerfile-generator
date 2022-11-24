# SPDX-License-Identifier: MIT
#!BuildTag: suse/blackbox_exporter:%%blackbox_exporter_version%%
#!BuildTag: suse/blackbox_exporter:%%blackbox_exporter_version%%-%RELEASE%

FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.blackbox_exporter
LABEL org.opencontainers.image.title="SLE Blackbox Exporter Container Image"
LABEL org.opencontainers.image.description="Blackbox Exporter based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%blackbox_exporter_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/suse/blackbox_exporter:%%blackbox_exporter_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends prometheus-blackbox_exporter; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/bin/blackbox_exporter"]
EXPOSE 9115
