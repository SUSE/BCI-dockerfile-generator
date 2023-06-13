# SPDX-License-Identifier: MIT
#!BuildTag: bci/php-apache:8
#!BuildTag: bci/php-apache:8-%RELEASE%

FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.php-apache
LABEL org.opencontainers.image.title="SLE BCI PHP-APACHE 8 Container Image"
LABEL org.opencontainers.image.description="PHP-APACHE 8 based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="8"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/php-apache:8-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN set -euo pipefail; zypper -n in php8 php8-cli php-composer php8-curl php8-zip php8-zlib php8-phar php8-mbstring apache2-mod_php8; zypper -n clean; rm -rf /var/log/*
ENV PHP_VERSION="%%php_version%%"
ENV PHP_INI_DIR="/etc/php8/"
ENV PHPIZE_DEPS="php8-devel awk make"
ENV COMPOSER_VERSION="%%composer_version%%"
ENV APACHE_CONFDIR="/etc/apache2"
ENV APACHE_ENVVARS="/usr/sbin/envvars"

ENTRYPOINT ["docker-php-entrypoint"]
CMD ["apache2-foreground"]
COPY docker-php-source docker-php-entrypoint docker-php-ext-configure docker-php-ext-enable docker-php-ext-install /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-php-*

STOPSIGNAL SIGWINCH

# create our own apache2-foreground from the systemd startup script
RUN sed 's|^exec $apache_bin|exec $apache_bin -DFOREGROUND|' /usr/sbin/start_apache2 > /usr/local/bin/apache2-foreground
RUN chmod +x /usr/local/bin/apache2-foreground

# apache fails to start without its log folder
RUN mkdir -p /var/log/apache2

WORKDIR /srv/www/htdocs

EXPOSE 80
