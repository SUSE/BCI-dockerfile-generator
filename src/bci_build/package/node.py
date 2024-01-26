"""Node.js BCI container"""
import datetime
from typing import Literal

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import _SUPPORTED_UNTIL_SLE
from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.package import SupportLevel

# see https://raw.githubusercontent.com/nodejs/Release/main/README.md
_NODEJS_SUPPORT_ENDS = {
    20: datetime.date(2026, 4, 30),
    # ... upstream is 2024/4/30 but SUSE ends earlier with SP5
    # see https://confluence.suse.com/display/SLE/Node.js
    18: _SUPPORTED_UNTIL_SLE[OsVersion.SP5],
    # upstream 2023/9/11 but SUSE extends end of general support SP4
    # see https://confluence.suse.com/display/SLE/Node.js
    16: _SUPPORTED_UNTIL_SLE[OsVersion.SP4],
}


def _get_node_kwargs(ver: Literal[16, 18, 20], os_version: OsVersion):
    return {
        "name": "nodejs",
        "os_version": os_version,
        "is_latest": ver == 20 and os_version in CAN_BE_LATEST_OS_VERSION,
        "supported_until": _NODEJS_SUPPORT_ENDS.get(ver, None),
        "package_name": f"nodejs-{ver}-image",
        "pretty_name": f"Node.js {ver} development",
        "additional_names": ["node"],
        "version": str(ver),
        "package_list": [
            f"nodejs{ver}",
            # devel dependencies:
            f"npm{ver}",
            "git-core",
            # dependency of nodejs:
            "update-alternatives",
        ],
        "env": {
            "NODE_VERSION": ver,
        },
    }


NODE_CONTAINERS = [
    LanguageStackContainer(
        **_get_node_kwargs(18, OsVersion.SP5), support_level=SupportLevel.L3
    ),
    LanguageStackContainer(
        **_get_node_kwargs(20, OsVersion.SP5), support_level=SupportLevel.L3
    ),
    LanguageStackContainer(
        **_get_node_kwargs(20, OsVersion.SP6), support_level=SupportLevel.L3
    ),
    LanguageStackContainer(**_get_node_kwargs(20, OsVersion.TUMBLEWEED)),
]
