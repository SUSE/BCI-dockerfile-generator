import enum
from itertools import product

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import _BASH_SET
from bci_build.package import DevelopmentContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement
from bci_build.package import SupportLevel


@enum.unique
class PhpVariant(enum.Enum):
    cli = "PHP"
    apache = "PHP-Apache"
    fpm = "PHP-FPM"

    def __str__(self) -> str:
        return str(self.value)


def _php_entrypoint(variant: PhpVariant) -> str:
    cmd: str = {
        PhpVariant.cli: "php",
        PhpVariant.apache: "apache2-foreground",
        PhpVariant.fpm: "php-fpm",
    }[variant]
    return f"""#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
if [ "${{1#-}}" != "$1" ]; then
	set -- {cmd} "$@"
fi

exec "$@"
"""


_EMPTY_SCRIPT = """#!/bin/sh
echo "This script is not required in this PHP container."
"""

_PHP_VERSIONS = (8,)
_LATEST_PHP_VERSION = sorted(_PHP_VERSIONS, reverse=True)[0]


def _create_php_bci(
    os_version: OsVersion, php_variant: PhpVariant, php_version: int
) -> DevelopmentContainer:
    common_end = """COPY docker-php-source docker-php-entrypoint docker-php-ext-configure docker-php-ext-enable docker-php-ext-install /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-php-*
"""
    assert php_version in _PHP_VERSIONS, f"PHP version {php_version} is not supported"

    if php_variant == PhpVariant.apache:
        extra_pkgs = [f"apache2-mod_php{php_version}"]
        extra_env = {
            "APACHE_CONFDIR": "/etc/apache2",
        }
        # Tumbleweed apache has dropped envvars
        if os_version != OsVersion.TUMBLEWEED:
            extra_env["APACHE_ENVVARS"] = "/usr/sbin/envvars"
        cmd = ["apache2-foreground"]
        custom_end = (
            common_end
            + """
STOPSIGNAL SIGWINCH

# create our own apache2-foreground from the systemd startup script
RUN sed 's|^exec $apache_bin|exec $apache_bin -DFOREGROUND|' /usr/sbin/start_apache2 > /usr/local/bin/apache2-foreground
RUN chmod +x /usr/local/bin/apache2-foreground

# apache fails to start without its log folder
RUN mkdir -p /var/log/apache2

WORKDIR /srv/www/htdocs

EXPOSE 80
"""
        )
    elif php_variant == PhpVariant.fpm:
        extra_pkgs = [f"php{php_version}-fpm"]
        extra_env = {}
        cmd = ["php-fpm"]
        custom_end = (
            common_end
            + """WORKDIR /srv/www/htdocs

"""
            + DOCKERFILE_RUN
            + r""" \
	cd /etc/php8/fpm/; \
        test -e php-fpm.d/www.conf.default && cp -p php-fpm.d/www.conf.default php-fpm.d/www.conf; \
        test -e php-fpm.conf.default && cp -p php-fpm.conf.default php-fpm.conf; \
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
"""
        )
    else:
        extra_pkgs = (
            []
            if os_version not in (OsVersion.TUMBLEWEED, OsVersion.SP6)
            else [f"php{php_version}-readline"]
        )
        extra_env = {}
        cmd = ["php", "-a"]
        custom_end = common_end

    return DevelopmentContainer(
        name=str(php_variant).lower(),
        no_recommends=False,
        version=php_version,
        pretty_name=f"{str(php_variant)} {php_version}",
        package_name=f"{str(php_variant).lower()}{php_version}-image",
        os_version=os_version,
        is_latest=php_version == _LATEST_PHP_VERSION
        and os_version in CAN_BE_LATEST_OS_VERSION,
        package_list=[
            f"php{php_version}",
            f"php{php_version}-cli",
            "php-composer2",
            f"php{php_version}-curl",
            f"php{php_version}-zip",
            f"php{php_version}-zlib",
            f"php{php_version}-phar",
            f"php{php_version}-mbstring",
        ]
        + os_version.lifecycle_data_pkg
        + extra_pkgs,
        replacements_via_service=[
            Replacement("%%composer_version%%", package_name="php-composer2"),
            Replacement("%%php_version%%", package_name=f"php{php_version}"),
        ],
        cmd=cmd,
        support_level=SupportLevel.L3,
        entrypoint=["docker-php-entrypoint"],
        env={
            "PHP_VERSION": "%%php_version%%",
            "PHP_INI_DIR": f"/etc/php{php_version}/",
            "PHPIZE_DEPS": f"php{php_version}-devel awk make findutils",
            "COMPOSER_VERSION": "%%composer_version%%",
            **extra_env,
        },
        extra_files={
            "docker-php-entrypoint": _php_entrypoint(php_variant),
            "docker-php-source": _EMPTY_SCRIPT,
            "docker-php-ext-configure": _EMPTY_SCRIPT,
            "docker-php-ext-enable": _EMPTY_SCRIPT,
            "docker-php-ext-install": f"""#!/bin/bash
{_BASH_SET}

extensions=()

for ext in $@; do
    [[ "$ext" =~ ^- ]] || extensions+=("php{php_version}-$ext")
done

zypper -n in ${{extensions[*]}}
""",
        },
        custom_end=custom_end,
    )


PHP_CONTAINERS = [
    _create_php_bci(os_version, variant, 8)
    for os_version, variant in product(
        (OsVersion.SP5, OsVersion.SP6, OsVersion.TUMBLEWEED),
        (PhpVariant.cli, PhpVariant.apache, PhpVariant.fpm),
    )
]
