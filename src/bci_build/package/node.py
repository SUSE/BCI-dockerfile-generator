"""Node.js BCI container"""

import datetime
from typing import Literal

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import _SUPPORTED_UNTIL_SLE
from bci_build.package import DevelopmentContainer
from bci_build.package import OsVersion
from bci_build.package import SupportLevel

_NODE_VERSIONS = Literal[16, 18, 20, 21, 22, 23, 24]

# see https://raw.githubusercontent.com/nodejs/Release/main/README.md
_NODEJS_SUPPORT_ENDS = {
    # upcoming LTS version ~ 2025-04
    24: datetime.date(2028, 4, 30),
    23: datetime.date(2025, 6, 1),
    22: datetime.date(2027, 4, 30),
    21: datetime.date(2024, 6, 1),
    20: datetime.date(2026, 4, 30),
    # ... upstream is 2024/4/30 but SUSE ends earlier with SP5
    # see https://confluence.suse.com/display/SLE/Node.js
    18: _SUPPORTED_UNTIL_SLE[OsVersion.SP5],
    # upstream 2023/9/11 but SUSE extends end of general support SP4
    # see https://confluence.suse.com/display/SLE/Node.js
    16: _SUPPORTED_UNTIL_SLE[OsVersion.SP4],
}


def _get_node_kwargs(ver: _NODE_VERSIONS, os_version: OsVersion):
    return {
        "name": "nodejs",
        "os_version": os_version,
        # we label the newest LTS version as latest
        "is_latest": ver == 20 and os_version in CAN_BE_LATEST_OS_VERSION,
        "supported_until": _NODEJS_SUPPORT_ENDS.get(ver),
        "package_name": f"nodejs-{ver}-image",
        "pretty_name": f"Node.js {ver} development",
        "additional_names": ["node"],
        "version": str(ver),
        "package_list": [
            f"nodejs{ver}",
            # devel dependencies:
            f"npm{ver}",
            # dependency of nodejs:
            "update-alternatives",
        ]
        + os_version.common_devel_packages,
        "env": {
            "NODE_VERSION": ver,
        },
    }


NODE_CONTAINERS = [
    DevelopmentContainer(
        **_get_node_kwargs(18, OsVersion.SP5), support_level=SupportLevel.L3
    ),
    DevelopmentContainer(
        **_get_node_kwargs(20, OsVersion.SP6), support_level=SupportLevel.L3
    ),
    DevelopmentContainer(**_get_node_kwargs(20, OsVersion.TUMBLEWEED)),
    DevelopmentContainer(**_get_node_kwargs(22, OsVersion.TUMBLEWEED)),
]
