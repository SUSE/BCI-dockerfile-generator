from __future__ import annotations

import abc
import asyncio
import datetime
import enum
import os
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Literal
from typing import overload

import jinja2
from packaging import version

from bci_build.templates import DOCKERFILE_TEMPLATE
from bci_build.templates import INFOHEADER_TEMPLATE
from bci_build.templates import KIWI_TEMPLATE
from bci_build.templates import SERVICE_TEMPLATE
from bci_build.util import write_to_file

_BASH_SET: str = "set -euo pipefail"

#: a ``RUN`` command with a common set of bash flags applied to prevent errors
#: from not being noticed
DOCKERFILE_RUN: str = f"RUN {_BASH_SET};"

#: Remove various log files. While it is possible to just ``rm -rf /var/log/*``,
#: that would also remove some package owned directories (not %ghost)
LOG_CLEAN: str = "rm -rf /var/log/{lastlog,tallylog,zypper.log,zypp/history,YaST2}"


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
class OsVersion(enum.Enum):
    """Enumeration of the base operating system versions for BCI."""

    #: SLE 15 Service Pack 7
    SP7 = 7
    #: SLE 15 Service Pack 6
    SP6 = 6
    #: SLE 15 Service Pack 5
    SP5 = 5
    #: SLE 15 Service Pack 4
    SP4 = 4
    #: SLE 15 Service Pack 3
    SP3 = 3
    #: SUSE Linux Framework One
    SLE16_0 = "16.0"
    #: openSUSE Tumbleweed
    TUMBLEWEED = "Tumbleweed"

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
        if self.value in (OsVersion.TUMBLEWEED.value, OsVersion.SLE16_0.value):
            return self.value
        return f"SP{self.value}"

    @property
    def pretty_os_version_no_dash(self) -> str:
        if self.value == OsVersion.TUMBLEWEED.value:
            # TW has no version by itself and the "openSUSE Tumbleweed" is
            # already part of the base identifier
            return ""
        if self.is_slfo:
            return "Framework One"

        return f"15 SP{self.value}"

    @property
    def deployment_branch_name(self) -> str:
        if self.is_tumbleweed or self.is_slfo:
            return str(self.value)
        if self.is_sle15:
            return f"sle15-sp{self.value}"
        raise NotImplementedError("unhandled version {self.value}")

    @property
    def lifecycle_data_pkg(self) -> list[str]:
        if self.value not in (OsVersion.SLE16_0.value, OsVersion.TUMBLEWEED.value):
            return ["lifecycle-data-sle-module-development-tools"]
        return []

    @property
    def common_devel_packages(self) -> list[str]:
        """Returns a list of common development packages that are needed for
        all development containers"""
        r = set(("findutils", "gawk", "git-core", "curl", "procps"))
        if self.is_tumbleweed or self.is_slfo:
            r.add("util-linux")

        return sorted(list(r))

    @property
    def is_sle15(self) -> bool:
        return self.value in (
            OsVersion.SP3.value,
            OsVersion.SP4.value,
            OsVersion.SP5.value,
            OsVersion.SP6.value,
            OsVersion.SP7.value,
        )

    @property
    def is_slfo(self) -> bool:
        return self.value in (OsVersion.SLE16_0.value,)

    @property
    def is_tumbleweed(self) -> bool:
        return self.value == OsVersion.TUMBLEWEED.value

    @property
    def is_ltss(self) -> bool:
        return self in ALL_OS_LTSS_VERSIONS

    @property
    def os_version(self) -> str:
        """Returns the numeric version of :py:class:`OsContainer` (or
        ``latest``).

        """
        if self.is_sle15:
            return f"15.{str(self.value)}"
        if self.value == OsVersion.SLE16_0.value:
            return "16.0"
        # Tumbleweed rolls too fast, just use latest
        return "latest"

    @property
    def has_container_suseconnect(self) -> bool:
        return self.is_sle15 or self.is_slfo

    @property
    def eula_package_names(self) -> tuple[str, ...]:
        if self.is_sle15:
            return ("skelcd-EULA-bci",)
        # if self.is_slcc:
        #     return (f"skelcd-EULA-{str(self.value).lower()}",)
        return ()

    @property
    def release_package_names(self) -> tuple[str, ...]:
        if self.value == OsVersion.TUMBLEWEED.value:
            return ("openSUSE-release", "openSUSE-release-appliance-docker")
        if self.value == OsVersion.SLE16_0.value:
            return ("SLES-release",)
        if self.is_ltss:
            return ("sles-ltss-release",)
        # if self.is_slcc:
        #     return (f"{str(self.value).lower()}-release",)

        assert self.is_sle15
        return ("sles-release",)


#: Operating system versions that have the label ``com.suse.release-stage`` set
#: to ``released``.
RELEASED_OS_VERSIONS: list[OsVersion] = [
    OsVersion.SP3,
    OsVersion.SP4,
    OsVersion.SP5,
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
]

# For which versions to create Application and Language Containers?
ALL_NONBASE_OS_VERSIONS: list[OsVersion] = [
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
]

# For which versions to create Base Container Images?
ALL_BASE_OS_VERSIONS: list[OsVersion] = [
    OsVersion.SP5,
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
    OsVersion.SLE16_0,
]

# List of SPs that are already under LTSS
ALL_OS_LTSS_VERSIONS: list[OsVersion] = [OsVersion.SP3, OsVersion.SP4]

# joint set of BASE and NON_BASE versions
ALL_OS_VERSIONS: set[OsVersion] = {
    v for v in (*ALL_BASE_OS_VERSIONS, *ALL_NONBASE_OS_VERSIONS)
}

CAN_BE_LATEST_OS_VERSION: list[OsVersion] = [
    OsVersion.SP6,
    OsVersion.TUMBLEWEED,
    OsVersion.SLE16_0,
]


# End of General Support Dates
_SUPPORTED_UNTIL_SLE: dict[OsVersion, datetime.date | None] = {
    OsVersion.SP4: datetime.date(2023, 12, 31),
    OsVersion.SP5: datetime.date(2024, 12, 31),
    OsVersion.SP6: None,
    OsVersion.SP7: datetime.date(2031, 7, 31),
}


