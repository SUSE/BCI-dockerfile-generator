#!/usr/bin/env python3
from __future__ import annotations

import abc
import asyncio
import datetime
import enum
import os
import textwrap
from dataclasses import dataclass
from dataclasses import field
from itertools import product
from typing import Callable
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import overload
from typing import Union

from bci_build.templates import DOCKERFILE_TEMPLATE
from bci_build.templates import KIWI_TEMPLATE
from bci_build.templates import SERVICE_TEMPLATE
from bci_build.util import write_to_file
from packaging import version


_BASH_SET = "set -euo pipefail"

#: a ``RUN`` command with a common set of bash flags applied to prevent errors
#: from not being noticed
DOCKERFILE_RUN = f"RUN {_BASH_SET};"


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
        if self.value == OsVersion.TUMBLEWEED.value:
            return self.value
        return f"SP{self.value}"

    @property
    def pretty_os_version_no_dash(self) -> str:
        if self.value == OsVersion.TUMBLEWEED.value:
            return f"openSUSE {self.value}"

        return f"15 SP{self.value}"


#: Operating system versions that have the label ``com.suse.release-stage`` set
#: to ``released``.
RELEASED_OS_VERSIONS = [OsVersion.SP4, OsVersion.SP5, OsVersion.TUMBLEWEED]

# For which versions to create Application and Language Containers?
ALL_NONBASE_OS_VERSIONS = [OsVersion.SP5, OsVersion.TUMBLEWEED]

# For which versions to create Base Container Images?
ALL_BASE_OS_VERSIONS = [OsVersion.SP4, OsVersion.SP5, OsVersion.TUMBLEWEED]

# joint set of BASE and NON_BASE versions
ALL_OS_VERSIONS = {v for v in (*ALL_BASE_OS_VERSIONS, *ALL_NONBASE_OS_VERSIONS)}

CAN_BE_LATEST_OS_VERSION = [OsVersion.SP5, OsVersion.TUMBLEWEED]


