# SPDX-License-Identifier: MIT
#!BuildTag: bci/bci-init:%OS_VERSION_ID_SP%
#!BuildTag: bci/bci-init:%OS_VERSION_ID_SP%.%RELEASE%
#!BuildTag: bci/bci-init:latest
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.init
LABEL org.opencontainers.image.title="SLE BCI %OS_VERSION_NO_DASH% Init Container Image"
LABEL org.opencontainers.image.description="Systemd environment for containers based on the SLE Base Container Image. This container is not supported when using container runtime other than podman."
LABEL org.opencontainers.image.version="%OS_VERSION_ID_SP%.%RELEASE%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/bci-init:%OS_VERSION_ID_SP%.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="l3"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix
LABEL usage="This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."

RUN set -euo pipefail; zypper -n in --no-recommends systemd gzip; zypper -n clean; rm -rf /var/log/*
CMD ["/usr/lib/systemd/systemd"]
RUN systemctl disable getty@tty1.service
HEALTHCHECK --interval=5s --timeout=5s --retries=5     CMD ["/usr/bin/systemctl", "is-active", "multi-user.target"]