@dataclass
class Package:
    """Representation of a package in a kiwi build, for Dockerfile based builds the
    :py:attr:`~Package.pkg_type`.

    """

    #: The name of the package
    name: str

    #: The package type. This parameter is only applicable for kiwi builds and
    #: defines into which ``<packages>`` element this package is inserted.
    pkg_type: PackageType = PackageType.IMAGE

    def __str__(self) -> str:
        return self.name


@enum.unique
class ParseVersion(enum.StrEnum):
    MAJOR = enum.auto()
    MINOR = enum.auto()
    PATCH = enum.auto()
    PATCH_UPDATE = enum.auto()
    OFFSET = enum.auto()


@dataclass
class Replacement:
    """Represents a replacement via the `obs-service-replace_using_package_version
    <https://github.com/openSUSE/obs-service-replace_using_package_version>`_.

    """

    #: regex to be replaced in :py:attr:`~bci_build.package.Replacement.file_name`, :file:`Dockerfile` or :file:`$pkg_name.kiwi`
    regex_in_build_description: str

    #: package name to be queried for the version
    package_name: str

    #: override file name, if unset use :file:`Dockerfile` or :file:`$pkg_name.kiwi`
    file_name: str | None = None

    #: specify how the version should be formated, see
    #: `<https://github.com/openSUSE/obs-service-replace_using_package_version#usage>`_
    #: for further details
    parse_version: None | ParseVersion = None

    def __post_init__(self) -> None:
        """Barf if someone tries to replace variables in README, as those
        changes will be only performed in the buildroot, but not in the actual
        source package.

        """

        if self.file_name and "readme" in self.file_name.lower():
            raise ValueError(f"Cannot replace variables in {self.file_name}!")


def _build_tag_prefix(os_version: OsVersion) -> str:
    if os_version == OsVersion.TUMBLEWEED:
        return "opensuse/bci"
    if os_version == OsVersion.SP3:
        return "suse/ltss/sle15.3"
    if os_version == OsVersion.SP4:
        return "suse/ltss/sle15.4"

    return "bci"


