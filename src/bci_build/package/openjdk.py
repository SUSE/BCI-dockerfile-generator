"""OpenJDK (Java) related BCI containers"""
import os
from itertools import product
from typing import Literal

from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import Arch
from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.package import SupportLevel
from bci_build.package import _build_tag_prefix
from bci_build.package import generate_disk_size_constraints


def _get_openjdk_kwargs(
    os_version: OsVersion, devel: bool, java_version: Literal[11, 13, 15, 17, 20, 21]
):
    JAVA_HOME = f"/usr/lib64/jvm/java-{java_version}-openjdk-{java_version}"
    JAVA_ENV = {
        "JAVA_BINDIR": os.path.join(JAVA_HOME, "bin"),
        "JAVA_HOME": JAVA_HOME,
        "JAVA_ROOT": JAVA_HOME,
        "JAVA_VERSION": f"{java_version}",
    }

    is_latest = java_version == 17 and os_version in CAN_BE_LATEST_OS_VERSION

    common = {
        # Hardcoding /usr/lib64 in JAVA_HOME atm
        "exclusive_arch": [Arch.AARCH64, Arch.X86_64, Arch.PPC64LE, Arch.S390X],
        "env": JAVA_ENV,
        "version": java_version,
        "os_version": os_version,
        "is_latest": is_latest,
        "package_name": f"openjdk-{java_version}"
        + ("-devel" if devel else "")
        + "-image",
        "extra_files": {
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6)
        },
        # smoke test for container environment variables
        "custom_end": f"""{DOCKERFILE_RUN} [ -d $JAVA_HOME ]; [ -d $JAVA_BINDIR ]; [ -f "$JAVA_BINDIR/java" ] && [ -x "$JAVA_BINDIR/java" ]""",
    }

    if devel:
        return common | {
            "name": "openjdk-devel",
            "custom_labelprefix_end": "openjdk.devel",
            "pretty_name": f"OpenJDK {java_version} development",
            "package_list": [f"java-{java_version}-openjdk-devel", "git-core", "maven"],
            "cmd": ["/usr/bin/jshell"],
            "from_image": f"{_build_tag_prefix(os_version)}/openjdk:{java_version}",
        }
    return common | {
        "name": "openjdk",
        "pretty_name": f"OpenJDK {java_version} runtime",
        "package_list": [f"java-{java_version}-openjdk"],
    }


OPENJDK_CONTAINERS = (
    [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version, devel, java_version=11),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.SP5, OsVersion.TUMBLEWEED),
            (True, False),
        )
    ]
    + [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=17),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.SP5, OsVersion.TUMBLEWEED), (True, False)
        )
    ]
    + [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=21),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.SP6, OsVersion.TUMBLEWEED), (True, False)
        )
    ]
)
