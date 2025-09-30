"""This package contains enumerations with constants like architectures or build
types.

"""

import enum
from dataclasses import dataclass


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

    LTSS = "ltss"
    SLE_BCI = "sle-bci"
    APPLICATION = "application"

    def __str__(self) -> str:
        return self.value


@enum.unique
class BuildType(enum.Enum):
    """Options for how the image is build, either as a kiwi build or from a
    :file:`Dockerfile`.

    """

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
    CUSTOM_BUILD_ARG = "build_arg"

    def __str__(self) -> str:
        return self.value


@enum.unique
class PackageType(enum.Enum):
    """Package types that are supported by kiwi, see
    `<https://osinside.github.io/kiwi/concept_and_workflow/packages.html>`_ for
    further details.

    Note that these are only supported for kiwi builds.

    """

    DELETE = "delete"
    UNINSTALL = "uninstall"
    BOOTSTRAP = "bootstrap"
    IMAGE = "image"

    def __str__(self) -> str:
        return self.value


@enum.unique
class NetworkProtocol(enum.Enum):
    TCP = "tcp"
    UDP = "udp"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class NetworkPort:
    """Representation of a port to expose from a container."""

    #: the port number
    number: int

    #: the network protocol
    protocol: NetworkProtocol = NetworkProtocol.TCP

    def __post_init__(self) -> None:
        if self.number < 1 or self.number > 65535:
            raise ValueError(f"Invalid port number: {self.number}")

    def __str__(self) -> str:
        return f"{self.number}/{self.protocol}"


def TCP(port_number: int) -> NetworkPort:
    return NetworkPort(port_number, protocol=NetworkProtocol.TCP)


def UDP(port_number: int) -> NetworkPort:
    return NetworkPort(port_number, protocol=NetworkProtocol.UDP)