@dataclass
class BaseContainerImage(abc.ABC):
    """Base class for all Base Containers."""

    #: Name of this image. It is used to generate the build tags, i.e. it
    #: defines under which name this image is published.
    name: str

    #: The SLE service pack to which this package belongs
    os_version: OsVersion

    #: Human readable name that will be inserted into the image title and description
    pretty_name: str

    #: Optional a package_name, used for creating the package name on OBS or IBS in
    # ``devel:BCI:SLE-15-SP$ver`` (on  OBS) or ``SUSE:SLE-15-SP$ver:Update:BCI`` (on IBS)
    package_name: str | None = None

    #: Epoch to use for handling os_version downgrades
    os_epoch: int | None = None

    #: The container from which the build stage is running. On SLE15, this defaults to
    #: ``suse/sle15:15.$SP`` for Application Containers and ``bci/bci-base:15.$SP``
    #: for all other images. On openSUSE, ``opensuse/tumbleweed:latest`` is used
    #: when an empty string is used.
    #:
    #: When from image is ``None``, then this image will not be based on
    #: **anything**, i.e. the ``FROM`` line is missing in the ``Dockerfile``.
    from_image: str | None = ""

    #: The container that is used to install this image into. If this is not set, then
    #: only a single stage build is produced, otherwise a multistage build
    from_target_image: str | None = None

    #: Architectures of this image.
    #:
    #: If supplied, then this image will be restricted to only build on the
    #: supplied architectures. By default, there is no restriction
    exclusive_arch: list[Arch] | None = None

    #: Determines whether this image will have the ``latest`` tag.
    is_latest: bool = False

    #: Determines whether only one version of this image will be published
    #: under the same registry path.
    is_singleton_image: bool = False

    #: An optional entrypoint for the image, it is omitted if empty or ``None``
    #: If you provide a string, then it will be included in the container build
    #: recipe as is, i.e. it will be called via a shell as
    #: :command:`sh -c "MY_CMD"`.
    #: If your entrypoint must not be called through a shell, then pass the
    #: binary and its parameters as a list
    entrypoint: list[str] | None = None

    # The user to use for entrypoint service
    entrypoint_user: str | None = ""

    #: An optional CMD for the image, it is omitted if empty or ``None``
    cmd: list[str] | None = None

    #: An optional list of volumes, it is omitted if empty or ``None``
    volumes: list[str] | None = None

    #: An optional list of tcp port exposes, it is omitted if empty or ``None``
    exposes_tcp: list[int] | None = None

    #: Extra environment variables to be set in the container
    env: dict[str, str | int] | dict[str, str] | dict[str, int] = field(
        default_factory=dict
    )

    #: Add any replacements via `obs-service-replace_using_package_version
    #: <https://github.com/openSUSE/obs-service-replace_using_package_version>`_
    #: that are used in this image into this list.
    #: See also :py:class:`~Replacement`
    replacements_via_service: list[Replacement] = field(default_factory=list)

    #: Additional labels that should be added to the image. These are added as labels
    #  within the "labelprefix" section.
    extra_labels: dict[str, str] = field(default_factory=dict)

    #: Packages to be installed inside the container image
    package_list: list[str] | list[Package] = field(default_factory=list)

    #: This string is appended to the automatically generated dockerfile and can
    #: contain arbitrary instructions valid for a :file:`Dockerfile`.
    #:
    #: .. note::
    #:   Setting both this property and :py:attr:`~BaseContainerImage.config_sh_script`
    #:   is not possible and will result in an error.
    custom_end: str = ""

    #: A script that is put into :file:`config.sh` if a kiwi image is
    #: created. If a :file:`Dockerfile` based build is used then this script is
    #: prependend with a :py:const:`~bci_build.package.DOCKERFILE_RUN` and added
    #: at the end of the ``Dockerfile``. It must thus fit on a single line if
    #: you want to be able to build from a kiwi and :file:`Dockerfile` at the
    #: same time!
    config_sh_script: str = ""

    #: The interpreter of the :file:`config.sh` script that is executed by kiwi
    #: during the image build.
    #: It defaults to :file:`/bin/bash` and has no effect for :file:`Dockerfile`
    #: based builds.
    #: *Warning:* Using a different interpreter than :file:`/bin/bash` could
    #: lead to unpredictable results as kiwi's internal functions are written
    #: for bash and not for a different shell.
    config_sh_interpreter: str = "/bin/bash"

    #: The oci image author annoation for this image, defaults to SUSE/openSUSE
    maintainer: str | None = None

    #: Additional files that belong into this container-package.
    #: The key is the filename, the values are the file contents.
    extra_files: dict[str, str | bytes] | dict[str, bytes] | dict[str, str] = field(
        default_factory=dict
    )

    #: Additional names under which this image should be published alongside
    #: :py:attr:`~BaseContainerImage.name`.
    #: These names are only inserted into the
    #: :py:attr:`~BaseContainerImage.build_tags`
    additional_names: list[str] = field(default_factory=list)

    #: By default the containers get the labelprefix
    #: ``{label_prefix}.bci.{self.name}``. If this value is not an empty string,
    #: then it is used instead of the name after ``com.suse.bci.``.
    custom_labelprefix_end: str = ""

    #: Provide a custom description instead of the automatically generated one
    custom_description: str = ""

    #: Define whether this container image is built using docker or kiwi.
    #: If not set, then the build type will default to docker from SP4 onwards.
    build_recipe_type: BuildType | None = None

    #: Define packages that should be ignored by kiwi in the creation of the
    #: final container image even if dependencies would otherwise pull them in.
    kiwi_ignore_packages: list[str] | None = None

    #: A license string to be placed in a comment at the top of the Dockerfile
    #: or kiwi build description file.
    license: str = "MIT"

    #: The support level for this image, defaults to :py:attr:`SupportLevel.TECHPREVIEW`
    support_level: SupportLevel = SupportLevel.TECHPREVIEW

    #: The support level end date
    supported_until: datetime.date | None = None

    #: flag whether to not install recommended packages in the call to
    #: :command:`zypper` in :file:`Dockerfile`
    no_recommends: bool = True

    #: URL to the logo of this container image.
    #: This value is added to the ``io.artifacthub.package.logo-url`` label if
    #: present
    logo_url: str = ""

    #: Optional build_release setting that will be inserted as the
    #: ``#!BuildRelease`` magic comment for the build service to ensure that
    #: the release suffix of a container tag is sequentially increasing (for
    #: webui sorting)
    _min_release_counter: int | None = None

    def __post_init__(self) -> None:
        self.pretty_name = self.pretty_name.strip()

        if not self.package_name:
            self.package_name = f"{self.name}-image"
        if not self.package_list:
            raise ValueError(f"No packages were added to {self.pretty_name}.")
        if self.exclusive_arch and Arch.LOCAL in self.exclusive_arch:
            raise ValueError(f"{Arch.LOCAL} must not appear in {self.exclusive_arch=}")
        if self.config_sh_script and self.custom_end:
            raise ValueError(
                "Cannot specify both a custom_end and a config.sh script! Use just config_sh_script."
            )

        if self.build_recipe_type is None:
            self.build_recipe_type = (
                BuildType.KIWI if self.os_version == OsVersion.SP3 else BuildType.DOCKER
            )

        if not self.maintainer:
            self.maintainer = (
                "openSUSE (https://www.opensuse.org/)"
                if self.os_version.is_tumbleweed
                else "SUSE LLC (https://www.suse.com/)"
            )

        # limit to tech preview for beta releases
        if (
            self.release_stage == ReleaseStage.BETA
            and self.support_level == SupportLevel.L3
        ):
            self.support_level = SupportLevel.TECHPREVIEW

    @property
    @abc.abstractmethod
    def uid(self) -> str:
        """unique identifier of this image, either its name or ``$name-$tag_version``."""
        pass

    @property
    @abc.abstractmethod
    def oci_version(self) -> str:
        """The "main" version label of this image.

        It is added as the ``org.opencontainers.image.version`` label to the
        container image.
        """
        pass

    @property
    def build_name(self) -> str | None:
        if self.build_tags:
            build_name: str = self.build_tags[0]
            if self.is_singleton_image:
                build_name = build_name.partition(":")[0]
            return build_name.replace("/", ":").replace(":", "-")

        return None

    @property
    def build_version(self) -> str | None:
        if self.os_version not in (OsVersion.TUMBLEWEED, OsVersion.SLE16_0):
            epoch = ""
            if self.os_epoch:
                epoch = f"{self.os_epoch}."
            return f"15.{epoch}{int(self.os_version.value)}"
        return None

    @property
    def build_release(self) -> str | None:
        if self.os_version not in (OsVersion.SP6,):
            return None

        return (
            str(self._min_release_counter)
            if self._min_release_counter is not None
            else None
        )

    @property
    def distribution_base_name(self) -> str:
        if self.os_version.is_tumbleweed:
            return "openSUSE Tumbleweed"
        elif self.os_version.is_ltss:
            return "SLE LTSS"
        elif self.os_version.is_sle15 or self.os_version.is_slfo:
            return "SLE"

        raise NotImplementedError(f"Unknown os_version: {self.os_version}")

    @property
    def eula(self) -> str:
        """EULA covering this image. can be ``sle-eula`` or ``sle-bci``."""
        if self.os_version.is_ltss:
            return "sle-eula"
        return "sle-bci"

    @property
    def lifecycle_url(self) -> str:
        if self.os_version.is_tumbleweed:
            return "https://en.opensuse.org/Lifetime#openSUSE_BCI"
        if self.os_version.is_sle15:
            return "https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
        return "https://www.suse.com/lifecycle"

    @property
    def release_stage(self) -> ReleaseStage:
        """This container images' release stage.

        It is :py:attr:`~ReleaseStage.RELEASED` if the container images'
        operating system version is in the list
        :py:const:`~bci_build.package.RELEASED_OS_VERSIONS`. Otherwise it
        is :py:attr:`~ReleaseStage.BETA`.

        """
        if self.os_version in RELEASED_OS_VERSIONS:
            return ReleaseStage.RELEASED

        return ReleaseStage.BETA

    @property
    def url(self) -> str:
        """The default url that is put into the
        ``org.opencontainers.image.url`` label

        """
        if self.os_version.is_tumbleweed:
            return "https://www.opensuse.org"
        if self.os_version.is_ltss:
            return "https://www.suse.com/products/long-term-service-pack-support/"

        return "https://www.suse.com/products/base-container-images/"

    @property
    def vendor(self) -> str:
        """The vendor that is put into the ``org.opencontainers.image.vendor``
        label

        """
        if self.os_version.is_tumbleweed:
            return "openSUSE Project"
        return "SUSE LLC"

    @property
    def registry(self) -> str:
        """The registry where the image is available on."""
        if self.os_version.is_tumbleweed:
            return "registry.opensuse.org"
        return "registry.suse.com"

    @property
    def dockerfile_custom_end(self) -> str:
        """This part is appended at the end of the :file:`Dockerfile`. It is either
        generated from :py:attr:`BaseContainerImage.custom_end` or by prepending
        ``RUN`` in front of :py:attr:`BaseContainerImage.config_sh_script`. The
        later implies that the script in that variable fits on a single line or
        newlines are escaped, e.g. via `ansi escapes
        <https://stackoverflow.com/a/33439625>`_.

        """
        if self.custom_end:
            return self.custom_end
        if self.config_sh_script:
            return f"{DOCKERFILE_RUN} {self.config_sh_script}"
        return ""

    @property
    def _registry_prefix(self) -> str:
        return _build_tag_prefix(self.os_version)

    @staticmethod
    def _cmd_entrypoint_docker(
        prefix: Literal["CMD", "ENTRYPOINT"], value: list[str] | None
    ) -> str | None:
        if not value:
            return None
        if isinstance(value, list):
            return "\n" + prefix + " " + str(value).replace("'", '"')
        assert False, f"Unexpected type for {prefix}: {type(value)}"

    @property
    def entrypoint_docker(self) -> str | None:
        """The entrypoint line in a :file:`Dockerfile`."""
        return self._cmd_entrypoint_docker("ENTRYPOINT", self.entrypoint)

    @property
    def cmd_docker(self) -> str | None:
        return self._cmd_entrypoint_docker("CMD", self.cmd)

    @staticmethod
    def _cmd_entrypoint_kiwi(
        prefix: Literal["subcommand", "entrypoint"],
        value: list[str] | None,
    ) -> str | None:
        if not value:
            return None
        if len(value) == 1:
            val = value if isinstance(value, str) else value[0]
            return f'\n        <{prefix} execute="{val}"/>'
        else:
            return (
                f"""\n        <{prefix} execute=\"{value[0]}\">
"""
                + "\n".join(f'          <argument name="{arg}"/>' for arg in value[1:])
                + f"""
        </{prefix}>
"""
            )

    @property
    def entrypoint_kiwi(self) -> str | None:
        return self._cmd_entrypoint_kiwi("entrypoint", self.entrypoint)

    @property
    def cmd_kiwi(self) -> str | None:
        return self._cmd_entrypoint_kiwi("subcommand", self.cmd)

    @property
    def config_sh(self) -> str:
        """The full :file:`config.sh` script required for kiwi builds."""
        if not self.config_sh_script and self.custom_end:
            raise ValueError(
                "This image cannot be build as a kiwi image, it has a `custom_end` set."
            )
        return f"""#!{self.config_sh_interpreter}
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: (c) 2022-{datetime.datetime.now().date().strftime("%Y")} SUSE LLC

{_BASH_SET}

test -f /.kconfig && . /.kconfig
test -f /.profile && . /.profile

echo "Configure image: [$kiwi_iname]..."

#============================================
# Import repositories' keys if rpm is present
#--------------------------------------------
if command -v rpm > /dev/null; then
    suseImportBuildKey
fi

{self.config_sh_script}

#=======================================
# Clean up after zypper if it is present
#---------------------------------------
if command -v zypper > /dev/null; then
    zypper -n clean
fi

{LOG_CLEAN}

exit 0
"""

    @property
    def _from_image(self) -> str | None:
        if self.from_image is None:
            return None
        if self.from_image:
            return self.from_image

        if self.os_version == OsVersion.TUMBLEWEED:
            return "opensuse/tumbleweed:latest"
        if self.os_version == OsVersion.SLE16_0:
            return f"{_build_tag_prefix(self.os_version)}/bci-base:{self.os_version}"
        if self.os_version in ALL_OS_LTSS_VERSIONS:
            return f"{_build_tag_prefix(self.os_version)}/sle15:15.{self.os_version}"
        if self.image_type == ImageType.APPLICATION:
            return f"suse/sle15:15.{self.os_version}"

        return f"bci/bci-base:15.{self.os_version}"

    @property
    def dockerfile_from_line(self) -> str:
        if self._from_image is None:
            return ""

        if self.from_target_image:
            return (
                f"FROM {self.from_target_image} AS target\n"
                f"FROM {self._from_image} AS builder"
            )

        return f"FROM {self._from_image}"

    @property
    def kiwi_derived_from_entry(self) -> str:
        if self._from_image is None:
            return ""
        return (
            f" derived_from=\"obsrepositories:/{self._from_image.replace(':', '#')}\""
        )

    @property
    def packages(self) -> str:
        """The list of packages joined so that it can be appended to a
        :command:`zypper in`.

        """
        for pkg in self.package_list:
            if isinstance(pkg, Package) and pkg.pkg_type != PackageType.IMAGE:
                raise ValueError(
                    f"Cannot add a package of type {pkg.pkg_type} into a Dockerfile based build."
                )
        return " ".join(str(pkg) for pkg in self.package_list)

    @overload
    def _kiwi_volumes_expose(
        self,
        main_element: Literal["volumes"],
        entry_element: Literal["volume name"],
        entries: list[str] | None,
    ) -> str: ...

    @overload
    def _kiwi_volumes_expose(
        self,
        main_element: Literal["expose"],
        entry_element: Literal["port number"],
        entries: list[int] | None,
    ) -> str: ...

    def _kiwi_volumes_expose(
        self,
        main_element: Literal["volumes", "expose"],
        entry_element: Literal["volume name", "port number"],
        entries: list[int] | list[str] | None,
    ) -> str:
        if not entries:
            return ""

        res = f"""
        <{main_element}>
"""
        for entry in entries:
            res += f"""          <{entry_element}="{entry}" />
"""
        res += f"""        </{main_element}>"""
        return res

    @property
    def volumes_kiwi(self) -> str:
        """The volumes for this image as xml elements that are inserted into
        a container.
        """
        return self._kiwi_volumes_expose("volumes", "volume name", self.volumes)

    @property
    def exposes_kiwi(self) -> str:
        """The EXPOSES for this image as kiwi xml elements."""
        return self._kiwi_volumes_expose("expose", "port number", self.exposes_tcp)

    @overload
    def _dockerfile_volume_expose(
        self,
        instruction: Literal["EXPOSE"],
        entries: list[int] | None,
    ) -> str: ...

    @overload
    def _dockerfile_volume_expose(
        self,
        instruction: Literal["VOLUME"],
        entries: list[str] | None,
    ) -> str: ...

    def _dockerfile_volume_expose(
        self,
        instruction: Literal["EXPOSE", "VOLUME"],
        entries: list[int] | list[str] | None,
    ):
        if not entries:
            return ""

        return "\n" + f"{instruction} " + " ".join(str(e) for e in entries)

    @property
    def volume_dockerfile(self) -> str:
        return self._dockerfile_volume_expose("VOLUME", self.volumes)

    @property
    def expose_dockerfile(self) -> str:
        return self._dockerfile_volume_expose("EXPOSE", self.exposes_tcp)

    @property
    def kiwi_packages(self) -> str:
        """The package list as xml elements that are inserted into a kiwi build
        description file.
        """

        def create_pkg_filter_func(
            pkg_type: PackageType,
        ) -> Callable[[str | Package], bool]:
            def pkg_filter_func(p: str | Package) -> bool:
                if isinstance(p, str):
                    return pkg_type == PackageType.IMAGE
                return p.pkg_type == pkg_type

            return pkg_filter_func

        def pkg_listing_func(pkg: Package) -> str:
            return f'<package name="{pkg}"/>'

        PKG_TYPES = (
            PackageType.DELETE,
            PackageType.BOOTSTRAP,
            PackageType.IMAGE,
            PackageType.UNINSTALL,
        )
        delete_packages, bootstrap_packages, image_packages, uninstall_packages = (
            list(filter(create_pkg_filter_func(pkg_type), self.package_list))
            for pkg_type in PKG_TYPES
        )

        res = ""
        for pkg_list, pkg_type in zip(
            (delete_packages, bootstrap_packages, image_packages, uninstall_packages),
            PKG_TYPES,
        ):
            if pkg_list:
                res += (
                    f"""  <packages type="{pkg_type}">
    """
                    + "\n    ".join(pkg_listing_func(pkg) for pkg in pkg_list)
                    + """
  </packages>
"""
                )
        return res

    @property
    def env_lines(self) -> str:
        """Part of the :file:`Dockerfile` that sets every environment variable defined
        in :py:attr:`~BaseContainerImage.env`.

        """
        return (
            ""
            if not self.env
            else "\n" + "\n".join(f'ENV {k}="{v}"' for k, v in self.env.items()) + "\n"
        )

    @property
    def kiwi_env_entry(self) -> str:
        """Environment variable settings for a kiwi build recipe."""
        if not self.env:
            return ""
        return (
            """\n        <environment>
          """
            + """
          """.join(f'<env name="{k}" value="{v}"/>' for k, v in self.env.items())
            + """
        </environment>
"""
        )

    @property
    @abc.abstractmethod
    def image_type(self) -> ImageType:
        """Define the value of the ``com.suse.image-type`` label."""
        pass

    @property
    @abc.abstractmethod
    def build_tags(self) -> list[str]:
        """All build tags that will be added to this image. Note that build tags are
        full paths on the registry and not just a tag.

        """
        pass

    @property
    @abc.abstractmethod
    def image_ref_name(self) -> str:
        """The immutable reference for this target under which this image can be pulled. It is used
        to set the ``org.opencontainers.image.ref.name`` OCI annotation and defaults to
        ``{self.build_tags[0]}``.
        """
        pass

    @property
    @abc.abstractmethod
    def reference(self) -> str:
        """The primary URL via which this image can be pulled. It is used to set the
        ``org.opensuse.reference`` label and defaults to
        ``{self.registry}/{self.image_ref_name}``.

        """
        pass

    @property
    @abc.abstractmethod
    def pretty_reference(self) -> str:
        """Returns the human readable registry URL to this image. It is intended
        to be used in the image documentation.

        This url needn't point to an exact version-release but can include just
        the major os version or the latest tag.

        """

    @property
    def description(self) -> str:
        """The description of this image which is inserted into the
        ``org.opencontainers.image.description`` label.

        If :py:attr:`BaseContainerImage.custom_description` is set, then that
        value is used. Custom descriptions can use str.format() substitution to
        expand the custom description with the following options:

        - ``{pretty_name}``: the value of the pretty_name property
        - ``{based_on_container}``: the standard "based on the $distro Base Container Image" suffix that descriptions have
        - ``{podman_only}``: "This container is only supported with podman."
        - ``{privileged_only}``: "This container is only supported in privileged mode."

        Otherwise it reuses
        :py:attr:`BaseContainerImage.pretty_name` to generate a description.

        """

        description_formatters = {
            "pretty_name": self.pretty_name,
            "based_on_container": (
                f"based on the {self.distribution_base_name} Base Container Image"
            ),
            "podman_only": "This container is only supported with podman.",
            "privileged_only": "This container is only supported in privileged mode.",
        }
        description = "{pretty_name} container {based_on_container}."
        if self.custom_description:
            description = self.custom_description

        return description.format(**description_formatters)

    @property
    def title(self) -> str:
        """The image title that is inserted into the ``org.opencontainers.image.title``
        label.

        It is generated from :py:attr:`BaseContainerImage.pretty_name` as
        follows: ``"{distribution_base_name} BCI {self.pretty_name}"``, where
        ``distribution_base_name`` is taken from
        :py:attr:`~ImageProperties.distribution_base_name`.

        """
        return f"{self.distribution_base_name} BCI {self.pretty_name}"

    @property
    def readme_path(self) -> str:
        return f"{self.package_name}/README.md"

    @property
    def readme_url(self) -> str:
        # we cannot use %SOURCEURL% for Tumbleweed, as it points directly to OBS
        # with a url like:
        # https://build.opensuse.org/package/show/openSUSE:Factory/ruby-3.2-image?rev=2bf407f529a768e95f024bce5a916c69
        # to point to the README, we'd have to inject something *before* the query
        if self.os_version.is_tumbleweed:
            return f"https://raw.githubusercontent.com/SUSE/BCI-dockerfile-generator/{self.os_version.deployment_branch_name}/{self.readme_path}"

        return "%SOURCEURL%/README.md"

    @property
    def readme(self) -> str:
        if "README.md" in self.extra_files:
            if isinstance(self.extra_files["README.md"], bytes):
                return self.extra_files["README.md"].decode("utf-8")
            return str(self.extra_files["README.md"])

        # default template if no custom README.md.j2 template is provided in the package folder
        readme_template = textwrap.dedent(f"""
            # The {self.title} container image
            {{% include 'badges.j2' %}}

            {self.description}

            {{% include 'licensing_and_eula.j2' %}}
            """).strip()
        readme_template_fname = Path(__file__).parent / self.name / "README.md.j2"
        if readme_template_fname.exists():
            readme_template = readme_template_fname.read_text()

        jinja2_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
            autoescape=jinja2.select_autoescape(["md"]),
        )
        return jinja2_env.from_string(readme_template).render(image=self)

    @property
    def extra_label_lines(self) -> str:
        """Lines for a :file:`Dockerfile` to set the additional labels defined in
        :py:attr:`BaseContainerImage.extra_labels`.

        """
        return (
            ""
            if not self.extra_labels
            else "\n"
            + "\n".join(f'LABEL {k}="{v}"' for k, v in self.extra_labels.items())
        )

    @property
    def extra_label_xml_lines(self) -> str:
        """XML Elements for a kiwi build description to set the additional labels
        defined in :py:attr:`BaseContainerImage.extra_labels`.

        """

        if not self.extra_labels:
            return ""

        return "\n" + "\n".join(
            f'            <label name="{k}" value="{v}"/>'
            for k, v in self.extra_labels.items()
        )

    @property
    def labelprefix(self) -> str:
        """The label prefix used to duplicate the labels. See
        `<https://en.opensuse.org/Building_derived_containers#Labels>`_ for
        further information.

        This value is by default ``com.suse.bci.{self.name}`` for images of type
        :py:attr:`ImageType.SLE_BCI` and ```com.suse.application.{self.name}``
        for images of type :py:attr:`ImageType.APPLICATION` unless
        :py:attr:`BaseContainerImage.custom_labelprefix_end` is set. In that
        case ``self.name`` is replaced by
        :py:attr:`~BaseContainerImage.custom_labelprefix_end`.

        """
        labelprefix = "com.suse"
        if self.os_version.is_tumbleweed:
            labelprefix = "org.opensuse"
        return (
            labelprefix
            + "."
            + (
                {
                    ImageType.SLE_BCI: "bci",
                    ImageType.APPLICATION: "application",
                    ImageType.LTSS: "sle",
                }[self.image_type]
            )
            + "."
            + (self.custom_labelprefix_end or self.name)
        )

    @property
    def kiwi_version(self) -> str:
        if self.os_version in (OsVersion.TUMBLEWEED, OsVersion.SLE16_0):
            return str(datetime.datetime.now().year)
        return f"15.{int(self.os_version.value)}.0"

    @property
    def kiwi_additional_tags(self) -> str | None:
        """Entry for the ``additionaltags`` attribute in the kiwi build
        description.

        This attribute is used by kiwi to add additional tags to the image under
        it's primary name. This string contains a coma separated list of all
        build tags (except for the primary one) that have the **same** name as
        the image itself.

        """
        extra_tags: list[str] = []
        all_tags = self.build_tags
        first_path = all_tags[0].partition(":")[0]
        for buildtag in all_tags[1:]:
            path, tag = buildtag.split(":")
            if path.endswith(first_path):
                extra_tags.append(tag)

        return ",".join(extra_tags) if extra_tags else None

    async def write_files_to_folder(self, dest: str) -> list[str]:
        """Writes all files required to build this image into the destination folder and
        returns the filenames (not full paths) that were written to the disk.

        """
        files = ["_service"]
        tasks = []

        async def write_file_to_dest(fname: str, contents: str | bytes) -> None:
            await write_to_file(os.path.join(dest, fname), contents)

        if self.build_recipe_type == BuildType.DOCKER:
            fname = "Dockerfile"
            infoheader = textwrap.indent(INFOHEADER_TEMPLATE, "# ")

            dockerfile = DOCKERFILE_TEMPLATE.render(
                image=self,
                INFOHEADER=infoheader,
                DOCKERFILE_RUN=DOCKERFILE_RUN,
                LOG_CLEAN=LOG_CLEAN,
            )
            if dockerfile[-1] != "\n":
                dockerfile += "\n"

            tasks.append(asyncio.ensure_future(write_file_to_dest(fname, dockerfile)))
            files.append(fname)

        elif self.build_recipe_type == BuildType.KIWI:
            fname = f"{self.package_name}.kiwi"
            tasks.append(
                asyncio.ensure_future(
                    write_file_to_dest(
                        fname,
                        KIWI_TEMPLATE.render(
                            image=self, INFOHEADER=INFOHEADER_TEMPLATE
                        ),
                    )
                )
            )
            files.append(fname)

            if self.config_sh:
                tasks.append(
                    asyncio.ensure_future(
                        write_file_to_dest("config.sh", self.config_sh)
                    )
                )
                files.append("config.sh")

        else:
            assert (
                False
            ), f"got an unexpected build_recipe_type: '{self.build_recipe_type}'"

        tasks.append(
            asyncio.ensure_future(
                write_file_to_dest("_service", SERVICE_TEMPLATE.render(image=self))
            )
        )

        changes_file_name = self.package_name + ".changes"
        if not (Path(dest) / changes_file_name).exists():
            name_to_include = self.pretty_name
            if "%" in name_to_include:
                name_to_include = self.name.capitalize()

            if hasattr(self, "version"):
                ver = self.version
                # we don't want to include the version for language stack
                # containers with the version_in_uid flag set to False, but by
                # default we include it (for os containers which don't have this
                # flag)
                if str(ver) not in name_to_include and getattr(
                    self, "version_in_uid", True
                ):
                    name_to_include += f" {ver}"
            tasks.append(
                asyncio.ensure_future(
                    write_file_to_dest(
                        changes_file_name,
                        f"""-------------------------------------------------------------------
{datetime.datetime.now(tz=datetime.timezone.utc).strftime("%a %b %d %X %Z %Y")} - SUSE Update Bot <bci-internal@suse.de>

- First version of the {name_to_include} BCI
""",
                    )
                )
            )
            files.append(changes_file_name)

        for fname, contents in self.extra_files.items():
            files.append(fname)
            tasks.append(write_file_to_dest(fname, contents))

        if "README.md" not in self.extra_files:
            files.append("README.md")
            tasks.append(write_file_to_dest("README.md", self.readme))

        await asyncio.gather(*tasks)

        return files