# End of General Support Dates
_SUPPORTED_UNTIL_SLE = {
    OsVersion.SP4: datetime.date(2023, 12, 31),
    OsVersion.SP5: None,  # datetime.date(2024, 12, 31),
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


@dataclass
class Replacement:
    """Represents a replacement via the `obs-service-replace_using_package_version
    <https://github.com/openSUSE/obs-service-replace_using_package_version>`_.

    """

    #: regex to be replaced in :file:`Dockerfile` or :file:`$pkg_name.kiwi`
    regex_in_build_description: str

    #: package name to be queried for the version
    package_name: str

    #: specify how the version should be formated, see
    #: `<https://github.com/openSUSE/obs-service-replace_using_package_version#usage>`_
    #: for further details
    parse_version: Optional[
        Literal["major", "minor", "patch", "patch_update", "offset"]
    ] = None


def _build_tag_prefix(os_version: OsVersion) -> str:
    return "opensuse/bci" if os_version == OsVersion.TUMBLEWEED else "bci"


@dataclass(frozen=True)
class ImageProperties:
    """Class storing the properties of the Base Container that differ
    depending on the vendor.

    """

    #: maintainer of the image
    maintainer: str

    #: full vendor string as it will be included in the
    #: ``org.opencontainers.image.vendor`` label
    vendor: str

    #: The name of the underlying distribution. It will be inserted into the
    #: image's title as ``$distribution_base_name BCI $pretty_name Container
    #: Image``.
    distribution_base_name: str

    #: The url to the registry of this vendor
    registry: str

    #: Url to the vendor's home page
    url: str

    #: Url to learn about the support lifecycle of the image
    lifecycle_url: str

    #: The prefix of the label names ``$label_prefix.bci.$label = foobar``
    label_prefix: str

    #: The prefix of the build tag for LanguageStackContainer and OsContainer Images.
    #: The build tag is constructed as `$build_tag_prefix/$name`
    build_tag_prefix: str

    #: Same as :py:attr:`build_tag_prefix` but for ApplicationStackContainer Images.
    application_container_build_tag_prefix: str


#: Image properties for openSUSE Tumbleweed
_OPENSUSE_IMAGE_PROPS = ImageProperties(
    maintainer="openSUSE (https://www.opensuse.org/)",
    vendor="openSUSE Project",
    registry="registry.opensuse.org",
    url="https://www.opensuse.org",
    lifecycle_url="https://en.opensuse.org/Lifetime",
    label_prefix="org.opensuse",
    distribution_base_name="openSUSE Tumbleweed",
    build_tag_prefix=_build_tag_prefix(OsVersion.TUMBLEWEED),
    application_container_build_tag_prefix="opensuse",
)

#: Image properties for SUSE Linux Enterprise
_SLE_IMAGE_PROPS = ImageProperties(
    maintainer="SUSE LLC (https://www.suse.com/)",
    vendor="SUSE LLC",
    registry="registry.suse.com",
    url="https://www.suse.com/products/server/",
    lifecycle_url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15",
    label_prefix="com.suse",
    distribution_base_name="SLE",
    build_tag_prefix=_build_tag_prefix(OsVersion.SP4),
    application_container_build_tag_prefix="suse",
)


@dataclass
class BaseContainerImage(abc.ABC):
    """Base class for all Base Containers."""

    #: Name of this image. It is used to generate the build tags, i.e. it
    #: defines under which name this image is published.
    name: str

    #: Human readable name that will be inserted into the image title and description
    pretty_name: str

    #: The name of the package on OBS or IBS in ``devel:BCI:SLE-15-SP$ver`` (on
    #: OBS) or ``SUSE:SLE-15-SP$ver:Update:BCI`` (on IBS)
    package_name: str

    #: The SLE service pack to which this package belongs
    os_version: OsVersion

    #: The container from which this one is derived. defaults to
    #: ``suse/sle15:15.$SP`` (for SLE) or ``opensuse/tumbleweed:latest`` (for
    #: Tumbleweed) when an empty string is used.
    #:
    #: When from image is ``None``, then this image will not be based on
    #: **anything**, i.e. the ``FROM`` line is missing in the ``Dockerfile``.
    from_image: Optional[str] = ""

    #: Architectures of this image.
    #:
    #: If supplied, then this image will be restricted to only build on the
    #: supplied architectures. By default, there is no restriction
    exclusive_arch: list[Arch] | None = None

    #: Determines whether this image will have the ``latest`` tag.
    is_latest: bool = False

    #: An optional entrypoint for the image, it is omitted if empty or ``None``
    #: If you provide a string, then it will be included in the container build
    #: recipe as is, i.e. it will be called via a shell as
    #: :command:`sh -c "MY_CMD"`.
    #: If your entrypoint must not be called through a shell, then pass the
    #: binary and its parameters as a list
    entrypoint: Optional[List[str]] = None

    # The user to use for entrypoint service
    entrypoint_user: Optional[str] = ""

    #: An optional CMD for the image, it is omitted if empty or ``None``
    cmd: Optional[List[str]] = None

    #: An optional list of volumes, it is omitted if empty or ``None``
    volumes: Optional[List[str]] = None

    #: An optional list of tcp port exposes, it is omitted if empty or ``None``
    exposes_tcp: Optional[List[int]] = None

    #: Extra environment variables to be set in the container
    env: Union[Dict[str, Union[str, int]], Dict[str, str], Dict[str, int]] = field(
        default_factory=dict
    )

    #: Add any replacements via `obs-service-replace_using_package_version
    #: <https://github.com/openSUSE/obs-service-replace_using_package_version>`_
    #: that are used in this image into this list.
    #: See also :py:class:`~Replacement`
    replacements_via_service: List[Replacement] = field(default_factory=list)

    #: Additional labels that should be added to the image. These are added into
    #: the ``PREFIXEDLABEL`` section.
    extra_labels: Dict[str, str] = field(default_factory=dict)

    #: Packages to be installed inside the container image
    package_list: Union[List[str], List[Package]] = field(default_factory=list)

    #: This string is appended to the automatically generated dockerfile and can
    #: contain arbitrary instructions valid for a :file:`Dockerfile`.
    #: **Caution** Setting both this property and
    #: :py:attr:`~BaseContainerImage.config_sh_script` is not possible and will
    #: result in an error.
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

    #: The maintainer of this image, defaults to SUSE/openSUSE
    maintainer: Optional[str] = None

    #: Additional files that belong into this container-package.
    #: The key is the filename, the values are the file contents.
    extra_files: Union[
        Dict[str, Union[str, bytes]], Dict[str, bytes], Dict[str, str]
    ] = field(default_factory=dict)

    #: Additional names under which this image should be published alongside
    #: :py:attr:`~BaseContainerImage.name`.
    #: These names are only inserted into the
    #: :py:attr:`~BaseContainerImage.build_tags`
    additional_names: List[str] = field(default_factory=list)

    #: By default the containers get the labelprefix
    #: ``{label_prefix}.bci.{self.name}``. If this value is not an empty string,
    #: then it is used instead of the name after ``com.suse.bci.``.
    custom_labelprefix_end: str = ""

    #: Provide a custom description instead of the automatically generated one
    custom_description: str = ""

    #: Define whether this container image is built using docker or kiwi.
    #: If not set, then the build type will default to docker from SP4 onwards.
    build_recipe_type: Optional[BuildType] = None

    #: A license string to be placed in a comment at the top of the Dockerfile
    #: or kiwi build description file.
    license: str = "MIT"

    #: The support level for this image, defaults to :py:attr:`SupportLevel.TECHPREVIEW`
    support_level: SupportLevel = SupportLevel.TECHPREVIEW

    #: The support level end date
    supported_until: Optional[datetime.date] = None

    #: flag whether to not install recommended packages in the call to
    #: :command:`zypper` in :file:`Dockerfile`
    no_recommends: bool = True

    _image_properties: ImageProperties = field(default=_SLE_IMAGE_PROPS)

    def __post_init__(self) -> None:
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
        self._image_properties = (
            _OPENSUSE_IMAGE_PROPS if self.is_opensuse else _SLE_IMAGE_PROPS
        )
        if not self.maintainer:
            self.maintainer = self._image_properties.maintainer

    @property
    def is_opensuse(self) -> bool:
        return self.os_version == OsVersion.TUMBLEWEED

    @property
    @abc.abstractmethod
    def uid(self) -> str:
        """unique identifier of this image, either its name or ``$name-$version``."""
        pass

    @property
    @abc.abstractmethod
    def version_label(self) -> str:
        """The "main" version label of this image.

        It is added as the ``org.opencontainers.image.version`` label to the
        container image and also added to the
        :py:attr:`~BaseContainerImage.build_tags`.

        """
        pass

    @property
    def build_version(self) -> Optional[str]:
        if self.os_version in (OsVersion.SP4, OsVersion.SP5):
            return f"15.{int(self.os_version.value)}"
        return None

    @property
    def lifecycle_url(self) -> str:
        return self._image_properties.lifecycle_url

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
        return self._image_properties.url

    @property
    def vendor(self) -> str:
        """The vendor that is put into the ``org.opencontainers.image.vendor``
        label

        """
        return self._image_properties.vendor

    @property
    def registry(self) -> str:
        """The registry where the image is available on."""
        return self._image_properties.registry

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
        return self._image_properties.build_tag_prefix

    @staticmethod
    def _cmd_entrypoint_docker(
        prefix: Literal["CMD", "ENTRYPOINT"], value: Optional[List[str]]
    ) -> Optional[str]:
        if not value:
            return None
        if isinstance(value, list):
            return "\n" + prefix + " " + str(value).replace("'", '"')
        assert False, f"Unexpected type for {prefix}: {type(value)}"

    @property
    def entrypoint_docker(self) -> Optional[str]:
        """The entrypoint line in a :file:`Dockerfile`."""
        return self._cmd_entrypoint_docker("ENTRYPOINT", self.entrypoint)

    @property
    def cmd_docker(self) -> Optional[str]:
        return self._cmd_entrypoint_docker("CMD", self.cmd)

    @staticmethod
    def _cmd_entrypoint_kiwi(
        prefix: Literal["subcommand", "entrypoint"],
        value: Optional[List[str]],
    ) -> Optional[str]:
        if not value:
            return None
        if len(value) == 1:
            val = value if isinstance(value, str) else value[0]
            return f'\n        <{prefix} execute="{val}"/>'
        else:
            return (
                f"""\n        <{prefix} execute=\"{value[0]}\">
"""
                + "\n".join(
                    (f'          <argument name="{arg}"/>' for arg in value[1:])
                )
                + f"""
        </{prefix}>
"""
            )

    @property
    def entrypoint_kiwi(self) -> Optional[str]:
        return self._cmd_entrypoint_kiwi("entrypoint", self.entrypoint)

    @property
    def cmd_kiwi(self) -> Optional[str]:
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

rm -rf /var/log/zypp

exit 0
"""

    @property
    def _from_image(self) -> Optional[str]:
        if self.from_image is None:
            return None
        if self.from_image:
            return self.from_image

        if self.os_version == OsVersion.TUMBLEWEED:
            return "opensuse/tumbleweed:latest"
        else:
            return f"suse/sle15:15.{self.os_version}"

    @property
    def dockerfile_from_line(self) -> str:
        if self._from_image is None:
            return ""
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
        entries: Optional[List[str]],
    ) -> str:
        ...

    @overload
    def _kiwi_volumes_expose(
        self,
        main_element: Literal["expose"],
        entry_element: Literal["port number"],
        entries: Optional[List[int]],
    ) -> str:
        ...

    def _kiwi_volumes_expose(
        self,
        main_element: Literal["volumes", "expose"],
        entry_element: Literal["volume name", "port number"],
        entries: Optional[Union[List[int], List[str]]],
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
        entries: Optional[List[int]],
    ) -> str:
        ...

    @overload
    def _dockerfile_volume_expose(
        self,
        instruction: Literal["VOLUME"],
        entries: Optional[List[str]],
    ) -> str:
        ...

    def _dockerfile_volume_expose(
        self,
        instruction: Literal["EXPOSE", "VOLUME"],
        entries: Optional[Union[List[int], List[str]]],
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
        ) -> Callable[[Union[str, Package]], bool]:
            def pkg_filter_func(p: Union[str, Package]) -> bool:
                if isinstance(p, str):
                    return pkg_type == PackageType.IMAGE
                return p.pkg_type == pkg_type

            return pkg_filter_func

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
            if len(pkg_list) > 0:
                res += (
                    f"""  <packages type="{pkg_type}">
    """
                    + """
    """.join(
                        f'<package name="{pkg}"/>' for pkg in pkg_list
                    )
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
          """.join(
                f'<env name="{k}" value="{v}"/>' for k, v in self.env.items()
            )
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
    def build_tags(self) -> List[str]:
        """All build tags that will be added to this image. Note that build tags are
        full paths on the registry and not just a tag.

        """
        pass

    @property
    @abc.abstractmethod
    def reference(self) -> str:
        """The primary URL via which this image can be pulled. It is used to set the
        ``org.opensuse.reference`` label and defaults to
        ``{self.registry}/{self.build_tags[0]}``.

        """
        pass

    @property
    def description(self) -> str:
        """The description of this image which is inserted into the
        ``org.opencontainers.image.description`` label.

        If :py:attr:`BaseContainerImage.custom_description` is set, then that
        value is used. Otherwise it reuses
        :py:attr:`BaseContainerImage.pretty_name` to generate a description.

        """
        if self.custom_description:
            return self.custom_description

        return (
            f"{self.pretty_name} container based on the "
            f"{self._image_properties.distribution_base_name} Base Container Image."
        )

    @property
    def title(self) -> str:
        """The image title that is inserted into the ``org.opencontainers.image.title``
        label.

        It is generated from :py:attr:`BaseContainerImage.pretty_name` as
        follows: ``"{distribution_base_name} BCI {self.pretty_name}"``, where
        ``distribution_base_name`` is taken from
        :py:attr:`~ImageProperties.distribution_base_name`.

        """
        return f"{self._image_properties.distribution_base_name} BCI {self.pretty_name}"

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
        return (
            self._image_properties.label_prefix
            + "."
            + (
                {ImageType.SLE_BCI: "bci", ImageType.APPLICATION: "application"}[
                    self.image_type
                ]
            )
            + "."
            + (self.custom_labelprefix_end or self.name)
        )

    @property
    def kiwi_version(self) -> str:
        if self.os_version in (OsVersion.TUMBLEWEED,):
            return str(datetime.datetime.now().year)
        return f"15.{int(self.os_version.value)}.0"

    @property
    def kiwi_additional_tags(self) -> Optional[str]:
        """Entry for the ``additionaltags`` attribute in the kiwi build
        description.

        This attribute is used by kiwi to add additional tags to the image under
        it's primary name. This string contains a coma separated list of all
        build tags (except for the primary one) that have the **same** name as
        the image itself.

        """
        extra_tags = []
        for buildtag in self.build_tags[1:]:
            path, tag = buildtag.split(":")
            if path.endswith(self.name):
                extra_tags.append(tag)

        return ",".join(extra_tags) if extra_tags else None

    async def write_files_to_folder(self, dest: str) -> List[str]:
        """Writes all files required to build this image into the destination folder and
        returns the filenames (not full paths) that were written to the disk.

        """
        files = ["_service"]
        tasks = []

        async def write_file_to_dest(fname: str, contents: Union[str, bytes]) -> None:
            await write_to_file(os.path.join(dest, fname), contents)

        if self.build_recipe_type == BuildType.DOCKER:
            fname = "Dockerfile"
            dockerfile = DOCKERFILE_TEMPLATE.render(
                image=self, DOCKERFILE_RUN=DOCKERFILE_RUN
            )
            if dockerfile[-1] != "\n":
                dockerfile += "\n"

            tasks.append(asyncio.ensure_future(write_file_to_dest(fname, dockerfile)))
            files.append(fname)

        elif self.build_recipe_type == BuildType.KIWI:
            fname = f"{self.package_name}.kiwi"
            tasks.append(
                asyncio.ensure_future(
                    write_file_to_dest(fname, KIWI_TEMPLATE.render(image=self))
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
        changes_file_dest = os.path.join(dest, changes_file_name)
        if not os.path.exists(changes_file_dest):
            name_to_include = self.pretty_name
            if "%" in name_to_include:
                name_to_include = self.name.capitalize()

            if hasattr(self, "version"):
                ver = getattr(self, "version")
                # we don't want to include the version for language stack
                # containers with the version_in_uid flag set to False, but by
                # default we include it (for os containers which don't have this
                # flag)
                if str(ver) not in name_to_include and not getattr(
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

        await asyncio.gather(*tasks)

        return files


@dataclass
class LanguageStackContainer(BaseContainerImage):
    #: the primary version of the language or application inside this container
    version: Union[str, int] = ""

    # a rolling stability tag like 'stable' or 'oldstable' that will be added first
    stability_tag: Optional[str] = None

    #: additional versions that should be added as tags to this container
    additional_versions: List[str] = field(default_factory=list)

    #: flag whether the version should be included in the uid
    version_in_uid: bool = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.version:
            raise ValueError("A language stack container requires a version")

    @property
    def image_type(self) -> ImageType:
        return ImageType.SLE_BCI

    @property
    def version_label(self) -> str:
        return str(self.version)

    @property
    def uid(self) -> str:
        return f"{self.name}-{self.version}" if self.version_in_uid else self.name

    @property
    def _release_suffix(self) -> str:
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
            return f"{_STABILITY_TAG_ORDERING.index(self.stability_tag)}.%RELEASE%"
        return "%RELEASE%"

    @property
    def build_tags(self) -> List[str]:
        tags = []

        for name in [self.name] + self.additional_names:
            ver_labels = [self.version_label]
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
    def reference(self) -> str:
        return (
            f"{self.registry}/{self._registry_prefix}/{self.name}"
            + f":{self.version_label}-{self._release_suffix}"
        )

    @property
    def build_version(self) -> Optional[str]:
        build_ver = super().build_version
        if build_ver:
            # if self.version is a numeric version and not a macro, then
            # version.parse() returns a `Version` object => then we concatenate
            # it with the existing build_version
            # for non PEP440 versions, we'll get an exception and just return
            # the parent's classes build_version
            try:
                version.parse(str(self.version))
                return f"{build_ver}.{self.version}"
            except version.InvalidVersion:
                return build_ver
        return None


@dataclass
class ApplicationStackContainer(LanguageStackContainer):
    @property
    def _registry_prefix(self) -> str:
        return self._image_properties.application_container_build_tag_prefix

    @property
    def image_type(self) -> ImageType:
        return ImageType.APPLICATION

    @property
    def title(self) -> str:
        return f"{self._image_properties.distribution_base_name} {self.pretty_name}"


@dataclass
class OsContainer(BaseContainerImage):
    @staticmethod
    def version_to_container_os_version(os_version: OsVersion) -> str:
        if os_version == OsVersion.TUMBLEWEED:
            return "latest"
        return f"15.{os_version}"

    @property
    def uid(self) -> str:
        return self.name

    @property
    def version_label(self) -> str:
        return "%OS_VERSION_ID_SP%.%RELEASE%"

    @property
    def image_type(self) -> ImageType:
        return ImageType.SLE_BCI

    @property
    def build_tags(self) -> List[str]:
        tags = []
        for name in [self.name] + self.additional_names:
            tags += [
                f"{self._registry_prefix}/bci-{name}:%OS_VERSION_ID_SP%",
                f"{self._registry_prefix}/bci-{name}:{self.version_label}",
            ] + (
                [f"{self._registry_prefix}/bci-{name}:latest"] if self.is_latest else []
            )
        return tags

    @property
    def reference(self) -> str:
        return f"{self.registry}/{self._registry_prefix}/bci-{self.name}:{self.version_label}"


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


def _get_python_kwargs(
    py3_ver: Literal["3.6", "3.9", "3.10", "3.11"], os_version: OsVersion
):
    is_system_py: bool = py3_ver == (
        "3.6" if os_version != OsVersion.TUMBLEWEED else "3.11"
    )
    py3_ver_nodots = py3_ver.replace(".", "")

    py3 = (
        "python3"
        if is_system_py and os_version != OsVersion.TUMBLEWEED
        else f"python{py3_ver_nodots}"
    )
    py3_ver_replacement = f"%%py{py3_ver_nodots}_ver%%"
    pip3 = f"{py3}-pip"
    pip3_replacement = "%%pip_ver%%"
    kwargs = {
        "name": "python",
        "pretty_name": f"Python {py3_ver} development",
        "version": py3_ver,
        "additional_versions": ["3"],
        "env": {"PYTHON_VERSION": py3_ver_replacement, "PIP_VERSION": pip3_replacement},
        "package_list": [f"{py3}-devel", py3, pip3, "curl", "git-core"]
        + (
            [f"{py3}-wheel"]
            if is_system_py or os_version == OsVersion.TUMBLEWEED
            else []
        ),
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=py3_ver_replacement,
                package_name=f"{py3}-base",
            ),
            Replacement(regex_in_build_description=pip3_replacement, package_name=pip3),
        ],
        "os_version": os_version,
    }
    if not is_system_py:
        symlink_py_and_pydoc = rf"""ln -s /usr/bin/python{py3_ver} /usr/local/bin/python3; \
    ln -s /usr/bin/pydoc{py3_ver} /usr/local/bin/pydoc"""

        kwargs["config_sh_script"] = symlink_py_and_pydoc

    return kwargs


PYTHON_3_6_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs("3.6", os_version),
        package_name="python-3.6-image",
        support_level=SupportLevel.L3,
    )
    for os_version in (OsVersion.SP5,)
)

