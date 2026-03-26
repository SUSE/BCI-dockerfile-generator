"""Application Containers that are generated with the BCI tooling"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_SLFO_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion


def _envsubst_pkg_name(os_version: OsVersion) -> str:
    return "envsubst" if os_version == OsVersion.TUMBLEWEED else "gettext-runtime"


_NGINX_FILES = {}
for filename in (
    "docker-entrypoint.sh",
    "LICENSE",
    "20-envsubst-on-templates.sh",
    "30-tune-worker-processes.sh",
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
        "package_list": (
            [
                "curl",
                "gawk",
                "nginx",
                "findutils",
                _envsubst_pkg_name(os_version),
            ]
        )
        + (["libcurl-mini4"] if os_version.is_sl16 else []),
        "entrypoint": ["/usr/local/bin/docker-entrypoint.sh"],
        "from_target_image": generate_from_image_tag(os_version, "bci-micro"),
        "cmd": ["nginx", "-g", "daemon off;"],
        "build_recipe_type": BuildType.DOCKER,
        "extra_files": _NGINX_FILES,
        "support_level": SupportLevel.L3,
        "exposes_ports": [TCP(80)],
        "build_stage_custom_end": generate_package_version_check(
            "nginx", nginx_version, use_target=True
        ),
        "custom_end": textwrap.dedent(f"""
            {DOCKERFILE_RUN} mkdir /docker-entrypoint.d
            COPY [1-3]0-*.sh /docker-entrypoint.d/
            COPY docker-entrypoint.sh /usr/local/bin
            COPY index.html /srv/www/htdocs/
            {DOCKERFILE_RUN} chmod +x /docker-entrypoint.d/*.sh /usr/local/bin/docker-entrypoint.sh
            {DOCKERFILE_RUN} install -d -o nginx -g nginx -m 750 /var/log/nginx; \
                ln -sf /dev/stdout /var/log/nginx/access.log; \
                ln -sf /dev/stderr /var/log/nginx/error.log
            STOPSIGNAL SIGQUIT"""),
    }

    return kwargs


NGINX_CONTAINERS = [
    ApplicationStackContainer(
        name="nginx",
        pretty_name="NGINX",
        custom_description="NGINX open source all-in-one load balancer, content cache and web server {based_on_container}.",
        **_get_nginx_kwargs(os_version),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