@dataclass
class DevelopmentContainer(BaseContainerImage):
    #: the main version of the language or application inside this container
    #: used for `org.opencontainers.image.version`
    version: str | int = ""

    #: the version-$variant to use in the first build_tag. defaults to version
    #: if not set.
    tag_version: str | None = None

    # a rolling stability tag like 'stable' or 'oldstable' that will be added first
    stability_tag: str | None = None

    #: versions that to include as tags to this container
    additional_versions: list[str] = field(default_factory=list)

    #: flag whether the version is included in the uid
    version_in_uid: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.version:
            raise ValueError("A language stack container requires a version")
        if not self.tag_version:
            self.tag_version = self.version

    @property
    def _registry_prefix(self) -> str:
        if self.os_version.is_tumbleweed:
            return "opensuse/bci"
        return "bci"

    @property
    def image_type(self) -> ImageType:
        return ImageType.SLE_BCI

    @property
    def oci_version(self) -> str:
        return str(self.version)

    @property
    def uid(self) -> str:
        return f"{self.name}-{self.tag_version}" if self.version_in_uid else self.name

    @property
    def _stability_suffix(self) -> str:
        # The stability-tags feature in containers may result in the generation of
        # identical release numbers for the same version from two different package
        # containers, such as "oldstable" and "stable."
        #
        # When a new version is committed, the check-in counter and the rebuild
        # counters are reset to "1", resulting in a release number like 1.1.
        # Subsequent changes will have release numbers like 1.2 (rebuild on the same source)
        # and 2.1 (new source change without version change).
        #
        # Here's an example:
        #   lang-stable: 1.70-1.1 (first build of the very first commit after version update)
        #   lang-oldstable: 1.69-5.1 (first build of the fifth source change after version update)

        # After a version rollover occurs from "stable" to "oldstable", the release numbers become:

        #   lang-oldstable: 1.70-1.1
        #   lang-stable: 1.71-1.1

        # Now there is a conflict with the tags that were previously produced by the lang-stable
        # container (see lang-stable-1.70-1.1 above).
        #
        # In order To resolve this, the solution is to namespace
        # the tags with a prefix based on the stability ordering. This ensures that we have:

        #   lang-stable: 1.70-1.1.1
        #   lang-oldstable: 1.69-2.5.1

        # After a version rollover, the numbers now become:

        #   lang-oldstable: 1.70-2.1.1
        #   lang-stable: 1.71-1.1.1

        # To avoid conflicts, the tags are deconflicted based on the stability ordering.
        _STABILITY_TAG_ORDERING = (None, "stable", "oldstable")
        if self.stability_tag and self.stability_tag in _STABILITY_TAG_ORDERING:
            return f"{_STABILITY_TAG_ORDERING.index(self.stability_tag)}"
        return ""

    @property
    def _release_suffix(self) -> str:
        if self._stability_suffix:
            return f"{self._stability_suffix}.%RELEASE%"
        return "%RELEASE%"

    @property
    def build_tags(self) -> list[str]:
        tags = []

        for name in [self.name] + self.additional_names:
            ver_labels: list[str] = [self.tag_version]
            if self.stability_tag:
                ver_labels = [self.stability_tag] + ver_labels
            for ver_label in ver_labels + self.additional_versions:
                tags += [f"{self._registry_prefix}/{name}:{ver_label}"]
                tags += [
                    f"{self._registry_prefix}/{name}:{ver_label}-{self._release_suffix}"
                ]
            if self.is_latest:
                tags += [f"{self._registry_prefix}/{name}:latest"]
        return tags

    @property
    def image_ref_name(self) -> str:
        return f"{self.tag_version}-{self._release_suffix}"

    @property
    def reference(self) -> str:
        return (
            f"{self.registry}/{self._registry_prefix}/{self.name}:{self.image_ref_name}"
        )

    @property
    def pretty_reference(self) -> str:
        return f"{self.registry}/{self._registry_prefix}/{self.name}:{self.tag_version}"

    @property
    def build_version(self) -> str | None:
        build_ver = super().build_version
        if build_ver:
            # if self.version is a numeric version and not a macro, then
            # version.parse() returns a `Version` object => then we concatenate
            # it with the existing build_version
            # for non PEP440 versions, we'll get an exception and just return
            # the parent's classes build_version
            try:
                version.parse(str(self.version))
                stability_suffix: str = ""
                if self._stability_suffix:
                    stability_suffix = "." + self._stability_suffix
                return f"{build_ver}.{self.version}{stability_suffix}"
            except version.InvalidVersion:
                return build_ver
        return None


