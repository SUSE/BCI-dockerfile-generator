# SPDX-License-Identifier: MIT
#!BuildTag: suse/rmt-mariadb-client:%%mariadb_version%%
#!BuildTag: suse/rmt-mariadb-client:%%mariadb_version%%-%RELEASE%
#!BuildName: suse-rmt-mariadb-client-%%mariadb_version%%
#!BuildVersion: 15.6
FROM suse/sle15:15.6

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.rmt-mariadb-client
LABEL org.opencontainers.image.title="SLE MariaDB Client for SUSE RMT"
LABEL org.opencontainers.image.description="MariaDB Client for SUSE RMT container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%mariadb_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/rmt-mariadb-client:%%mariadb_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends mariadb-client; zypper -n clean; rm -rf /var/log/*
CMD ["mariadb"]
