# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/rmt-mariadb-client:%%mariadb_version%%
#!BuildTag: opensuse/rmt-mariadb-client:latest
#!BuildTag: opensuse/rmt-mariadb-client:%%mariadb_version%%-%RELEASE%

FROM opensuse/tumbleweed:latest

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.application.rmt-mariadb-client
LABEL org.opencontainers.image.title="openSUSE Tumbleweed MariaDB Client Container Image"
LABEL org.opencontainers.image.description="MariaDB client for RMT, based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%mariadb_version%%"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/rmt-mariadb-client:%%mariadb_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends mariadb-client; zypper -n clean; rm -rf /var/log/*
CMD ["mariadb"]
