# SPDX-License-Identifier: (LGPL-2.1+ AND GPL-2.0+)
#!BuildTag: suse/pcp:%%pcp_patch%%
#!BuildTag: suse/pcp:%%pcp_patch%%-%RELEASE%
#!BuildTag: suse/pcp:%%pcp_minor%%
#!BuildTag: suse/pcp:%%pcp_minor%%-%RELEASE%
#!BuildTag: suse/pcp:%%pcp_major%%
#!BuildTag: suse/pcp:%%pcp_major%%-%RELEASE%

FROM bci/bci-init:15.3

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.pcp
LABEL org.opencontainers.image.title="SLE Performance Co-Pilot (pcp) Container Image"
LABEL org.opencontainers.image.description="Performance Co-Pilot (pcp) container image based on the SLE Base Container Image. This container image is not supported when using a container runtime other than podman."
LABEL org.opencontainers.image.version="%%pcp_patch%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/suse/pcp:%%pcp_patch%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends pcp hostname shadow gettext-runtime util-linux-systemd; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/local/bin/container-entrypoint"]
CMD ["/usr/lib/systemd/systemd"]
VOLUME /var/log/pcp/pmlogger
EXPOSE 44321 44322 44323

RUN set -euo pipefail; mkdir -p /usr/share/container-scripts/pcp; mkdir -p /etc/sysconfig
COPY container-entrypoint healthcheck /usr/local/bin/
RUN set -euo pipefail; chmod +x /usr/local/bin/container-entrypoint /usr/local/bin/healthcheck
COPY pmproxy.conf.template 10-host_mount.conf.template /usr/share/container-scripts/pcp/
COPY pmcd pmlogger /etc/sysconfig/

# This can be removed after the pcp dependency on sysconfig is removed
RUN set -euo pipefail; systemctl disable wicked wickedd

HEALTHCHECK --start-period=30s --timeout=20s --interval=10s --retries=3     CMD /usr/local/bin/healthcheck
