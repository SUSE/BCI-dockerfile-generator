from jinja2 import Template

DOCKER_PHP_ENTRYPOINT = Template(
    """#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
if [ "${1#-}" != "$1" ]; then
	set -- {% if variant == 'cli' %}php{% elif variant == 'apache' %}apache2-foreground{% elif variant == 'fpm' %}php-fpm{% endif %} "$@"
fi

exec "$@"
"""
)


DOCKER_PHP_SOURCE = Template(
    """#!/bin/sh
set -euo pipefail

dir=/usr/src/php

usage() {
	echo "usage: $0 COMMAND"
	echo
	echo "Manage php source tarball lifecycle."
	echo
	echo "Commands:"
	echo "   extract  extract php source tarball into directory $dir if not already done."
	echo "   delete   delete extracted php source located into $dir if not already done."
	echo
}

case "$1" in
	extract)
		mkdir -p "$dir"
		if [ ! -f "$dir/.docker-extracted" ]; then
			{{ php_package.prep_section }}
			touch "$dir/.docker-extracted"
		fi
		;;

	delete)
		rm -rf "$dir"
		;;

	*)
		usage
		exit 1
		;;
esac
"""
)


DOCKER_PHP_EXT_CONFIGURE = Template(
    r"""#!/bin/sh
set -e

# prefer user supplied CFLAGS, but default to our PHP_CFLAGS
: ${CFLAGS:=$PHP_CFLAGS}
: ${CPPFLAGS:=$PHP_CPPFLAGS}
: ${LDFLAGS:=$PHP_LDFLAGS}
export CFLAGS CPPFLAGS LDFLAGS

srcExists=
if [ -d /usr/src/php ]; then
	srcExists=1
fi
docker-php-source extract
if [ -z "$srcExists" ]; then
	touch /usr/src/php/.docker-delete-me
fi

cd /usr/src/php/php-{{ php_package.version }}/ext

usage() {
	echo "usage: $0 ext-name [configure flags]"
	echo "   ie: $0 gd --with-jpeg-dir=/usr/local/something"
	echo
	echo 'Possible values for ext-name:'
	find . \
			-mindepth 2 \
			-maxdepth 2 \
			-type f \
			-name 'config.m4' \
		| xargs -n1 dirname \
		| xargs -n1 basename \
		| sort \
		| xargs
	echo
	echo 'Some of the above modules are already compiled into PHP; please check'
	echo 'the output of "php -i" to see which modules are already loaded.'
}

ext="$1"
if [ -z "$ext" ] || [ ! -d "$ext" ]; then
	usage >&2
	exit 1
fi
shift

cd "$ext"
phpize
./configure --enable-option-checking=fatal "$@"
"""
)


DOCKER_PHP_EXT_INSTALL = Template(
    r"""#!/bin/sh
set -e

# prefer user supplied CFLAGS, but default to our PHP_CFLAGS
: ${CFLAGS:=$PHP_CFLAGS}
: ${CPPFLAGS:=$PHP_CPPFLAGS}
: ${LDFLAGS:=$PHP_LDFLAGS}
export CFLAGS CPPFLAGS LDFLAGS

srcExists=
if [ -d /usr/src/php ]; then
	srcExists=1
fi
docker-php-source extract
if [ -z "$srcExists" ]; then
	touch /usr/src/php/.docker-delete-me
fi

cd /usr/src/php/php-{{ php_package.version }}/ext

usage() {
	echo "usage: $0 [-jN] [--ini-name file.ini] ext-name [ext-name ...]"
	echo "   ie: $0 gd mysqli"
	echo "       $0 pdo pdo_mysql"
	echo "       $0 -j5 gd mbstring mysqli pdo pdo_mysql shmop"
	echo
	echo 'if custom ./configure arguments are necessary, see docker-php-ext-configure'
	echo
	echo 'Possible values for ext-name:'
	find . \
			-mindepth 2 \
			-maxdepth 2 \
			-type f \
			-name 'config.m4' \
		| xargs -n1 dirname \
		| xargs -n1 basename \
		| sort \
		| xargs
	echo
	echo 'Some of the above modules are already compiled into PHP; please check'
	echo 'the output of "php -i" to see which modules are already loaded.'
}

opts="$(getopt -o 'h?j:' --long 'help,ini-name:,jobs:' -- "$@" || { usage >&2 && false; })"
eval set -- "$opts"

j=1
iniName=
while true; do
	flag="$1"
	shift
	case "$flag" in
		--help|-h|'-?') usage && exit 0 ;;
		--ini-name) iniName="$1" && shift ;;
		--jobs|-j) j="$1" && shift ;;
		--) break ;;
		*)
			{
				echo "error: unknown flag: $flag"
				usage
			} >&2
			exit 1
			;;
	esac
done

exts=
for ext; do
	if [ -z "$ext" ]; then
		continue
	fi
	if [ ! -d "$ext" ]; then
		echo >&2 "error: $PWD/$ext does not exist"
		echo >&2
		usage >&2
		exit 1
	fi
	exts="$exts $ext"
done

if [ -z "$exts" ]; then
	usage >&2
	exit 1
fi

popDir="$PWD"
for ext in $exts; do
	cd "$ext"

	[ -e Makefile ] || docker-php-ext-configure "$ext"

	make -j"$j"

	if ! php -n -d 'display_errors=stderr' -r 'exit(ZEND_DEBUG_BUILD ? 0 : 1);' > /dev/null; then
		# only "strip" modules if we aren't using a debug build of PHP
		# (none of our builds are debug builds, but PHP might be recompiled with "--enable-debug" configure option)
		# https://github.com/docker-library/php/issues/1268

		find modules \
			-maxdepth 1 \
			-name '*.so' \
			-exec sh -euxc ' \
				strip --strip-all "$@" || :
			' -- '{}' +
	fi

	make -j"$j" install

	find modules \
		-maxdepth 1 \
		-name '*.so' \
		-exec basename '{}' ';' \
			| xargs -r docker-php-ext-enable ${iniName:+--ini-name "$iniName"}

	make -j"$j" clean

	cd "$popDir"
done

if [ -e /usr/src/php/.docker-delete-me ]; then
	docker-php-source delete
fi
"""
)