_PYTHON_TW_VERSIONS = ("3.9", "3.10", "3.11")
PYTHON_TW_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs(pyver, OsVersion.TUMBLEWEED),
        is_latest=pyver == _PYTHON_TW_VERSIONS[-1],
        package_name=f"python-{pyver}-image",
    )
    for pyver in _PYTHON_TW_VERSIONS
)

PYTHON_3_10_SP4 = LanguageStackContainer(
    package_name="python-3.10-image",
    support_level=SupportLevel.L3,
    is_latest=False,
    **_get_python_kwargs("3.10", OsVersion.SP4),
)

PYTHON_3_11_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs("3.11", os_version),
        package_name="python-3.11-image",
        support_level=SupportLevel.L3,
        # https://peps.python.org/pep-0664/ defines 2027/10/31, SUSE offers until end of the year
        supported_until=datetime.date(2027, 12, 31),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
    )
    for os_version in (OsVersion.SP5,)
)


def _get_ruby_kwargs(ruby_version: Literal["2.5", "3.2"], os_version: OsVersion):
    ruby = f"ruby{ruby_version}"
    ruby_major = ruby_version.split(".")[0]

    return {
        "name": "ruby",
        "package_name": f"ruby-{ruby_version}-image",
        "pretty_name": f"Ruby {ruby_version}",
        "version": ruby_version,
        "additional_versions": [ruby_major],
        "is_latest": os_version in CAN_BE_LATEST_OS_VERSION,
        "os_version": os_version,
        "env": {
            # upstream does this
            "LANG": "C.UTF-8",
            "RUBY_VERSION": "%%rb_ver%%",
            "RUBY_MAJOR": "%%rb_maj%%",
        },
        "replacements_via_service": [
            Replacement(regex_in_build_description="%%rb_ver%%", package_name=ruby),
            Replacement(
                regex_in_build_description="%%rb_maj%%",
                package_name=ruby,
                parse_version="minor",
            ),
        ],
        "package_list": [
            ruby,
            f"{ruby}-rubygem-bundler",
            f"{ruby}-devel",
            # provides getopt, which is required by ruby-common, but OBS doesn't resolve that
            "util-linux",
            "curl",
            "git-core",
            "distribution-release",
            # additional dependencies to build rails, ffi, sqlite3 gems -->
            "gcc-c++",
            "sqlite3-devel",
            "make",
            "awk",
            # additional dependencies supplementing rails
            "timezone",
        ],
        "extra_files": {
            # avoid ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6)
        },
        # as we only ship one ruby version, we want to make sure that binaries belonging
        # to our gems get installed as `bin` and not as `bin.ruby$ruby_version`
        "config_sh_script": "sed -i 's/--format-executable/--no-format-executable/' /etc/gemrc",
    }


