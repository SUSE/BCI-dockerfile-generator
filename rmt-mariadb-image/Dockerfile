# SPDX-License-Identifier: MIT
#!BuildTag: suse/rmt-mariadb:%%mariadb_version%%
#!BuildTag: suse/rmt-mariadb:%%mariadb_version%%-%RELEASE%
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.rmt-mariadb
LABEL org.opencontainers.image.title="SLE MariaDB Server Container Image"
LABEL org.opencontainers.image.description="MariaDB server for RMT, based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%mariadb_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/rmt-mariadb:%%mariadb_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends mariadb mariadb-tools gawk timezone util-linux; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["mariadbd"]
EXPOSE 3306
RUN set -euo pipefail; mkdir /docker-entrypoint-initdb.d

# docker-entrypoint from https://github.com/MariaDB/mariadb-docker.git
COPY docker-entrypoint.sh /usr/local/bin/
RUN set -euo pipefail; chmod 755 /usr/local/bin/docker-entrypoint.sh
RUN set -euo pipefail; ln -s usr/local/bin/docker-entrypoint.sh / # backwards compat

RUN set -euo pipefail; sed -i 's#gosu mysql#su mysql -s /bin/bash -m#g' /usr/local/bin/docker-entrypoint.sh

# Ensure all logs goes to stdout
RUN set -euo pipefail; sed -i 's/^log/#log/g' /etc/my.cnf

# Disable binding to localhost only, doesn't make sense in a container
RUN set -euo pipefail; sed -i -e 's|^\(bind-address.*\)|#\1|g' /etc/my.cnf

RUN set -euo pipefail; mkdir /run/mysql

VOLUME /var/lib/mysql
