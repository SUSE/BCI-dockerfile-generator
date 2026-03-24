"""Node.js BCI container"""

import datetime
from typing import Literal

from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import CAN_BE_LATEST_SLFO_OS_VERSION
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.replacement import Replacement

_NODE_VERSIONS = Literal[16, 18, 20, 21, 22, 23, 24, 25]

# see https://raw.githubusercontent.com/nodejs/Release/main/README.md
_NODEJS_SUPPORT_ENDS = {
    25: datetime.date(2026, 6, 1),
    # upstream 2028/4/30 but we pick general support of SL16.1
    24: datetime.date(2028, 11, 30),
    23: datetime.date(2025, 6, 1),
    # ... upstream ends 2027/4/30, SP7 goes until 2027-12-31 but we pick the shorter SLES16 date
    22: datetime.date(2027, 11, 30),
    21: datetime.date(2024, 6, 1),
    20: datetime.date(2026, 4, 30),
    # ... upstream is 2024/4/30 but SUSE ends earlier with SP5
    # see https://confluence.suse.com/display/SLE/Node.js
    18: _SUPPORTED_UNTIL_SLE[OsVersion.SP5],
    # upstream 2023/9/11 but SUSE extends end of general support SP4
    # see https://confluence.suse.com/display/SLE/Node.js
    16: _SUPPORTED_UNTIL_SLE[OsVersion.SP4],
}


def _get_node_kwargs(
    ver: _NODE_VERSIONS, os_version: OsVersion, build_flavor: str | None = None
):
    node_version_replacement = "%%nodejs_version%%"
    node_devel_deps = [f"npm{ver}"]
    return {
        "name": "nodejs",
        "os_version": os_version,
        # we label the newest LTS version as latest
        "is_latest": (
            ver == 24
            and os_version in CAN_BE_LATEST_SLFO_OS_VERSION
            and build_flavor != "micro"
        ),
        "supported_until": _NODEJS_SUPPORT_ENDS.get(ver),
        "use_build_flavor_in_tag": (build_flavor == "micro"),
        "package_name": f"nodejs-{ver}-image",
        "pretty_name": f"Node.js {ver} development",
        "from_target_image": (
            generate_from_image_tag(os_version, "bci-micro")
            if build_flavor == "micro"
            else None
        ),
        "additional_names": ["node"],
        "additional_versions": (
            [f"{ver}-{os_version.dist_id}"] if os_version.dist_id else []
        ),
        "version": node_version_replacement,
        "support_level": SupportLevel.L3,
        "tag_version": str(ver),
        "package_list": sorted(
            [
                f"nodejs{ver}",
            ]
            + (["update-alternatives"] if os_version.is_sle15 else [])
            + (node_devel_deps if build_flavor != "micro" else [])
            + os_version.common_devel_packages
        ),
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=node_version_replacement,
                package_name=f"nodejs{ver}",
            ),
        ],
        "env": {
            "NODE_VERSION": ver,
        },
    } | ({"build_flavor": build_flavor} if build_flavor else {})


NODE_CONTAINERS = [
    DevelopmentContainer(**_get_node_kwargs(node_version, os_version))
    for node_version, os_version in (
        (22, OsVersion.SP7),
        (22, OsVersion.SL16_0),
        (24, OsVersion.SL16_0),
        (24, OsVersion.SL16_1),
    )
] + [
    DevelopmentContainer(**_get_node_kwargs(24, OsVersion.TUMBLEWEED, build_flavor))
    for build_flavor in ("base", "micro")
]

NODE_CRATE = ContainerCrate(NODE_CONTAINERS)
