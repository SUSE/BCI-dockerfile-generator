"""This module contains constant settings and enums used in the BCI Dockerfile generator."""
from __future__ import annotations

import datetime
import enum
from typing import List


BASH_SET = "set -euo pipefail"

#: a ``RUN`` command with a common set of bash flags applied to prevent errors
#: from not being noticed
DOCKERFILE_RUN = f"RUN {BASH_SET};"


@enum.unique
class Arch(enum.Enum):
    """Architectures of packages on OBS"""

    X86_64 = "x86_64"
    AARCH64 = "aarch64"
    PPC64LE = "ppc64le"
    S390X = "s390x"
    LOCAL = "local"

    def __str__(self) -> str:
        return self.value


@enum.unique
class ReleaseStage(enum.Enum):
    """Values for the ``release-stage`` label of a BCI"""

    BETA = "beta"
    RELEASED = "released"

    def __str__(self) -> str:
        return self.value


@enum.unique
class ImageType(enum.Enum):
    """Values of the ``image-type`` label of a BCI"""

    SLE_BCI = "sle-bci"
    APPLICATION = "application"

    def __str__(self) -> str:
        return self.value


@enum.unique
class BuildType(enum.Enum):
    """Build Type.

    Options for how the image is build, either as a kiwi build or from a
    :file:`Dockerfile`."""

    DOCKER = "docker"
    KIWI = "kiwi"

    def __str__(self) -> str:
        return self.value


@enum.unique
class SupportLevel(enum.Enum):
    """Potential values of the ``com.suse.supportlevel`` label."""

    L2 = "l2"
    L3 = "l3"
    #: Additional Customer Contract
    ACC = "acc"
    UNSUPPORTED = "unsupported"
    TECHPREVIEW = "techpreview"

    def __str__(self) -> str:
        return self.value


@enum.unique
class PackageType(enum.Enum):
    """Package types supported by kiwi.

    See `<https://osinside.github.io/kiwi/concept_and_workflow/packages.html>`_ for
    further details. Note that these are only supported for kiwi builds.
    """

    DELETE = "delete"
    UNINSTALL = "uninstall"
    BOOTSTRAP = "bootstrap"
    IMAGE = "image"

    def __str__(self) -> str:
        return self.value


@enum.unique
class OsVersion(enum.Enum):
    """Enumeration of the base operating system versions for BCI."""

    #: SLE 15 Service Pack 6
    SP6 = 6
    #: SLE 15 Service Pack 5
    SP5 = 5
    #: SLE 15 Service Pack 4
    SP4 = 4
    #: SLE 15 Service Pack 3
    SP3 = 3
    #: openSUSE Tumbleweed
    TUMBLEWEED = "Tumbleweed"
    #: Adaptable Linux Platform, Basalt project
    BASALT = "Basalt"

    @staticmethod
    def parse(val: str) -> OsVersion:
        try:
            return OsVersion(int(val))
        except ValueError:
            return OsVersion(val)

    def __str__(self) -> str:
        return str(self.value)

    @property
    def pretty_print(self) -> str:
        """Pretty print the OS version."""
        if self.value in (OsVersion.TUMBLEWEED.value, OsVersion.BASALT.value):
            return self.value
        return f"SP{self.value}"

    @property
    def pretty_os_version_no_dash(self) -> str:
        """Pretty print the OS version without a dash."""
        if self.value == OsVersion.TUMBLEWEED.value:
            return f"openSUSE {self.value}"
        if self.value == OsVersion.BASALT.value:
            return "Adaptable Linux Platform"

        return f"15 SP{self.value}"

    @property
    def lifecycle_data_pkg(self) -> List[str]:
        """Return the lifecycle data package list for the given OS version."""
        if self.value not in (OsVersion.BASALT.value, OsVersion.TUMBLEWEED.value):
            return ["lifecycle-data-sle-module-development-tools"]
        return []


#: Operating system versions that have the label ``com.suse.release-stage`` set
#: to ``released``.
RELEASED_OS_VERSIONS = [OsVersion.SP3] + [
    OsVersion.SP4,
    OsVersion.SP5,
    OsVersion.TUMBLEWEED,
]

# For which versions to create Application and Language Containers?
ALL_NONBASE_OS_VERSIONS = [OsVersion.SP5, OsVersion.SP6, OsVersion.TUMBLEWEED]

# For which versions to create Base Container Images?
ALL_BASE_OS_VERSIONS = [
    OsVersion.SP4,
    OsVersion.SP5,
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
    OsVersion.BASALT,
]

# joint set of BASE and NON_BASE versions
ALL_OS_VERSIONS = set(ALL_BASE_OS_VERSIONS + ALL_NONBASE_OS_VERSIONS)

CAN_BE_LATEST_OS_VERSION = [OsVersion.SP5, OsVersion.TUMBLEWEED, OsVersion.BASALT]


# End of General Support Dates
SUPPORTED_UNTIL_SLE = {
    OsVersion.SP4: datetime.date(2023, 12, 31),
    OsVersion.SP5: None,  # datetime.date(2024, 12, 31),
    OsVersion.SP6: None,
}
