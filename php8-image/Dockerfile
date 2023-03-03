# SPDX-License-Identifier: MIT
#!BuildTag: bci/php:8
#!BuildTag: bci/php:8-%RELEASE%

FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.php
LABEL org.opencontainers.image.title="SLE BCI PHP 8 Container Image"
LABEL org.opencontainers.image.description="PHP 8 based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="8"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opensuse.reference="registry.suse.com/bci/php:8-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="beta"
# endlabelprefix

RUN set -euo pipefail; zypper -n in php8 php8-cli php-composer php8-curl php8-zip php8-zlib php8-phar php8-mbstring; zypper -n clean; rm -rf /var/log/*
ENV PHP_VERSION="%%php_version%%"
ENV PHP_INI_DIR="/etc/php8/"
ENV PHPIZE_DEPS="php8-devel"
ENV COMPOSER_VERSION="%%composer_version%%"

ENTRYPOINT ["docker-php-entrypoint"]
CMD ["php", "-a"]
COPY docker-php-source docker-php-entrypoint docker-php-ext-configure docker-php-ext-enable docker-php-ext-install /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-php-*
