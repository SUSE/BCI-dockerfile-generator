"""Build description for the GCC Container Images"""

from typing import Literal

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import DevelopmentContainer
from bci_build.package import OsVersion
from bci_build.package import Replacement

_GCC_VERSIONS = Literal[7, 12, 13, 14]


def _is_latest_gcc(os_version: OsVersion, gcc_version: _GCC_VERSIONS) -> bool:
    if os_version == OsVersion.TUMBLEWEED and gcc_version == 14:
        return True
    # FIXME: os_version.is_sles
    if os_version in (OsVersion.SP6, OsVersion.SP5) and gcc_version == 13:
        return True
    # if os_version in (OsVersion.SLCC_DEVELOPMENT, OsVersion.SLCC_PRODUCTION):
    #     assert gcc_version == 13
    #     return True
    return False


def _is_main_gcc(os_version: OsVersion, gcc_version: _GCC_VERSIONS) -> bool:
    if os_version == OsVersion.TUMBLEWEED and gcc_version == 13:
        return True
    # FIXME: os_version.is_sles
    if os_version in (OsVersion.SP5, OsVersion.SP6) and gcc_version == 7:
        return True
    # if os_version in (OsVersion.SLCC_DEVELOPMENT, OsVersion.SLCC_PRODUCTION):
    #     assert gcc_version == 13
    #     return True
    return False


GCC_CONTAINERS = [
    DevelopmentContainer(
        name="gcc",
        package_name=f"gcc-{gcc_version}-image",
        os_version=os_version,
        version=gcc_version,
        package_list=(
            [
                (gcc_pkg := f"gcc{gcc_version}"),
                (gpp := f"{gcc_pkg}-c++"),
                "make",
            ]
            + (["gcc", "gcc-c++"] if _is_main_gcc(os_version, gcc_version) else [])
        ),
        pretty_name="GNU Compiler Collection",
        is_latest=(
            (os_version in CAN_BE_LATEST_OS_VERSION)
            and _is_latest_gcc(os_version, gcc_version)
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%gcc_version%%",
                package_name=gcc_pkg,
                parse_version="minor",
            )
        ],
        env={"GCC_VERSION": "%%gcc_version%%"},
        additional_versions=["%%gcc_version%%"],
        custom_end=(
            rf"""# symlink all versioned gcc & g++ binaries to unversioned
# ones in /usr/local/bin so that plain gcc works
{DOCKERFILE_RUN} for gcc_bin in $(rpm -ql {gcc_pkg} {gpp} |grep ^/usr/bin/ ); do \
        ln -f $gcc_bin $(echo "$gcc_bin" | sed -e 's|/usr/bin/|/usr/local/bin/|' -e 's|-{gcc_version}$||'); \
    done
"""
            if not _is_main_gcc(os_version, gcc_version)
            else ""
        ),
    )
    for (gcc_version, os_version) in (
        (7, OsVersion.SP5),
        (13, OsVersion.SP5),
        (7, OsVersion.SP6),
        (13, OsVersion.SP6),
        # (13, OsVersion.SLCC_DEVELOPMENT),
        # (13, OsVersion.SLCC_PRODUCTION),
        (12, OsVersion.TUMBLEWEED),
        (13, OsVersion.TUMBLEWEED),
        (14, OsVersion.TUMBLEWEED),
    )
]