RUBY_CONTAINERS = [
    LanguageStackContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP5),
        support_level=SupportLevel.L3,
    ),
    LanguageStackContainer(**_get_ruby_kwargs("3.2", OsVersion.TUMBLEWEED)),
]


_GO_VER_T = Literal["1.19", "1.20"]
_GOLANG_VERSIONS: List[_GO_VER_T] = ["1.19", "1.20"]
_GOLANG_VARIANTS: List[Literal] = ["", "-openssl"]

assert len(_GOLANG_VERSIONS) == 2, "Only two golang versions must be supported"


def _get_golang_kwargs(
    ver: _GO_VER_T, variant: _GOLANG_VARIANTS, os_version: OsVersion
):
    golang_version_regex = "%%golang_version%%"
    is_stable = ver == _GOLANG_VERSIONS[-1]
    stability_tag = f"stable{variant}" if is_stable else f"oldstable{variant}"
    go = f"go{ver}{variant}"
    return {
        "os_version": os_version,
        "package_name": f"golang-{stability_tag}-image",
        "pretty_name": f"Go {ver}{variant} development",
        "name": f"golang",
        "stability_tag": stability_tag,
        "pretty_name": f"Golang {ver}{variant}",
        "is_latest": (is_stable and (os_version in CAN_BE_LATEST_OS_VERSION)),
        "version": f"{ver}{variant}",
        "env": {
            "GOLANG_VERSION": golang_version_regex,
            "GOPATH": "/go",
            "PATH": "/go/bin:/usr/local/go/bin:/root/go/bin/:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        },
        "replacements_via_service": [
            Replacement(
                regex_in_build_description=golang_version_regex, package_name=go
            )
        ],
        "package_list": [go, "distribution-release", "make", "git-core"],
        "extra_files": {
            # the go binaries are huge and will ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(8)
        },
    }


GOLANG_IMAGES = [
    LanguageStackContainer(
        **_get_golang_kwargs(ver, govariant, OsVersion.SP5),
        support_level=SupportLevel.L3,
    )
    for ver, govariant in product(_GOLANG_VERSIONS, _GOLANG_VARIANTS)
] + [
    LanguageStackContainer(
        **_get_golang_kwargs(ver, "", OsVersion.TUMBLEWEED),
        support_level=SupportLevel.L3,
    )
    for ver in _GOLANG_VERSIONS
]

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
        "is_latest": (
            (ver == 18 and os_version == OsVersion.SP4)
            or (ver == 20 and os_version == OsVersion.TUMBLEWEED)
        ),
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
            "distribution-release",
        ],
        "env": {
            "NODE_VERSION": ver,
        },
    }


NODE_CONTAINERS = [
    LanguageStackContainer(
        **_get_node_kwargs(16, OsVersion.SP5), support_level=SupportLevel.L3
    ),
    LanguageStackContainer(
        **_get_node_kwargs(18, OsVersion.SP5), support_level=SupportLevel.L3
    ),
    LanguageStackContainer(**_get_node_kwargs(20, OsVersion.TUMBLEWEED)),
]


def _get_openjdk_kwargs(
    os_version: OsVersion, devel: bool, java_version: Literal[11, 13, 15, 17, 20]
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
        return {
            **common,
            "name": "openjdk-devel",
            "custom_labelprefix_end": "openjdk.devel",
            "pretty_name": f"OpenJDK {java_version} development",
            "package_list": [f"java-{java_version}-openjdk-devel", "git-core", "maven"],
            "cmd": ["/usr/bin/jshell"],
            "from_image": f"{_build_tag_prefix(os_version)}/openjdk:{java_version}",
        }
    else:
        return {
            **common,
            "name": "openjdk",
            "pretty_name": f"OpenJDK {java_version} runtime",
            "package_list": [f"java-{java_version}-openjdk"],
        }


OPENJDK_CONTAINERS = (
    [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version, devel, 11), support_level=SupportLevel.L3
        )
        for os_version, devel in product(
            ALL_NONBASE_OS_VERSIONS,
            (True, False),
        )
    ]
    + [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=17),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(ALL_NONBASE_OS_VERSIONS, (True, False))
    ]
    + [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=20),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product((OsVersion.TUMBLEWEED,), (True, False))
    ]
)


