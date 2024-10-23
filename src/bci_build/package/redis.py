"""Redis Advanced Key-Value Store Container definitions"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import _build_tag_prefix
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version

REDIS_CONTAINERS = [
    ApplicationStackContainer(
        name="redis",
        pretty_name="Advanced Key-Value Store",
        from_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%redis_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%redis_version%%",
                package_name="redis",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="BSD-3-Clause",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "redis",
                "util-linux",
            )
        ],
        config_sh_script=textwrap.dedent(
            """
            chown redis:redis /var/lib/redis
            """
        ),
        entrypoint_user="redis",
        cmd=["redis-server", "--protected-mode no", "--dir /var/lib/redis"],
        volumes=["/var/lib/redis"],
        exposes_ports=[6379],
        build_recipe_type=BuildType.KIWI,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
