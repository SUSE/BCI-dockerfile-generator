"""Valkey container definition"""

import textwrap

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement
from bci_build.package import _build_tag_prefix

VALKEY_CONTAINERS = [
    ApplicationStackContainer(
        name="valkey",
        pretty_name="Persistent key-value database",
        custom_description=(
            "Valkey is a high-performance, open-source key-value "
            "data store designed for a variety of workloads, "
            "including caching, message queuing, and primary database use"
        ),
        from_target_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%valkey_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%redis_version%%", package_name="valkey"
            )
        ],
        license="Apache-2.0",
        package_list=["valkey", "valkey-compat-redis"],
        entrypoint=["/usr/bin/valkey-server"],
        entrypoint_user="valkey",
        exposes_tcp=[6379],
        custom_end=textwrap.dedent(
            f"""
            {DOCKERFILE_RUN} install -o valkey -g valkey -m 750 -d /data
            WORKDIR /data
        """
        ),
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