@dataclass
class ApplicationStackContainer(DevelopmentContainer):
    def __post_init__(self) -> None:
        self._min_release_counter = 35
        super().__post_init__()

    @property
    def _registry_prefix(self) -> str:
        if self.os_version.is_tumbleweed:
            return "opensuse"
        return "suse"

    @property
    def image_type(self) -> ImageType:
        return ImageType.APPLICATION

    @property
    def title(self) -> str:
        return f"{self.distribution_base_name} {self.pretty_name}"

    @property
    def eula(self) -> str:
        """SLE BCI Application containers are non-redistributable by default."""
        if self.os_version.is_tumbleweed:
            return "sle-bci"
        return "sle-eula"


@dataclass
class OsContainer(BaseContainerImage):
    @staticmethod
    def version_to_container_os_version(os_version: OsVersion) -> str:
        if os_version in (OsVersion.TUMBLEWEED, OsVersion.SLE16_0):
            return "latest"
        return f"15.{os_version}"

    @property
    def uid(self) -> str:
        return self.name

    @property
    def oci_version(self) -> str:
        return "%OS_VERSION_ID_SP%.%RELEASE%"

    @property
    def image_type(self) -> ImageType:
        if self.os_version in ALL_OS_LTSS_VERSIONS:
            return ImageType.LTSS

        return ImageType.SLE_BCI

    @property
    def build_tags(self) -> list[str]:
        tags: list[str] = []

        for name in [self.name] + self.additional_names:
            tags += [
                f"{self._registry_prefix}/bci-{name}:%OS_VERSION_ID_SP%",
                f"{self._registry_prefix}/bci-{name}:{self.image_ref_name}",
            ] + (
                [f"{self._registry_prefix}/bci-{name}:latest"] if self.is_latest else []
            )
        return tags

    @property
    def image_ref_name(self) -> str:
        return self.oci_version

    @property
    def reference(self) -> str:
        return f"{self.registry}/{self._registry_prefix}/bci-{self.name}:{self.image_ref_name}"

    @property
    def pretty_reference(self) -> str:
        return f"{self.registry}/{self._registry_prefix}/bci-{self.name}:{self.os_version.os_version}"