@enum.unique
class PhpVariant(enum.Enum):
    cli = "PHP"
    apache = "PHP-Apache"
    fpm = "PHP-FPM"

    def __str__(self) -> str:
        return str(self.value)


def _php_entrypoint(variant: PhpVariant) -> str:
    cmd: str = {
        PhpVariant.cli: "php",
        PhpVariant.apache: "apache2-foreground",
        PhpVariant.fpm: "php-fpm",
    }[variant]
    return f"""#!/bin/sh
set -e

# first arg is `-f` or `--some-option`
if [ "${{1#-}}" != "$1" ]; then
	set -- {cmd} "$@"
fi

exec "$@"
"""


_EMPTY_SCRIPT = """#!/bin/sh
echo "This script is not required in this PHP container."
"""


def _create_php_bci(
    os_version: OsVersion, php_variant: PhpVariant, php_version: int
) -> LanguageStackContainer:
    common_end = """COPY docker-php-source docker-php-entrypoint docker-php-ext-configure docker-php-ext-enable docker-php-ext-install /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-php-*
"""

    if php_variant == PhpVariant.apache:
        extra_pkgs = [f"apache2-mod_php{php_version}"]
        extra_env = {
            "APACHE_CONFDIR": "/etc/apache2",
            "APACHE_ENVVARS": "/usr/sbin/envvars",
        }
        cmd = ["apache2-foreground"]
        custom_end = (
            common_end
            + """
STOPSIGNAL SIGWINCH

# create our own apache2-foreground from the systemd startup script
RUN sed 's|^exec $apache_bin|exec $apache_bin -DFOREGROUND|' /usr/sbin/start_apache2 > /usr/local/bin/apache2-foreground
RUN chmod +x /usr/local/bin/apache2-foreground

# apache fails to start without its log folder
RUN mkdir -p /var/log/apache2

WORKDIR /srv/www/htdocs

EXPOSE 80
"""
        )
    elif php_variant == PhpVariant.fpm:
        extra_pkgs = [f"php{php_version}-fpm"]
        extra_env = {}
        cmd = ["php-fpm"]
        custom_end = (
            common_end
            + """WORKDIR /srv/www/htdocs

"""
            + DOCKERFILE_RUN
            + r""" \
	cd /etc/php8/fpm/; \
        test -e php-fpm.d/www.conf.default && cp -p php-fpm.d/www.conf.default php-fpm.d/www.conf; \
        test -e php-fpm.conf.default && cp -p php-fpm.conf.default php-fpm.conf; \
	{ \
		echo '[global]'; \
		echo 'error_log = /proc/self/fd/2'; \
		echo; echo '; https://github.com/docker-library/php/pull/725#issuecomment-443540114'; echo 'log_limit = 8192'; \
		echo; \
		echo '[www]'; \
		echo '; if we send this to /proc/self/fd/1, it never appears'; \
		echo 'access.log = /proc/self/fd/2'; \
		echo; \
		echo 'clear_env = no'; \
		echo; \
		echo '; Ensure worker stdout and stderr are sent to the main error log.'; \
		echo 'catch_workers_output = yes'; \
		echo 'decorate_workers_output = no'; \
	} | tee php-fpm.d/docker.conf; \
	{ \
		echo '[global]'; \
		echo 'daemonize = no'; \
	} | tee php-fpm.d/zz-docker.conf

# Override stop signal to stop process gracefully
# https://github.com/php/php-src/blob/17baa87faddc2550def3ae7314236826bc1b1398/sapi/fpm/php-fpm.8.in#L163
STOPSIGNAL SIGQUIT

EXPOSE 9000
"""
        )
    else:
        extra_pkgs = (
            [] if os_version != OsVersion.TUMBLEWEED else [f"php{php_version}-readline"]
        )
        extra_env = {}
        cmd = ["php", "-a"]
        custom_end = common_end

    return LanguageStackContainer(
        name=str(php_variant).lower(),
        no_recommends=False,
        version=php_version,
        pretty_name=f"{str(php_variant)} {php_version}",
        package_name=f"{str(php_variant).lower()}{php_version}-image",
        os_version=os_version,
        package_list=[
            f"php{php_version}",
            f"php{php_version}-cli",
            "php-composer2",
            f"php{php_version}-curl",
            f"php{php_version}-zip",
            f"php{php_version}-zlib",
            f"php{php_version}-phar",
            f"php{php_version}-mbstring",
        ]
        + extra_pkgs,
        replacements_via_service=[
            Replacement("%%composer_version%%", package_name="php-composer2"),
            Replacement("%%php_version%%", package_name=f"php{php_version}"),
        ],
        cmd=cmd,
        entrypoint=["docker-php-entrypoint"],
        env={
            "PHP_VERSION": "%%php_version%%",
            "PHP_INI_DIR": f"/etc/php{php_version}/",
            "PHPIZE_DEPS": f"php{php_version}-devel awk make",
            "COMPOSER_VERSION": "%%composer_version%%",
            **extra_env,
        },
        extra_files={
            "docker-php-entrypoint": _php_entrypoint(php_variant),
            "docker-php-source": _EMPTY_SCRIPT,
            "docker-php-ext-configure": _EMPTY_SCRIPT,
            "docker-php-ext-enable": _EMPTY_SCRIPT,
            "docker-php-ext-install": f"""#!/bin/bash
{_BASH_SET}

extensions=()

for ext in $@; do
    [[ "$ext" =~ ^- ]] || extensions+=("php{php_version}-$ext")
done

zypper -n in ${{extensions[*]}}
""",
        },
        custom_end=custom_end,
    )


PHP_CONTAINERS = [
    _create_php_bci(os_version, variant, 8)
    for os_version, variant in product(
        (OsVersion.SP5, OsVersion.TUMBLEWEED),
        (PhpVariant.cli, PhpVariant.apache, PhpVariant.fpm),
    )
]


_389DS_FILES: Dict[str, str] = {}
_fname = "nsswitch.conf"
with open(os.path.join(os.path.dirname(__file__), "389-ds", _fname)) as nsswitch:
    _389DS_FILES[_fname] = nsswitch.read(-1)

