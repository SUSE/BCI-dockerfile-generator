# SPDX-License-Identifier: MIT
#!BuildTag: opensuse/postgres:13
#!BuildTag: opensuse/postgres:13-%RELEASE%
#!BuildTag: opensuse/postgres:%%pg_version%%

FROM opensuse/tumbleweed:latest

MAINTAINER openSUSE (https://www.opensuse.org/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.application.postgres
LABEL org.opencontainers.image.title="openSUSE Tumbleweed PostgreSQL 13 Container Image"
LABEL org.opencontainers.image.description="PostgreSQL 13 based on the openSUSE Tumbleweed Base Container Image."
LABEL org.opencontainers.image.version="13"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/postgres:13-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"

LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends postgresql13-server distribution-release; zypper -n clean; rm -rf /var/log/*
ENV LANG="en_US.utf8"
ENV PG_MAJOR="13"
ENV PG_VERSION="%%pg_version%%"
ENV PGDATA="/var/lib/postgresql/data"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["postgres"]
VOLUME /var/lib/postgresql/data
EXPOSE 5432
COPY docker-entrypoint.sh /usr/local/bin/
RUN set -euo pipefail; chmod +x /usr/local/bin/docker-entrypoint.sh; \
    ln -s su /usr/bin/gosu; \
    mkdir /docker-entrypoint-initdb.d; \
    sed -ri "s|^#?(listen_addresses)\s*=\s*\S+.*|\1 = '*'|" /usr/share/postgresql13/postgresql.conf.sample

STOPSIGNAL SIGINT