def generate_disk_size_constraints(size_gb: int) -> str:
    """Creates the contents of a :file:`_constraints` file for OBS to require
    workers with at least ``size_gb`` GB of disk space.

    """
    return f"""<constraints>
  <hardware>
    <disk>
      <size unit="G">{size_gb}</size>
    </disk>
  </hardware>
</constraints>
"""


from .apache_tomcat import TOMCAT_CONTAINERS  # noqa: E402
from .appcontainers import ALERTMANAGER_CONTAINERS  # noqa: E402
from .appcontainers import BLACKBOX_EXPORTER_CONTAINERS  # noqa: E402
from .appcontainers import GIT_CONTAINERS  # noqa: E402
from .appcontainers import GRAFANA_CONTAINERS  # noqa: E402
from .appcontainers import HELM_CONTAINERS  # noqa: E402
from .appcontainers import NGINX_CONTAINERS  # noqa: E402
from .appcontainers import PCP_CONTAINERS  # noqa: E402
from .appcontainers import POSTGRES_CONTAINERS  # noqa: E402
from .appcontainers import PROMETHEUS_CONTAINERS  # noqa: E402
from .appcontainers import REGISTRY_CONTAINERS  # noqa: E402
from .appcontainers import THREE_EIGHT_NINE_DS_CONTAINERS  # noqa: E402
from .appcontainers import TRIVY_CONTAINERS  # noqa: E402
from .base import BASE_CONTAINERS  # noqa: E402
from .basecontainers import BUSYBOX_CONTAINERS  # noqa: E402
from .basecontainers import FIPS_BASE_CONTAINERS  # noqa: E402
from .basecontainers import GITEA_RUNNER_CONTAINER  # noqa: E402
from .basecontainers import INIT_CONTAINERS  # noqa: E402
from .basecontainers import KERNEL_MODULE_CONTAINERS  # noqa: E402
from .basecontainers import MICRO_CONTAINERS  # noqa: E402
from .basecontainers import MINIMAL_CONTAINERS  # noqa: E402
from .gcc import GCC_CONTAINERS  # noqa: E402
from .golang import GOLANG_CONTAINERS  # noqa: E402
from .kiwi import KIWI_CONTAINERS  # noqa: E402
from .mariadb import MARIADB_CLIENT_CONTAINERS  # noqa: E402
from .mariadb import MARIADB_CONTAINERS  # noqa: E402
from .node import NODE_CONTAINERS  # noqa: E402
from .openjdk import OPENJDK_CONTAINERS  # noqa: E402
from .php import PHP_CONTAINERS  # noqa: E402
from .postfix import POSTFIX_CONTAINERS  # noqa: E402
from .python import PYTHON_3_6_CONTAINERS  # noqa: E402
from .python import PYTHON_3_11_CONTAINERS  # noqa: E402
from .python import PYTHON_3_12_CONTAINERS  # noqa: E402
from .python import PYTHON_TW_CONTAINERS  # noqa: E402
from .rmt import RMT_CONTAINERS  # noqa: E402
from .ruby import RUBY_CONTAINERS  # noqa: E402
from .rust import RUST_CONTAINERS  # noqa: E402
from .spack import SPACK_CONTAINERS  # noqa: E402