THREE_EIGHT_NINE_DS_CONTAINERS = [
    ApplicationStackContainer(
        package_name="389-ds-container",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version_in_uid=False,
        name="389-ds",
        support_level=SupportLevel.L3,
        maintainer="william.brown@suse.com",
        pretty_name="389 Directory Server",
        package_list=["389-ds", "timezone", "openssl", "nss_synth"],
        cmd=["/usr/lib/dirsrv/dscontainer", "-r"],
        version="%%389ds_version%%",
        extra_files=_389DS_FILES,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%389ds_version%%",
                package_name="389-ds",
                parse_version="minor",
            )
        ],
        exposes_tcp=[3389, 3636],
        volumes=["/data"],
        custom_end=rf"""
COPY nsswitch.conf /etc/nsswitch.conf

{DOCKERFILE_RUN} mkdir -p /data/config; \
    mkdir -p /data/ssca; \
    mkdir -p /data/run; \
    mkdir -p /var/run/dirsrv; \
    ln -s /data/config /etc/dirsrv/slapd-localhost; \
    ln -s /data/ssca /etc/dirsrv/ssca; \
    ln -s /data/run /var/run/dirsrv

HEALTHCHECK --start-period=5m --timeout=5s --interval=5s --retries=2 \
    CMD /usr/lib/dirsrv/dscontainer -H
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

_DISABLE_GETTY_AT_TTY1_SERVICE = "systemctl disable getty@tty1.service"


def _get_os_container_package_names(os_version: OsVersion):
    if os_version == OsVersion.TUMBLEWEED:
        return ("openSUSE-release", "openSUSE-release-appliance-docker")

    return ("sles-release",)


INIT_CONTAINERS = [
    OsContainer(
        name="init",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Init",
        custom_description="Systemd environment for containers based on the SLE Base Container Image. This container is only supported with podman.",
        package_list=["systemd", "gzip"],
        cmd=["/usr/lib/systemd/systemd"],
        extra_labels={
            "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
        },
        package_name="init-image",
        custom_end=textwrap.dedent(
            f"""
            RUN mkdir -p /etc/systemd/system.conf.d/ && \\
                printf "[Manager]\\nLogColor=no" > \\
                    /etc/systemd/system.conf.d/01-sle-bci-nocolor.conf
            RUN {_DISABLE_GETTY_AT_TTY1_SERVICE}
            HEALTHCHECK --interval=5s --timeout=5s --retries=5 CMD ["/usr/bin/systemctl", "is-active", "multi-user.target"]
            """
        ),
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


with open(
    os.path.join(os.path.dirname(__file__), "mariadb", "entrypoint.sh")
) as entrypoint:
    _MARIAD_ENTRYPOINT = entrypoint.read(-1)

MARIADB_CONTAINERS = [
    ApplicationStackContainer(
        package_name="rmt-mariadb-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="rmt-mariadb",
        version="%%mariadb_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%mariadb_version%%",
                package_name="mariadb",
                parse_version="minor",
            )
        ],
        pretty_name="MariaDB Server for SUSE RMT",
        package_list=["mariadb", "mariadb-tools", "gawk", "timezone", "util-linux"],
        entrypoint=["docker-entrypoint.sh"],
        extra_files={
            "docker-entrypoint.sh": _MARIAD_ENTRYPOINT,
            "_constraints": generate_disk_size_constraints(11),
        },
        build_recipe_type=BuildType.DOCKER,
        cmd=["mariadbd"],
        volumes=["/var/lib/mysql"],
        exposes_tcp=[3306],
        custom_end=rf"""{DOCKERFILE_RUN} mkdir /docker-entrypoint-initdb.d

# docker-entrypoint from https://github.com/MariaDB/mariadb-docker.git
COPY docker-entrypoint.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod 755 /usr/local/bin/docker-entrypoint.sh
{DOCKERFILE_RUN} ln -s usr/local/bin/docker-entrypoint.sh / # backwards compat

{DOCKERFILE_RUN} sed -i 's#gosu mysql#su mysql -s /bin/bash -m#g' /usr/local/bin/docker-entrypoint.sh

# Ensure all logs goes to stdout
{DOCKERFILE_RUN} sed -i 's/^log/#log/g' /etc/my.cnf

# Disable binding to localhost only, doesn't make sense in a container
{DOCKERFILE_RUN} sed -i -e 's|^\(bind-address.*\)|#\1|g' /etc/my.cnf

{DOCKERFILE_RUN} mkdir /run/mysql
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


MARIADB_CLIENT_CONTAINERS = [
    ApplicationStackContainer(
        package_name="rmt-mariadb-client-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version_in_uid=False,
        name="rmt-mariadb-client",
        version="%%mariadb_version%%",
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%mariadb_version%%",
                package_name="mariadb-client",
                parse_version="minor",
            )
        ],
        pretty_name="MariaDB Client for SUSE RMT",
        package_list=["mariadb-client"],
        build_recipe_type=BuildType.DOCKER,
        cmd=["mariadb"],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


with open(
    os.path.join(os.path.dirname(__file__), "rmt", "entrypoint.sh")
) as entrypoint:
    _RMT_ENTRYPOINT = entrypoint.read(-1)

RMT_CONTAINERS = [
    ApplicationStackContainer(
        name="rmt-server",
        package_name="rmt-server-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name="SUSE RMT Server",
        build_recipe_type=BuildType.DOCKER,
        version="%%rmt_version%%",
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%rmt_version%%",
                package_name="rmt-server",
                parse_version="minor",
            )
        ],
        version_in_uid=False,
        package_list=["rmt-server", "catatonit"],
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        cmd=["/usr/share/rmt/bin/rails", "server", "-e", "production"],
        env={"RAILS_ENV": "production", "LANG": "en"},
        extra_files={"entrypoint.sh": _RMT_ENTRYPOINT},
        custom_end=f"""COPY entrypoint.sh /usr/local/bin/entrypoint.sh
{DOCKERFILE_RUN} chmod +x /usr/local/bin/entrypoint.sh
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


with open(
    os.path.join(os.path.dirname(__file__), "postgres", "entrypoint.sh")
) as entrypoint:
    _POSTGRES_ENTRYPOINT = entrypoint.read(-1)

with open(
    os.path.join(os.path.dirname(__file__), "postgres", "LICENSE")
) as license_file:
    _POSTGRES_LICENSE = license_file.read(-1)


_POSTGRES_MAJOR_VERSIONS = [15, 14, 13, 12]
POSTGRES_CONTAINERS = [
    ApplicationStackContainer(
        package_name=f"postgres-{ver}-image",
        os_version=os_version,
        is_latest=ver == _POSTGRES_MAJOR_VERSIONS[0],
        name="postgres",
        pretty_name=f"PostgreSQL {ver}",
        support_level=SupportLevel.ACC,
        package_list=[f"postgresql{ver}-server", "distribution-release"],
        version=ver,
        additional_versions=["%%pg_version%%"],
        entrypoint=["/usr/local/bin/docker-entrypoint.sh"],
        cmd=["postgres"],
        env={
            "LANG": "en_US.utf8",
            "PG_MAJOR": f"{ver}",
            "PG_VERSION": "%%pg_version%%",
            "PGDATA": "/var/lib/pgsql/data",
        },
        extra_files={
            "docker-entrypoint.sh": _POSTGRES_ENTRYPOINT,
            "LICENSE": _POSTGRES_LICENSE,
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(8),
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%pg_version%%",
                package_name=f"postgresql{ver}-server",
                parse_version="minor",
            )
        ],
        volumes=["$PGDATA"],
        exposes_tcp=[5432],
        custom_end=rf"""COPY docker-entrypoint.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/docker-entrypoint.sh; \
    sed -i -e 's/exec gosu postgres "/exec setpriv --reuid=postgres --regid=postgres --clear-groups -- "/g' /usr/local/bin/docker-entrypoint.sh; \
    mkdir /docker-entrypoint-initdb.d; \
    install -d -m 0700 -o postgres -g postgres $PGDATA; \
    sed -ri "s|^#?(listen_addresses)\s*=\s*\S+.*|\1 = '*'|" /usr/share/postgresql{ver}/postgresql.conf.sample

STOPSIGNAL SIGINT
HEALTHCHECK --interval=10s --start-period=10s --timeout=5s \
    CMD pg_isready -U ${{POSTGRES_USER:-postgres}} -h localhost -p 5432
