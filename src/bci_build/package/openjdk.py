"""OpenJDK (Java) related BCI containers"""

import datetime
import os
from itertools import product
from typing import Literal

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import _SUPPORTED_UNTIL_SLE
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import DevelopmentContainer
from bci_build.package import _build_tag_prefix
from bci_build.package import generate_disk_size_constraints
from bci_build.replacement import Replacement


def supported_until(os_version: OsVersion, jre_major: int) -> datetime.date | None:
    """Return the predicted end of support date for this os/jre combination. Unlike
    the SAC containers, we bound them to the SP lifecycle
    """
    if not os_version.is_sle15:
        return None

    # Taken from https://www.suse.com/releasenotes/x86_64/SUSE-SLES/15-SP7/index.html#java-version
    jre_end_support_dates: dict[int, datetime.date] = {
        21: datetime.date(2031, 6, 30),
        17: datetime.date(2027, 12, 31),
        11: datetime.date(2026, 12, 31),
        8: datetime.date(2026, 12, 31),
    }

    jre_sp_mapping: dict[int, datetime.date | None] = {
        11: _SUPPORTED_UNTIL_SLE[OsVersion.SP5],
        17: _SUPPORTED_UNTIL_SLE[OsVersion.SP7],
        21: _SUPPORTED_UNTIL_SLE[OsVersion.SP7],
    }

    if (
        jre_end_support_dates.get(jre_major) is None
        or jre_sp_mapping.get(jre_major) is None
    ):
        return None

    return min(
        jre_end_support_dates.get(jre_major, None), jre_sp_mapping.get(jre_major, None)
    )


def _get_openjdk_kwargs(
    os_version: Literal[
        OsVersion.TUMBLEWEED, OsVersion.SP7, OsVersion.SP6, OsVersion.SP5
    ],
    devel: bool,
    java_version: Literal[11, 17, 21, 25],
):
    JAVA_HOME = f"/usr/lib64/jvm/java-{java_version}-openjdk-{java_version}"
    JAVA_ENV = {
        "JAVA_BINDIR": os.path.join(JAVA_HOME, "bin"),
        "JAVA_HOME": JAVA_HOME,
        "JAVA_ROOT": JAVA_HOME,
        "JAVA_VERSION": f"{java_version}",
    }

    is_latest = (java_version == 21 and os_version.is_sle15) or (
        java_version == 25 and os_version.is_tumbleweed
    )

    common = {
        # Hardcoding /usr/lib64 in JAVA_HOME atm
        "exclusive_arch": [Arch.AARCH64, Arch.X86_64, Arch.PPC64LE, Arch.S390X],
        "env": JAVA_ENV,
        "tag_version": java_version,
        "version": "%%java_version%%",
        "os_version": os_version,
        "is_latest": is_latest,
        "supported_until": supported_until(os_version, java_version),
        "package_name": (
            f"openjdk-{java_version}" + ("-devel" if devel else "") + "-image"
        ),
        "extra_files": {
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6)
        },
        "replacements_via_service": [
            Replacement(
                regex_in_build_description="%%java_version%%",
                package_name=(
                    f"java-{java_version}-openjdk-devel"
                    if devel
                    else f"java-{java_version}-openjdk"
                ),
            ),
        ],
        # smoke test for container environment variables
        "custom_end": f"""{DOCKERFILE_RUN} [ -d $JAVA_HOME ]; [ -d $JAVA_BINDIR ]; [ -f "$JAVA_BINDIR/java" ] && [ -x "$JAVA_BINDIR/java" ]""",
    }

    if devel:
        # don't set CMD in SP7 onward as jshell is broken and the CMD is
        # arguably not too useful anyway
        if os_version in (OsVersion.SP5, OsVersion.SP6):
            common |= {"cmd": ["/usr/bin/jshell"]}

        return common | {
            "name": "openjdk-devel",
            "custom_labelprefix_end": "openjdk.devel",
            "pretty_name": f"OpenJDK {java_version} development",
            "package_list": [f"java-{java_version}-openjdk-devel", "maven"],
            "from_image": f"{_build_tag_prefix(os_version)}/openjdk:{java_version}",
        }
    return common | {
        "name": "openjdk",
        "pretty_name": f"OpenJDK {java_version} runtime",
        # adding nss-sysinit for /etc/pki/nssdb which is needed for NSS
        "package_list": [f"java-{java_version}-openjdk", "mozilla-nss-sysinit"]
        + os_version.common_devel_packages,
    }


OPENJDK_CONTAINERS = (
    [
        DevelopmentContainer(
            **_get_openjdk_kwargs(os_version, devel, java_version=11),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.TUMBLEWEED,),
            (True, False),
        )
    ]
    + [
        DevelopmentContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=17),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.SP7, OsVersion.SL16_0, OsVersion.TUMBLEWEED), (True, False)
        )
    ]
    + [
        DevelopmentContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=21),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.SP7, OsVersion.SL16_0, OsVersion.TUMBLEWEED), (True, False)
        )
    ]
    + [
        DevelopmentContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=25),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product((OsVersion.TUMBLEWEED,), (True, False))
    ]
)
