"""Build description for the GCC Container Images"""

import datetime
from typing import Literal

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import DevelopmentContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints

_GCC_VERSIONS = Literal[7, 12, 13, 14, 15]

# The lifecycle is two years after the XX.2 release
# according to upstream release date at
# https://gcc.gnu.org/releases.html
_GCC_SL16_SUPPORTED_UNTIL: dict[_GCC_VERSIONS, datetime.date | None] = {
    13: datetime.date(2025, 7, 31),
    14: datetime.date(2026, 7, 31),
}


def _is_latest_gcc(os_version: OsVersion, gcc_version: _GCC_VERSIONS) -> bool:
    if os_version == OsVersion.TUMBLEWEED:
        return gcc_version == 15
    if os_version.is_sle15:
        return gcc_version == 14
    if os_version.is_sl16:
        return gcc_version == 15
    return False


def _is_main_gcc(os_version: OsVersion, gcc_version: _GCC_VERSIONS) -> bool:
    if os_version == OsVersion.TUMBLEWEED and gcc_version == 14:
        return True
    if os_version.is_sle15 and gcc_version == 7:
        return True
    if os_version.is_sl16 and gcc_version == 15:
        return True
    return False


GCC_CONTAINERS = [
    DevelopmentContainer(
        name="gcc",
        package_name=f"gcc-{gcc_version}-image",
        license="GPL-3.0-or-later",
        os_version=os_version,
        version="%%gcc_minor_version%%",
        tag_version=str(gcc_version),
        support_level=SupportLevel.L3,
        supported_until=_GCC_SL16_SUPPORTED_UNTIL.get(gcc_version),
        package_list=(
            [
                (gcc_pkg := f"gcc{gcc_version}"),
                (gpp := f"{gcc_pkg}-c++"),
                (gfortran := f"{gcc_pkg}-fortran"),
                "make",
            ]
            + (
                ["gcc", "gcc-c++", "gcc-fortran"]
                if _is_main_gcc(os_version, gcc_version)
                else []
            )
            + os_version.common_devel_packages
            + os_version.lifecycle_data_pkg
        ),
        pretty_name="GNU Compiler Collection",
        logo_url="https://gcc.gnu.org/img/gccegg-65.png",
        is_latest=(
            (os_version in CAN_BE_LATEST_OS_VERSION)
            and _is_latest_gcc(os_version, gcc_version)
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%gcc_minor_version%%",
                package_name=gcc_pkg,
                parse_version=ParseVersion.MINOR,
            ),
        ],
        env={"GCC_VERSION": "%%gcc_minor_version%%"},
        extra_files={"_constraints": generate_disk_size_constraints(6)},
        custom_end=(
            rf"""# symlink all versioned gcc & g++ binaries to unversioned
# ones in /usr/local/bin so that plain gcc works
{DOCKERFILE_RUN} for gcc_bin in $(rpm -ql {gcc_pkg} {gpp} {gfortran} |grep ^/usr/bin/ ); do \
        ln -sf $gcc_bin $(echo "$gcc_bin" | sed -e 's|/usr/bin/|/usr/local/bin/|' -e 's|-{gcc_version}$||'); \
    done
"""
            if not _is_main_gcc(os_version, gcc_version)
            else ""
        ),
    )
    for (gcc_version, os_version) in (
        (14, OsVersion.SP7),
        (15, OsVersion.SL16_0),
        (13, OsVersion.TUMBLEWEED),
        (14, OsVersion.TUMBLEWEED),
        (15, OsVersion.TUMBLEWEED),
    )
]
