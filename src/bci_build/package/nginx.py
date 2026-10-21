"""Application Containers that are generated with the BCI tooling"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_SLFO_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_SLFO_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import StableUser
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion


def _envsubst_pkg_name(os_version: OsVersion) -> str:
    return "envsubst" if os_version == OsVersion.TUMBLEWEED else "gettext-runtime"


_NGINX_FILES = {}
for filename in (
    "docker-entrypoint.sles.sh",
    "LICENSE",
    "20-envsubst-on-templates.sh",
    "30-tune-worker-processes.sh",
    "40-unprivileged-mode.sh",
    "index.html",
):
    _NGINX_FILES[filename] = (Path(__file__).parent / "nginx" / filename).read_bytes()


def _get_nginx_kwargs(os_version: OsVersion):
    nginx_version = get_pkg_version("nginx", os_version)

    kwargs = {
        "os_version": os_version,
        "is_latest": os_version in CAN_BE_LATEST_SLFO_OS_VERSION,
        "version": nginx_version,
        "version_in_uid": False,
        # backward compatibility with SL15
        "is_singleton_image": (os_version not in (OsVersion.SP7,)),
        "replacements_via_service": [
            Replacement(
                regex_in_build_description="%%nginx_version%%",
                package_name="nginx",
                parse_version=ParseVersion.MINOR,
            )
        ],
        "package_list": sorted(
            [
                "curl",
                "gawk",
                "nginx",
                "findutils",
                _envsubst_pkg_name(os_version),
                "sed",
                "grep",
            ]
            + os_version.fips_compatibility_packages
            + (["libcurl-mini4"] if os_version.is_sl16 else [])
        ),
        "entrypoint": ["/usr/local/bin/docker-entrypoint.sh"],
        "from_target_image": generate_from_image_tag(os_version, "bci-micro"),
        "cmd": ["nginx", "-g", "daemon off;"],
        "build_recipe_type": BuildType.DOCKER,
        "extra_files": _NGINX_FILES,
        "support_level": SupportLevel.L3,
        "exposes_ports": [TCP(80)],
        "min_release_counter": {OsVersion.SL16_1: 30},
        "user_chown": (
            StableUser(
                user_name="nginx",
                group_name="nginx",
            )
        ),
        "build_stage_custom_end": generate_package_version_check(
            "nginx", nginx_version, use_target=True
        )
        + textwrap.dedent(f"""
            {DOCKERFILE_RUN} mkdir /target/docker-entrypoint.d
            COPY [1-4]0-*.sh /target/docker-entrypoint.d/
            COPY docker-entrypoint.sles.sh /target/usr/local/bin/docker-entrypoint.sh
            COPY index.html /target/srv/www/htdocs/
            {DOCKERFILE_RUN} \\
                chmod +x /target/docker-entrypoint.d/*.sh \\
                         /target/usr/local/bin/docker-entrypoint.sh
            {DOCKERFILE_RUN} cp /target/etc/nginx/nginx.conf.default /target/etc/nginx/nginx.conf.non-root
            {DOCKERFILE_RUN} \\
                sed -i 's/listen\\s*80;/listen 8080;/g' /target/etc/nginx/nginx.conf.non-root; \\
                sed -i -e '/^[[:space:]]*user[[:space:]]/d' /target/etc/nginx/nginx.conf.non-root; \\
                sed -i -e 's,^#\\?\\s*pid\\s\\+.*;$,pid /tmp/nginx.pid;,' /target/etc/nginx/nginx.conf.non-root; \\
                sed -i "/http {{/a\\    client_body_temp_path /tmp/nginx/client_temp;" /target/etc/nginx/nginx.conf.non-root; \\
                sed -i "/http {{/a\\    proxy_temp_path /tmp/nginx/proxy_temp;" /target/etc/nginx/nginx.conf.non-root; \\
                sed -i "/http {{/a\\    fastcgi_temp_path /tmp/nginx/fastcgi_temp;" /target/etc/nginx/nginx.conf.non-root; \\
                sed -i "/http {{/a\\    uwsgi_temp_path /tmp/nginx/uwsgi_temp;" /target/etc/nginx/nginx.conf.non-root; \\
                sed -i "/http {{/a\\    scgi_temp_path /tmp/nginx/scgi_temp;" /target/etc/nginx/nginx.conf.non-root
            {DOCKERFILE_RUN} chmod o+rx /target/var/log/nginx
            {DOCKERFILE_RUN} \\
                ln -sf /dev/stdout /target/var/log/nginx/access.log; \\
                ln -sf /dev/stderr /target/var/log/nginx/error.log"""),
        "custom_end": "STOPSIGNAL SIGQUIT",
    }

    return kwargs


NGINX_CONTAINERS = [
    ApplicationStackContainer(
        name="nginx",
        pretty_name="NGINX",
        custom_description="NGINX open source all-in-one load balancer, content cache and web server {based_on_container}.",
        **_get_nginx_kwargs(os_version),
    )
    for os_version in ALL_NONBASE_SLFO_OS_VERSIONS
]
