"""Valkey container definition"""

import textwrap

from bci_build.container_attributes import TCP
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import _build_tag_prefix
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version

VALKEY_CONTAINERS = [
    ApplicationStackContainer(
        name="valkey",
        pretty_name="Persistent key-value database",
        custom_description=(
            "Valkey is an open-source high-performance key/value "
            "data store designed for a variety of workloads such as "
            "caching, message queuing and primary database use"
        ),
        from_target_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%valkey_version%%",
        version_in_uid=False,
        tag_version=format_version(
            valkey_version := get_pkg_version("valkey", os_version), ParseVersion.MINOR
        ),
        additional_versions=[format_version(valkey_version, ParseVersion.MAJOR)],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%valkey_version%%", package_name="valkey"
            )
        ],
        license="BSD-3-Clause",
        package_list=["valkey", "valkey-compat-redis"],
        entrypoint=["/usr/bin/valkey-server"],
        entrypoint_user="valkey",
        exposes_ports=[TCP(6379)],
        volumes=["/data"],
        build_stage_custom_end=generate_package_version_check(
            "valkey", valkey_version, ParseVersion.MINOR, use_target=True
        ),
        custom_end=textwrap.dedent(
            f"""
            {DOCKERFILE_RUN} install -o valkey -g valkey -m 750 -d /data
            WORKDIR /data
        """
        ),
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