DOCKERFILE_END = Template(
    r"""WORKDIR /usr/src/
#!RemoteAssetUrl: {{ php_package.php_url }}
COPY php-{{ php_package.version }}.tar.xz .
#!RemoteAssetUrl: {{ php_package.php_asc_url }}
COPY php-{{ php_package.version }}.tar.xz.asc .
COPY README.macros .
{%- for patch in php_package.patches.values() %}
COPY {{ patch }} .
{%- endfor %}
COPY docker-php-source docker-php-entrypoint docker-php-ext-configure docker-php-ext-enable docker-php-ext-install /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-php-*

RUN set -euo pipefail; \
    zypper -n in --no-recommends \
       php{{ php_major_version }}-cli \
       {% if variant == "fpm" %}php{{ php_major_version }}-fpm{% elif variant == "apache" %}apache2-mod_php{{ php_major_version }}{% endif %} \
       php-composer \
       php{{ php_major_version }}-curl \
       php{{ php_major_version }}-zip \
       php{{ php_major_version }}-zlib \
       php{{ php_major_version }}-phar \
       php{{ php_major_version }}-mbstring \
       curl \
       git-core \
       distribution-release \
       tar \
       xz \
       patch \
       sed \
       find \
       binutils; \
    zypper -n clean; \
    rm -rf /var/log/*

ENV PHP_URL="{{ php_package.php_url }}" PHP_ASC_URL="{{ php_package.php_asc_url }}"
ENV PHP_SHA256="{{ php_package.archive_hash }}"
ENV GPG_KEYS="{{ php_package.gpg_keys | join(' ') }}"
ENV PHP_INI_DIR="/etc/php{{ php_major_version }}/"
ENV PHPIZE_DEPS="php{{ php_major_version }}-devel autoconf gawk gcc make file"
ENV PHP_VERSION="{{ php_package.version }}"
ENV COMPOSER_VERSION="%%composer_version%%"
ENV PHP_CFLAGS="{{ php_package.cflags }}"
ENV PHP_CPPFLAGS="{{ php_package.cxxflags }}"
ENV PHP_LDFLAGS="{{ php_package.ldflags }}"

ENTRYPOINT ["docker-php-entrypoint"]
CMD {% if variant == "cli" %}["php", "-a"]{% elif variant == "apache" %}["apache2-foreground"]{% elif variant == "fpm" %}["php-fpm"]{% endif %}

{% if variant == "apache" %}

ENV APACHE_CONFDIR /etc/apache2
ENV APACHE_ENVVARS /usr/sbin/envvars

STOPSIGNAL SIGWINCH

# create our own apache2-foreground from the systemd startup script
RUN cat /usr/sbin/start_apache2 | sed 's|^exec $apache_bin|exec $apache_bin -DFOREGROUND|' > /usr/local/bin/apache2-foreground
RUN chmod +x /usr/local/bin/apache2-foreground

# apache fails to start without its log folder
RUN mkdir -p /var/log/apache2

WORKDIR /srv/www/htdocs

EXPOSE 80
{% elif variant == "fpm" %}
WORKDIR /srv/www/htdocs

RUN set -eux; \
	cd /etc/php8/fpm/; \
        cp php-fpm.d/www.conf.default php-fpm.d/www.conf; \
        cp php-fpm.conf.default php-fpm.conf; \
	{ \
		echo '[global]'; \
		echo 'error_log = /proc/self/fd/2'; \
		echo; echo '; https://github.com/docker-library/php/pull/725#issuecomment-443540114'; echo 'log_limit = 8192'; \
		echo; \
		echo '[www]'; \
		echo '; if we send this to /proc/self/fd/1, it never appears'; \
		echo 'access.log = /proc/self/fd/2'; \
		echo; \
		echo 'clear_env = no'; \
		echo; \
		echo '; Ensure worker stdout and stderr are sent to the main error log.'; \
		echo 'catch_workers_output = yes'; \
		echo 'decorate_workers_output = no'; \
	} | tee php-fpm.d/docker.conf; \
	{ \
		echo '[global]'; \
		echo 'daemonize = no'; \
	} | tee php-fpm.d/zz-docker.conf

# Override stop signal to stop process gracefully
# https://github.com/php/php-src/blob/17baa87faddc2550def3ae7314236826bc1b1398/sapi/fpm/php-fpm.8.in#L163
STOPSIGNAL SIGQUIT

EXPOSE 9000
{% endif %}
"""
)