""",
    )
    for ver, os_version in list(product([15, 14], ALL_NONBASE_OS_VERSIONS))
    + [(pg_ver, OsVersion.TUMBLEWEED) for pg_ver in (13, 12)]
]

PROMETHEUS_PACKAGE_NAME = "golang-github-prometheus-prometheus"
PROMETHEUS_CONTAINERS = [
    ApplicationStackContainer(
        package_name="prometheus-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="prometheus",
        pretty_name="Prometheus",
        package_list=[PROMETHEUS_PACKAGE_NAME],
        version="%%prometheus_version%%",
        version_in_uid=False,
        entrypoint=["/usr/bin/prometheus"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%prometheus_version%%",
                package_name=PROMETHEUS_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        volumes=["/var/lib/prometheus"],
        exposes_tcp=[9090],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

ALERTMANAGER_PACKAGE_NAME = "golang-github-prometheus-alertmanager"
ALERTMANAGER_CONTAINERS = [
    ApplicationStackContainer(
        package_name="alertmanager-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="alertmanager",
        pretty_name="Alertmanager",
        package_list=[ALERTMANAGER_PACKAGE_NAME],
        version="%%alertmanager_version%%",
        version_in_uid=False,
        entrypoint=["/usr/bin/prometheus-alertmanager"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%alertmanager_version%%",
                package_name=ALERTMANAGER_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        volumes=["/var/lib/prometheus/alertmanager"],
        exposes_tcp=[9093],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

BLACKBOX_EXPORTER_PACKAGE_NAME = "prometheus-blackbox_exporter"
BLACKBOX_EXPORTER_CONTAINERS = [
    ApplicationStackContainer(
        package_name="blackbox_exporter-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="blackbox_exporter",
        pretty_name="Blackbox Exporter",
        package_list=[BLACKBOX_EXPORTER_PACKAGE_NAME],
        version="%%blackbox_exporter_version%%",
        version_in_uid=False,
        entrypoint=["/usr/bin/blackbox_exporter"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%blackbox_exporter_version%%",
                package_name=BLACKBOX_EXPORTER_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        exposes_tcp=[9115],
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

GRAFANA_FILES = {}
for filename in {"run.sh", "LICENSE"}:
    with open(os.path.join(os.path.dirname(__file__), "grafana", filename)) as cursor:
        GRAFANA_FILES[filename] = cursor.read()

GRAFANA_PACKAGE_NAME = "grafana"
GRAFANA_CONTAINERS = [
    ApplicationStackContainer(
        package_name="grafana-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="grafana",
        pretty_name="Grafana",
        license="Apache-2.0",
        package_list=[GRAFANA_PACKAGE_NAME],
        version="%%grafana_version%%",
        version_in_uid=False,
        entrypoint=["/run.sh"],
        extra_files=GRAFANA_FILES,
        env={
            "GF_PATHS_DATA": "/var/lib/grafana",
            "GF_PATHS_HOME": "/usr/share/grafana",
            "GF_PATHS_LOGS": "/var/log/grafana",
            "GF_PATHS_PLUGINS": "/var/lib/grafana/plugins",
            "GF_PATHS_PROVISIONING": "/etc/grafana/provisioning",
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%grafana_version%%",
                package_name=GRAFANA_PACKAGE_NAME,
                parse_version="patch",
            )
        ],
        volumes=["/var/lib/grafana"],
        exposes_tcp=[3000],
        custom_end=f"""COPY run.sh /run.sh
{DOCKERFILE_RUN} chmod +x /run.sh
        """,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

_NGINX_FILES = {}
for filename in (
    "docker-entrypoint.sh",
    "LICENSE",
    "10-listen-on-ipv6-by-default.sh",
    "20-envsubst-on-templates.sh",
    "30-tune-worker-processes.sh",
    "index.html",
):
    with open(os.path.join(os.path.dirname(__file__), "nginx", filename)) as cursor:
        _NGINX_FILES[filename] = cursor.read(-1)


NGINX_CONTAINERS = [
    ApplicationStackContainer(
        package_name="rmt-nginx-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="rmt-nginx",
        pretty_name="NGINX for SUSE RMT",
        version="%%nginx_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%nginx_version%%",
                package_name="nginx",
                parse_version="minor",
            )
        ],
        package_list=["nginx", "distribution-release"],
        entrypoint=["/docker-entrypoint.sh"],
        cmd=["nginx", "-g", "daemon off;"],
        build_recipe_type=BuildType.DOCKER,
        extra_files=_NGINX_FILES,
        exposes_tcp=[80],
        custom_end=f"""{DOCKERFILE_RUN} mkdir /docker-entrypoint.d
COPY 10-listen-on-ipv6-by-default.sh /docker-entrypoint.d/
COPY 20-envsubst-on-templates.sh /docker-entrypoint.d/
COPY 30-tune-worker-processes.sh /docker-entrypoint.d/
COPY docker-entrypoint.sh /
{DOCKERFILE_RUN} chmod +x /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
{DOCKERFILE_RUN} chmod +x /docker-entrypoint.d/20-envsubst-on-templates.sh
{DOCKERFILE_RUN} chmod +x /docker-entrypoint.d/30-tune-worker-processes.sh
{DOCKERFILE_RUN} chmod +x /docker-entrypoint.sh

COPY index.html /srv/www/htdocs/

{DOCKERFILE_RUN} mkdir /var/log/nginx
{DOCKERFILE_RUN} chown nginx:nginx /var/log/nginx
{DOCKERFILE_RUN} ln -sf /dev/stdout /var/log/nginx/access.log
{DOCKERFILE_RUN} ln -sf /dev/stderr /var/log/nginx/error.log

STOPSIGNAL SIGQUIT
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


_RUST_GCC_PATH = "/usr/local/bin/gcc"

# release dates are coming from upstream - https://raw.githubusercontent.com/rust-lang/rust/master/RELEASES.md
# we expect a new release every 6 weeks, two releases are supported at any point in time
# and we give us one week of buffer, leading to release date + 6 + 6 + 1
_RUST_SUPPORT_ENDS = {
    "1.70": datetime.date(2023, 6, 8) + datetime.timedelta(weeks=6 + 6 + 1),
    "1.69": datetime.date(2023, 4, 20) + datetime.timedelta(weeks=6 + 6 + 1),
}

# ensure that the **latest** rust version is the last one!
_RUST_VERSIONS = ["1.69", "1.70"]

assert (
    len(_RUST_VERSIONS) == 2
), "Only two versions of rust must be supported at the same time"

RUST_CONTAINERS = [
    LanguageStackContainer(
        name="rust",
        stability_tag=(
            stability_tag := (
                "stable" if (rust_version == _RUST_VERSIONS[-1]) else "oldstable"
            )
        ),
        package_name=f"rust-{stability_tag}-image",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=(
            rust_version == _RUST_VERSIONS[-1]
            and os_version in CAN_BE_LATEST_OS_VERSION
        ),
        supported_until=_RUST_SUPPORT_ENDS.get(rust_version, None),
        pretty_name=f"Rust {rust_version}",
        package_list=[
            f"rust{rust_version}",
            f"cargo{rust_version}",
            "distribution-release",
        ],
        version=rust_version,
        env={
            "RUST_VERSION": "%%RUST_VERSION%%",
            "CARGO_VERSION": "%%CARGO_VERSION%%",
            "CC": _RUST_GCC_PATH,
        },
        extra_files={
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": generate_disk_size_constraints(6)
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%RUST_VERSION%%",
                package_name=f"rust{rust_version}",
            ),
            Replacement(
                regex_in_build_description="%%CARGO_VERSION%%",
                package_name=f"cargo{rust_version}",
            ),
        ],
        custom_end=f"""# workaround for gcc only existing as /usr/bin/gcc-N
RUN ln -sf $(ls /usr/bin/gcc-*|grep -P ".*gcc-[[:digit:]]+") {_RUST_GCC_PATH}
# smoke test that gcc works
RUN gcc --version
RUN ${{CC}} --version
""",
    )
    for rust_version, os_version in product(
        _RUST_VERSIONS,
        ALL_NONBASE_OS_VERSIONS,
    )
]

MICRO_CONTAINERS = [
    OsContainer(
        name="micro",
        os_version=os_version,
        support_level=SupportLevel.L3,
        package_name="micro-image",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name=f"{os_version.pretty_os_version_no_dash} Micro",
        custom_description="A micro environment for containers based on the SLE Base Container Image.",
        from_image=None,
        build_recipe_type=BuildType.KIWI,
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "bash",
                "ca-certificates-mozilla-prebuilt",
                # ca-certificates-mozilla-prebuilt requires /bin/cp, which is otherwise not resolved…
                "coreutils",
            )
            + (() if os_version == OsVersion.TUMBLEWEED else ("skelcd-EULA-bci",))
            + _get_os_container_package_names(os_version)
        ],
        # intentionally empty
        config_sh_script="""
""",
    )
    for os_version in ALL_BASE_OS_VERSIONS
]


