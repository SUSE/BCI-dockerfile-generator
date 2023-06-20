# SPDX-License-Identifier: MIT
#!BuildTag: suse/rmt-nginx:%%nginx_version%%
#!BuildTag: suse/rmt-nginx:%%nginx_version%%-%RELEASE%
#!BuildTag: suse/rmt-nginx:latest
#!BuildVersion: 15.5
FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.rmt-nginx
LABEL org.opencontainers.image.title="SLE RMT Nginx Container Image"
LABEL org.opencontainers.image.description="RMT Nginx based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%nginx_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/rmt-nginx:%%nginx_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends nginx distribution-release; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
EXPOSE 80
RUN set -euo pipefail; mkdir /docker-entrypoint.d
COPY 10-listen-on-ipv6-by-default.sh /docker-entrypoint.d/
COPY 20-envsubst-on-templates.sh /docker-entrypoint.d/
COPY 30-tune-worker-processes.sh /docker-entrypoint.d/
COPY docker-entrypoint.sh /
RUN set -euo pipefail; chmod +x /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
RUN set -euo pipefail; chmod +x /docker-entrypoint.d/20-envsubst-on-templates.sh
RUN set -euo pipefail; chmod +x /docker-entrypoint.d/30-tune-worker-processes.sh
RUN set -euo pipefail; chmod +x /docker-entrypoint.sh

COPY index.html /srv/www/htdocs/

RUN set -euo pipefail; mkdir /var/log/nginx
RUN set -euo pipefail; chown nginx:nginx /var/log/nginx
RUN set -euo pipefail; ln -sf /dev/stdout /var/log/nginx/access.log
RUN set -euo pipefail; ln -sf /dev/stderr /var/log/nginx/error.log

STOPSIGNAL SIGQUIT