ALL_CONTAINER_IMAGE_NAMES: dict[str, BaseContainerImage] = {
    f"{bci.uid}-{bci.os_version.pretty_print.lower()}": bci
    for bci in (
        *BASE_CONTAINERS,
        PYTHON_3_12_CONTAINERS,
        *PYTHON_3_6_CONTAINERS,
        *PYTHON_3_11_CONTAINERS,
        *PYTHON_TW_CONTAINERS,
        *THREE_EIGHT_NINE_DS_CONTAINERS,
        *NGINX_CONTAINERS,
        *PCP_CONTAINERS,
        *REGISTRY_CONTAINERS,
        *HELM_CONTAINERS,
        *TRIVY_CONTAINERS,
        *RMT_CONTAINERS,
        *RUST_CONTAINERS,
        *GIT_CONTAINERS,
        *GOLANG_CONTAINERS,
        *KIWI_CONTAINERS,
        *RUBY_CONTAINERS,
        *NODE_CONTAINERS,
        *OPENJDK_CONTAINERS,
        *PHP_CONTAINERS,
        *INIT_CONTAINERS,
        *FIPS_BASE_CONTAINERS,
        *MARIADB_CONTAINERS,
        *MARIADB_CLIENT_CONTAINERS,
        *POSTFIX_CONTAINERS,
        *POSTGRES_CONTAINERS,
        *PROMETHEUS_CONTAINERS,
        *ALERTMANAGER_CONTAINERS,
        *BLACKBOX_EXPORTER_CONTAINERS,
        *GRAFANA_CONTAINERS,
        *MINIMAL_CONTAINERS,
        *MICRO_CONTAINERS,
        *BUSYBOX_CONTAINERS,
        *KERNEL_MODULE_CONTAINERS,
        GITEA_RUNNER_CONTAINER,
        *TOMCAT_CONTAINERS,
        *GCC_CONTAINERS,
        *SPACK_CONTAINERS,
    )
}

SORTED_CONTAINER_IMAGE_NAMES = sorted(
    ALL_CONTAINER_IMAGE_NAMES,
    key=lambda bci: f"{ALL_CONTAINER_IMAGE_NAMES[bci].os_version}-{ALL_CONTAINER_IMAGE_NAMES[bci].name}",
)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        "Write the contents of a package directly to the filesystem"
    )

    parser.add_argument(
        "image",
        type=str,
        nargs=1,
        choices=SORTED_CONTAINER_IMAGE_NAMES,
        help="The BCI container image, which package contents should be written to the disk",
    )
    parser.add_argument(
        "destination",
        type=str,
        nargs=1,
        help="destination folder to which the files should be written",
    )

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        ALL_CONTAINER_IMAGE_NAMES[args.image[0]].write_files_to_folder(
            args.destination[0]
        )
    )