def _get_minimal_kwargs(os_version: OsVersion):
    package_list = [
        Package(name, pkg_type=PackageType.DELETE)
        for name in ("grep", "diffutils", "info", "fillup", "libzio1")
    ]
    package_list += [
        Package(name, pkg_type=PackageType.BOOTSTRAP)
        for name in _get_os_container_package_names(os_version)
    ]
    if os_version == OsVersion.TUMBLEWEED:
        package_list.append(Package("rpm", pkg_type=PackageType.BOOTSTRAP))
    else:
        # in SLE15, rpm still depends on Perl.
        package_list += [
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in ("rpm-ndb", "perl-base")
        ]

    kwargs = {
        "from_image": f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        "pretty_name": f"{os_version.pretty_os_version_no_dash} Minimal",
        "package_list": package_list,
    }

    return kwargs


MINIMAL_CONTAINERS = [
    OsContainer(
        name="minimal",
        **_get_minimal_kwargs(os_version),
        support_level=SupportLevel.L3,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        package_name="minimal-image",
        os_version=os_version,
        build_recipe_type=BuildType.KIWI,
    )
    for os_version in ALL_BASE_OS_VERSIONS
]

BUSYBOX_CONTAINERS = [
    OsContainer(
        name="busybox",
        from_image=None,
        os_version=os_version,
        support_level=SupportLevel.L3,
        pretty_name=f"{os_version.pretty_os_version_no_dash} BusyBox",
        package_name="busybox-image",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        build_recipe_type=BuildType.KIWI,
        cmd=["/bin/sh"],
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in _get_os_container_package_names(os_version)
            + (
                "busybox",
                "busybox-links",
                "distribution-release",
                "ca-certificates-mozilla-prebuilt",
            )
        ],
        config_sh_script=textwrap.dedent(
            """
            sed -i 's|/bin/bash|/bin/sh|' /etc/passwd
            # Will be recreated by the next rpm(1) run as root user
            rm -v /usr/lib/sysimage/rpm/Index.db
        """
        ),
        config_sh_interpreter="/bin/sh",
    )
    for os_version in ALL_BASE_OS_VERSIONS
]

_PCP_FILES = {}
for filename in (
    "container-entrypoint",
    "pmproxy.conf.template",
    "10-host_mount.conf.template",
    "pmcd",
    "pmlogger",
    "README.md",
    "healthcheck",
):
    with open(os.path.join(os.path.dirname(__file__), "pcp", filename)) as cursor:
        _PCP_FILES[filename] = cursor.read(-1)

PCP_CONTAINERS = [
    ApplicationStackContainer(
        name="pcp",
        pretty_name="Performance Co-Pilot (pcp)",
        custom_description="Performance Co-Pilot (pcp) container image based on the SLE Base Container Image. This container is only supported with podman.",
        package_name="pcp-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-init:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        support_level=SupportLevel.L3,
        version="%%pcp_patch%%",
        version_in_uid=False,
        additional_versions=["%%pcp_minor%%", "%%pcp_major%%"],
        replacements_via_service=[
            Replacement(
                regex_in_build_description=f"%%pcp_{ver}%%",
                package_name="pcp",
                parse_version=ver,
            )
            for ver in ("major", "minor", "patch")
        ],
        license="(LGPL-2.1+ AND GPL-2.0+)",
        package_list=[
            "pcp",
            "hostname",
            "shadow",
            "gettext-runtime",
            "util-linux-systemd",
        ],
        entrypoint=["/usr/local/bin/container-entrypoint"],
        cmd=["/usr/lib/systemd/systemd"],
        build_recipe_type=BuildType.DOCKER,
        extra_files=_PCP_FILES,
        volumes=["/var/log/pcp/pmlogger"],
        exposes_tcp=[44321, 44322, 44323],
        custom_end=f"""
{DOCKERFILE_RUN} mkdir -p /usr/share/container-scripts/pcp; mkdir -p /etc/sysconfig
COPY container-entrypoint healthcheck /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/container-entrypoint /usr/local/bin/healthcheck
COPY pmproxy.conf.template 10-host_mount.conf.template /usr/share/container-scripts/pcp/
COPY pmcd pmlogger /etc/sysconfig/

# This can be removed after the pcp dependency on sysconfig is removed
{DOCKERFILE_RUN} systemctl disable wicked wickedd || :

HEALTHCHECK --start-period=30s --timeout=20s --interval=10s --retries=3 \
    CMD /usr/local/bin/healthcheck
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

REGISTRY_CONTAINERS = [
    ApplicationStackContainer(
        name="registry",
        pretty_name="OCI Container Registry (Distribution)",
        package_name="distribution-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%registry_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%registry_version%%",
                package_name="distribution-registry",
                parse_version="minor",
            )
        ],
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "apache2-utils",
                "ca-certificates-mozilla",
                "distribution-registry",
                "perl",
                "util-linux",
            )
        ],
        entrypoint=["/usr/bin/registry"],
        entrypoint_user="registry",
        cmd=["serve", "/etc/registry/config.yml"],
        build_recipe_type=BuildType.KIWI,
        volumes=["/var/lib/docker-registry"],
        exposes_tcp=[5000],
        support_level=SupportLevel.L3,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

HELM_CONTAINERS = [
    ApplicationStackContainer(
        name="helm",
        pretty_name="Kubernetes Package Manager",
        package_name="helm-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%helm_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%helm_version%%",
                package_name="helm",
                parse_version="minor",
            )
        ],
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "ca-certificates-mozilla",
                "helm",
            )
        ],
        entrypoint=["/usr/bin/helm"],
        cmd=["help"],
        build_recipe_type=BuildType.KIWI,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]

ALL_CONTAINER_IMAGE_NAMES: Dict[str, BaseContainerImage] = {
    f"{bci.uid}-{bci.os_version.pretty_print.lower()}": bci
    for bci in (
        *PYTHON_3_6_CONTAINERS,
        PYTHON_3_10_SP4,
        *PYTHON_3_11_CONTAINERS,
        *PYTHON_TW_CONTAINERS,
        *THREE_EIGHT_NINE_DS_CONTAINERS,
        *NGINX_CONTAINERS,
        *PCP_CONTAINERS,
        *REGISTRY_CONTAINERS,
        *HELM_CONTAINERS,
        *RMT_CONTAINERS,
        *RUST_CONTAINERS,
        *GOLANG_IMAGES,
        *RUBY_CONTAINERS,
        *NODE_CONTAINERS,
        *OPENJDK_CONTAINERS,
        *PHP_CONTAINERS,
        *INIT_CONTAINERS,
        *MARIADB_CONTAINERS,
        *MARIADB_CLIENT_CONTAINERS,
        *POSTGRES_CONTAINERS,
        *PROMETHEUS_CONTAINERS,
        *ALERTMANAGER_CONTAINERS,
        *BLACKBOX_EXPORTER_CONTAINERS,
        *GRAFANA_CONTAINERS,
        *MINIMAL_CONTAINERS,
        *MICRO_CONTAINERS,
        *BUSYBOX_CONTAINERS,
    )
}

SORTED_CONTAINER_IMAGE_NAMES = sorted(
    ALL_CONTAINER_IMAGE_NAMES,
    key=lambda bci: str(ALL_CONTAINER_IMAGE_NAMES[bci].os_version),
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
