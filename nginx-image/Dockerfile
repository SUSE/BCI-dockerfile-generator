# SPDX-License-Identifier: MIT
#!BuildTag: suse/nginx:%%nginx_version%%
#!BuildTag: suse/nginx:%%nginx_version%%-%RELEASE%
#!BuildTag: suse/nginx:latest
#!BuildName: suse-nginx-%%nginx_version%%
#!BuildVersion: 15.5
FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.application.nginx
LABEL org.opencontainers.image.title="SLE NGINX"
LABEL org.opencontainers.image.description="NGINX open source all-in-one load balancer, content cache and web server based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%nginx_version%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/suse/nginx:%%nginx_version%%-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="application"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in --no-recommends gawk nginx; zypper -n clean; rm -rf /var/log/*
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
EXPOSE 80
RUN set -euo pipefail; mkdir /docker-entrypoint.d
COPY [1-3]0-*.sh /docker-entrypoint.d/
COPY docker-entrypoint.sh /usr/local/bin
COPY index.html /srv/www/htdocs/
RUN set -euo pipefail; chmod +x /docker-entrypoint.d/*.sh /usr/local/bin/docker-entrypoint.sh
RUN set -euo pipefail; install -d -o nginx -g nginx -m 750 /var/log/nginx;     ln -sf /dev/stdout /var/log/nginx/access.log;     ln -sf /dev/stderr /var/log/nginx/error.log

STOPSIGNAL SIGQUIT
