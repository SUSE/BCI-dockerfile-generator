#!/usr/bin/env python3
from __future__ import annotations

import abc
import asyncio
import datetime
import enum
import os
from dataclasses import dataclass
from dataclasses import field
from itertools import product
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import overload
from typing import Union

import aiofiles
from bci_build.templates import DOCKERFILE_TEMPLATE
from bci_build.templates import KIWI_TEMPLATE
from bci_build.templates import SERVICE_TEMPLATE
from bci_build.util import write_to_file


_BASH_SET = "set -euo pipefail"

#: a ``RUN`` command with a common set of bash flags applied to prevent errors
#: from not being noticed
DOCKERFILE_RUN = f"RUN {_BASH_SET};"


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


#: Operating system versions that have the label ``com.suse.release-stage`` set
#: to ``released``.
RELEASED_OS_VERSIONS = [OsVersion.SP3, OsVersion.SP4, OsVersion.TUMBLEWEED]

ALL_OS_VERSIONS = [OsVersion.SP3, OsVersion.SP4, OsVersion.TUMBLEWEED]

CAN_BE_LATEST_OS_VERSION = [OsVersion.SP4, OsVersion.TUMBLEWEED]


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
    """Class storing the properties of the Base Container Images that differ
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
    label_prefix="com.suse",
    distribution_base_name="SLE",
    build_tag_prefix=_build_tag_prefix(OsVersion.SP4),
    application_container_build_tag_prefix="suse",
)


@dataclass
class BaseContainerImage(abc.ABC):
    """Base class for all Base Container Images."""

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
    #: ``suse/sle15:15.$SP`` when an empty string is used.
    #: When from image is ``None``, then this image will not be based on
    #: **anything**, i.e. the ``FROM`` line is missing in the ``Dockerfile``.
    from_image: Optional[str] = ""

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

    _image_properties: ImageProperties = field(default=_SLE_IMAGE_PROPS)

    def __post_init__(self) -> None:
        if not self.package_list:
            raise ValueError(f"No packages were added to {self.pretty_name}.")
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
        return "15.4" if self.os_version == OsVersion.SP4 else None

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
# SPDX-FileCopyrightText: (c) {datetime.datetime.now().date().strftime("%Y")} SUSE LLC

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
        for (pkg_list, pkg_type) in zip(
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
            f"{self.pretty_name} based on the "
            f"{self._image_properties.distribution_base_name} Base Container Image."
        )

    @property
    def title(self) -> str:
        """The image title that is inserted into the ``org.opencontainers.image.title``
        label.

        It is generated from :py:attr:`BaseContainerImage.pretty_name` as
        follows: ``"{distribution_base_name} BCI {self.pretty_name} Container
        Image"``, where ``distribution_base_name`` is taken from
        :py:attr:`~ImageProperties.distribution_base_name`.

        """
        return f"{self._image_properties.distribution_base_name} BCI {self.pretty_name} Container Image"

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
            tasks.append(
                asyncio.ensure_future(write_file_to_dest(changes_file_name, ""))
            )
            files.append(changes_file_name)

        for fname, contents in self.extra_files.items():
            files.append(fname)
            tasks.append(asyncio.ensure_future(write_file_to_dest(fname, contents)))

        await asyncio.gather(*tasks)

        return files


@dataclass
class LanguageStackContainer(BaseContainerImage):
    #: the primary version of the language or application inside this container
    version: Union[str, int] = ""

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
    def build_tags(self) -> List[str]:
        tags = []
        for name in [self.name] + self.additional_names:
            tags += (
                [f"{self._registry_prefix}/{name}:{self.version_label}"]
                + ([f"{self._registry_prefix}/{name}:latest"] if self.is_latest else [])
                + [f"{self._registry_prefix}/{name}:{self.version_label}-%RELEASE%"]
                + [
                    f"{self._registry_prefix}/{name}:{ver}"
                    for ver in self.additional_versions
                ]
            )
        return tags

    @property
    def reference(self) -> str:
        return f"{self.registry}/{self._registry_prefix}/{self.name}:{self.version_label}-%RELEASE%"


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
        return f"{self._image_properties.distribution_base_name} {self.pretty_name} Container Image"


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
        return f"{self.registry}/bci/bci-{self.name}:{self.version_label}"


def _generate_disk_size_constraints(size_gb: int) -> str:
    return f"""<constraints>
  <hardware>
    <disk>
      <size unit="G">{size_gb}</size>
    </disk>
  </hardware>
</constraints>
"""


def _get_python_kwargs(
    py3_ver: Literal["3.6", "3.8", "3.9", "3.10"], os_version: OsVersion
):
    is_system_py: bool = py3_ver == (
        "3.6" if os_version != OsVersion.TUMBLEWEED else "3.8"
    )
    py3_ver_nodots = py3_ver.replace(".", "")

    py3 = (
        "python3"
        if is_system_py and os_version != OsVersion.TUMBLEWEED
        else "python" + py3_ver_nodots
    )
    py3_ver_replacement = f"%%py{py3_ver_nodots}_ver%%"
    pip3 = f"{py3}-pip"
    pip3_replacement = "%%pip_ver%%"
    kwargs = {
        "name": "python",
        "pretty_name": f"Python {py3_ver}",
        "custom_description": f"Python {py3_ver} development environment based on the SLE Base Container Image.",
        "version": py3_ver,
        "additional_versions": ["3"],
        "env": {"PYTHON_VERSION": py3_ver_replacement, "PIP_VERSION": pip3_replacement},
        "package_list": [py3, pip3, "curl", "git-core"]
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

        # in SLE 15 SP3 python39-pip does not provide pip & pip3
        if os_version == OsVersion.SP3:
            kwargs[
                "config_sh_script"
            ] = rf"""ln -s /usr/bin/pip{py3_ver} /usr/local/bin/pip3; \
    ln -s /usr/bin/pip{py3_ver} /usr/local/bin/pip; \
    {symlink_py_and_pydoc}
    """
        else:
            kwargs["config_sh_script"] = symlink_py_and_pydoc

    return kwargs


PYTHON_3_6_CONTAINERS = (
    LanguageStackContainer(
        **_get_python_kwargs("3.6", os_version),
        package_name=package_name,
        support_level=SupportLevel.L3,
    )
    for (os_version, package_name) in (
        (OsVersion.SP3, "python-3.6"),
        (OsVersion.SP4, "python-3.6-image"),
    )
)

PYTHON_3_8_TW = LanguageStackContainer(
    package_name="python-3.8-image",
    **_get_python_kwargs(
        "3.8",
        OsVersion.TUMBLEWEED,
    ),
)
PYTHON_3_9_SP3 = LanguageStackContainer(
    package_name="python-3.9",
    support_level=SupportLevel.L3,
    is_latest=False,
    **_get_python_kwargs("3.9", OsVersion.SP3),
)
PYTHON_3_9_TW = LanguageStackContainer(
    package_name="python-3.9-image",
    **_get_python_kwargs("3.9", OsVersion.TUMBLEWEED),
)

PYTHON_3_10_SP4 = LanguageStackContainer(
    package_name="python-3.10-image",
    support_level=SupportLevel.L3,
    is_latest=True,
    **_get_python_kwargs("3.10", OsVersion.SP4),
)
PYTHON_3_10_TW = LanguageStackContainer(
    package_name="python-3.10-image",
    is_latest=True,
    **_get_python_kwargs(
        "3.10",
        os_version=OsVersion.TUMBLEWEED,
    ),
)


def _get_ruby_kwargs(ruby_version: Literal["2.5", "3.1"], os_version: OsVersion):
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
        # as we only ship one ruby version, we want to make sure that binaries belonging
        # to our gems get installed as `bin` and not as `bin.ruby$ruby_version`
        "config_sh_script": "sed -i 's/--format-executable/--no-format-executable/' /etc/gemrc",
    }


RUBY_CONTAINERS = [
    LanguageStackContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP3),
    ),
    LanguageStackContainer(
        **_get_ruby_kwargs("2.5", OsVersion.SP4),
        support_level=SupportLevel.L3,
    ),
    LanguageStackContainer(**_get_ruby_kwargs("3.1", OsVersion.TUMBLEWEED)),
]


_GO_VER_T = Literal["1.18", "1.19"]
_GOLANG_VERSIONS: List[_GO_VER_T] = ["1.18", "1.19"]


def _get_golang_kwargs(ver: _GO_VER_T, os_version: OsVersion):
    golang_version_regex = "%%golang_version%%"
    go = f"go{ver}"
    return {
        "os_version": os_version,
        "package_name": f"golang-{ver}"
        + ("-image" if os_version != OsVersion.SP3 else ""),
        "custom_description": f"Golang {ver} development environment based on the SLE Base Container Image.",
        "name": "golang",
        "pretty_name": f"Golang {ver}",
        "is_latest": (
            (ver == _GOLANG_VERSIONS[-1]) and (os_version in CAN_BE_LATEST_OS_VERSION)
        ),
        "version": ver,
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
        "package_list": [
            Package(
                name=name,
                pkg_type=PackageType.BOOTSTRAP
                if os_version == 3
                else PackageType.IMAGE,
            )
            for name in (go, "distribution-release", "make", "git-core")
        ],
        "extra_files": {
            # the go binaries are huge and will ftbfs on workers with a root partition with 4GB
            "_constraints": _generate_disk_size_constraints(8)
        },
    }


GOLANG_IMAGES = [
    LanguageStackContainer(
        **_get_golang_kwargs(ver, os_version), support_level=SupportLevel.L3
    )
    for ver, os_version in product(_GOLANG_VERSIONS, ALL_OS_VERSIONS)
]


def _get_node_kwargs(ver: Literal[14, 16, 18, 19], os_version: OsVersion):
    return {
        "name": "nodejs",
        "os_version": os_version,
        "is_latest": (ver == 16 and os_version == OsVersion.SP4)
        or (ver == 19 and os_version == OsVersion.TUMBLEWEED),
        "package_name": f"nodejs-{ver}"
        + ("-image" if os_version != OsVersion.SP3 else ""),
        "custom_description": f"Node.js {ver} development environment based on the SLE Base Container Image.",
        "additional_names": ["node"],
        "version": str(ver),
        "pretty_name": f"Node.js {ver}",
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
        **_get_node_kwargs(ver, os_version), support_level=SupportLevel.L3
    )
    for ver, os_version in list(product((14, 16), (OsVersion.SP3, OsVersion.SP4)))
    + [(18, OsVersion.TUMBLEWEED), (19, OsVersion.TUMBLEWEED)]
]


def _get_openjdk_kwargs(
    os_version: OsVersion, devel: bool, java_version: Literal[11, 13, 15, 17]
):
    JAVA_ENV = {
        "JAVA_BINDIR": "/usr/lib64/jvm/java/bin",
        "JAVA_HOME": "/usr/lib64/jvm/java",
        "JAVA_ROOT": "/usr/lib64/jvm/java",
        "JAVA_VERSION": f"{java_version}",
    }

    if os_version == OsVersion.TUMBLEWEED:
        is_latest = java_version == 17
    else:
        is_latest = java_version == 11 and os_version in CAN_BE_LATEST_OS_VERSION

    comon = {
        "env": JAVA_ENV,
        "version": java_version,
        "os_version": os_version,
        "is_latest": is_latest,
        "package_name": f"openjdk-{java_version}"
        + ("-devel" if devel else "")
        + ("" if os_version == OsVersion.SP3 else "-image"),
        "extra_files": {
            # prevent ftbfs on workers with a root partition with 4GB
            "_constraints": _generate_disk_size_constraints(6)
        },
    }

    if devel:
        return {
            **comon,
            "name": "openjdk-devel",
            "custom_labelprefix_end": "openjdk.devel",
            "pretty_name": f"OpenJDK {java_version} Development",
            "custom_description": f"Java {java_version} Development environment based on the SLE Base Container Image.",
            "package_list": [f"java-{java_version}-openjdk-devel", "git-core", "maven"],
            "cmd": ["/usr/bin/jshell"],
            "from_image": f"{_build_tag_prefix(os_version)}/openjdk:{java_version}",
        }
    else:
        return {
            **comon,
            "name": "openjdk",
            "pretty_name": f"OpenJDK {java_version} Runtime",
            "custom_description": f"Java {java_version} runtime based on the SLE Base Container Image.",
            "package_list": [f"java-{java_version}-openjdk"],
        }


OPENJDK_CONTAINERS = (
    [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version, devel, 11), support_level=SupportLevel.L3
        )
        for os_version, devel in product(
            (OsVersion.SP3, OsVersion.SP4, OsVersion.TUMBLEWEED), (True, False)
        )
    ]
    + [
        LanguageStackContainer(
            **_get_openjdk_kwargs(os_version=os_version, devel=devel, java_version=17),
            support_level=SupportLevel.L3,
        )
        for os_version, devel in product(
            (OsVersion.SP4, OsVersion.TUMBLEWEED), (True, False)
        )
    ]
    + [
        LanguageStackContainer(
            **_get_openjdk_kwargs(
                os_version=OsVersion.TUMBLEWEED, devel=devel, java_version=java_version
            )
        )
        for devel, java_version in product((True, False), (13, 15))
    ]
)


_389DS_FILES: Dict[str, str] = {}
_fname = "nsswitch.conf"
with open(os.path.join(os.path.dirname(__file__), "389-ds", _fname)) as nsswitch:
    _389DS_FILES[_fname] = nsswitch.read(-1)

THREE_EIGHT_NINE_DS_CONTAINERS = [
    ApplicationStackContainer(
        package_name="389-ds-container",
        os_version=os_version,
        is_latest=True,
        version_in_uid=False,
        name="389-ds",
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
    for os_version in (OsVersion.SP4, OsVersion.TUMBLEWEED)
]

_DISABLE_GETTY_AT_TTY1_SERVICE = "systemctl disable getty@tty1.service"


def init_container_kwargs(os_version: OsVersion):
    kwargs = {
        "name": "init",
        "os_version": os_version,
        "support_level": SupportLevel.L3,
        "custom_description": "Systemd environment for containers based on the SLE Base Container Image. This container is not supported when using container runtime other than podman.",
        "is_latest": os_version in CAN_BE_LATEST_OS_VERSION,
        "pretty_name": "%OS_VERSION_NO_DASH% Init",
        "package_list": ["systemd", "gzip"],
        "cmd": ["/usr/lib/systemd/systemd"],
        "extra_labels": {
            "usage": "This container should only be used to build containers for daemons. Add your packages and enable services using systemctl."
        },
    }
    if os_version == OsVersion.SP3:
        kwargs["package_name"] = "init"
        kwargs["config_sh_script"] = _DISABLE_GETTY_AT_TTY1_SERVICE
    else:
        kwargs["package_name"] = "init-image"
        kwargs[
            "custom_end"
        ] = f"""RUN {_DISABLE_GETTY_AT_TTY1_SERVICE}
HEALTHCHECK --interval=5s --timeout=5s --retries=5 \
    CMD ["/usr/bin/systemctl", "is-active", "multi-user.target"]
"""
    return kwargs


INIT_CONTAINERS = [
    OsContainer(**init_container_kwargs(os_version))
    for os_version in (OsVersion.SP3, OsVersion.SP4, OsVersion.TUMBLEWEED)
]


with open(
    os.path.join(os.path.dirname(__file__), "mariadb", "entrypoint.sh")
) as entrypoint:
    _MARIAD_ENTRYPOINT = entrypoint.read(-1)

MARIADB_CONTAINERS = [
    ApplicationStackContainer(
        package_name=(
            "rmt-mariadb" if os_version == OsVersion.SP3 else "rmt-mariadb-image"
        ),
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
        pretty_name="MariaDB Server",
        custom_description="MariaDB server for RMT, based on the SLE Base Container Image.",
        package_list=["mariadb", "mariadb-tools", "gawk", "timezone", "util-linux"],
        entrypoint=["docker-entrypoint.sh"],
        extra_files={"docker-entrypoint.sh": _MARIAD_ENTRYPOINT},
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
    for os_version in ALL_OS_VERSIONS
]


MARIADB_CLIENT_CONTAINERS = [
    ApplicationStackContainer(
        package_name=(
            "rmt-mariadb-client"
            if os_version == OsVersion.SP3
            else "rmt-mariadb-client-image"
        ),
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
        pretty_name="MariaDB Client",
        custom_description="MariaDB client for RMT, based on the SLE Base Container Image.",
        package_list=["mariadb-client"],
        build_recipe_type=BuildType.DOCKER,
        cmd=["mariadb"],
    )
    for os_version in ALL_OS_VERSIONS
]


with open(
    os.path.join(os.path.dirname(__file__), "rmt", "entrypoint.sh")
) as entrypoint:
    _RMT_ENTRYPOINT = entrypoint.read(-1)

RMT_CONTAINERS = [
    ApplicationStackContainer(
        name="rmt-server",
        package_name="rmt-server" + ("" if os_version == OsVersion.SP3 else "-image"),
        os_version=os_version,
        custom_description="SUSE RMT Server based on the SLE Base Container Image.",
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name="RMT Server",
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
    for os_version in ALL_OS_VERSIONS
]


with open(
    os.path.join(os.path.dirname(__file__), "postgres", "entrypoint.sh")
) as entrypoint:
    _POSTGRES_ENTRYPOINT = entrypoint.read(-1)

with open(
    os.path.join(os.path.dirname(__file__), "postgres", "LICENSE")
) as license_file:
    _POSTGRES_LICENSE = license_file.read(-1)


_POSTGRES_MAJOR_VERSIONS = [14, 13, 12, 10]
POSTGRES_CONTAINERS = [
    ApplicationStackContainer(
        package_name=f"postgres-{ver}-image",
        os_version=os_version,
        is_latest=ver == 14,
        name="postgres",
        pretty_name=f"PostgreSQL {ver}",
        package_list=[f"postgresql{ver}-server", "distribution-release"],
        version=ver,
        additional_versions=["%%pg_version%%"],
        entrypoint=["docker-entrypoint.sh"],
        cmd=["postgres"],
        env={
            "LANG": "en_US.utf8",
            "PG_MAJOR": f"{ver}",
            "PG_VERSION": "%%pg_version%%",
            "PGDATA": "/var/lib/postgresql/data",
        },
        extra_files={
            "docker-entrypoint.sh": _POSTGRES_ENTRYPOINT,
            "LICENSE": _POSTGRES_LICENSE,
        },
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%pg_version%%",
                package_name=f"postgresql{ver}-server",
                parse_version="minor",
            )
        ],
        volumes=["/var/lib/postgresql/data"],
        exposes_tcp=[5432],
        custom_end=rf"""COPY docker-entrypoint.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/docker-entrypoint.sh; \
    ln -s su /usr/bin/gosu; \
    mkdir /docker-entrypoint-initdb.d; \
    sed -ri "s|^#?(listen_addresses)\s*=\s*\S+.*|\1 = '*'|" /usr/share/postgresql{ver}/postgresql.conf.sample

STOPSIGNAL SIGINT
""",
    )
    for ver, os_version in product(
        _POSTGRES_MAJOR_VERSIONS, [OsVersion.SP4, OsVersion.TUMBLEWEED]
    )
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
    for os_version in (OsVersion.SP4, OsVersion.TUMBLEWEED)
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
    for os_version in (OsVersion.SP4, OsVersion.TUMBLEWEED)
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
    for os_version in (OsVersion.SP4, OsVersion.TUMBLEWEED)
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
    for os_version in (OsVersion.SP4, OsVersion.TUMBLEWEED)
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
        package_name="rmt-nginx" if os_version == OsVersion.SP3 else "rmt-nginx-image",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        name="rmt-nginx",
        pretty_name="RMT Nginx",
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
    for os_version in (OsVersion.SP3, OsVersion.SP4, OsVersion.TUMBLEWEED)
]


_RUST_GCC_PATH = "/usr/local/bin/gcc"

# ensure that the **latest** rust version is the last one!
_RUST_VERSIONS = ["1.62", "1.63", "1.64"]

RUST_CONTAINERS = [
    LanguageStackContainer(
        name="rust",
        package_name=f"rust-{rust_version}-image",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=(
            rust_version == _RUST_VERSIONS[-1]
            and os_version in CAN_BE_LATEST_OS_VERSION
        ),
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
            "_constraints": _generate_disk_size_constraints(6)
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
        (OsVersion.SP4, OsVersion.TUMBLEWEED),
    )
]

MICRO_CONTAINERS = [
    OsContainer(
        name="micro",
        os_version=os_version,
        support_level=SupportLevel.L3,
        package_name=package_name,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        pretty_name="%OS_VERSION_NO_DASH% Micro",
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
                "distribution-release",
            )
            + (() if os_version == OsVersion.TUMBLEWEED else ("skelcd-EULA-bci",))
        ],
        # intentionally empty
        config_sh_script="""
""",
    )
    for os_version, package_name in (
        (OsVersion.SP3, "micro"),
        (OsVersion.SP4, "micro-image"),
        (OsVersion.TUMBLEWEED, "micro-image"),
    )
]

MINIMAL_CONTAINERS = [
    OsContainer(
        name="minimal",
        from_image=f"{_build_tag_prefix(os_version)}/bci-micro:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        support_level=SupportLevel.L3,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        package_name=package_name,
        build_recipe_type=BuildType.KIWI,
        pretty_name="%OS_VERSION_NO_DASH% Minimal",
        custom_description="A minimal environment for containers based on the SLE Base Container Image.",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "rpm" if os_version == OsVersion.TUMBLEWEED else "rpm-ndb",
                "perl-base",
                "distribution-release",
            )
        ]
        + [
            Package(name, pkg_type=PackageType.DELETE)
            for name in ("grep", "diffutils", "info", "fillup", "libzio1")
        ],
    )
    for os_version, package_name in (
        (OsVersion.SP3, "minimal"),
        (OsVersion.SP4, "minimal-image"),
        (OsVersion.TUMBLEWEED, "minimal-image"),
    )
]

BUSYBOX_CONTAINERS = [
    OsContainer(
        name="busybox",
        from_image=None,
        os_version=os_version,
        support_level=SupportLevel.L3,
        pretty_name="%OS_VERSION_NO_DASH% Busybox",
        package_name="busybox-image",
        is_latest=True,
        build_recipe_type=BuildType.KIWI,
        custom_description="Busybox based on the SLE Base Container Image.",
        cmd=["/bin/sh"],
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "busybox",
                "busybox-links",
                "distribution-release",
                "ca-certificates-mozilla-prebuilt",
            )
        ],
        config_sh_script="sed -i 's|/bin/bash|/bin/sh|' /etc/passwd",
        config_sh_interpreter="/bin/sh",
    )
    for os_version in (OsVersion.SP4, OsVersion.TUMBLEWEED)
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
        custom_description="Performance Co-Pilot (pcp) container image based on the SLE Base Container Image. This container image is not supported when using a container runtime other than podman.",
        package_name="pcp-image",
        from_image=f"{_build_tag_prefix(os_version)}/bci-init:{OsContainer.version_to_container_os_version(os_version)}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
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
{DOCKERFILE_RUN} systemctl disable wicked wickedd

HEALTHCHECK --start-period=30s --timeout=20s --interval=10s --retries=3 \
    CMD /usr/local/bin/healthcheck
""",
    )
    for os_version in ALL_OS_VERSIONS
]

REGISTRY_CONTAINERS = [
    ApplicationStackContainer(
        name="registry",
        pretty_name="OCI Container Registry using the OCI Image Specification (Distribution)",
        custom_description="Open Source Registry implementation using the OCI Distribution Specification",
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
    )
    for os_version in CAN_BE_LATEST_OS_VERSION
]

ALL_CONTAINER_IMAGE_NAMES: Dict[str, BaseContainerImage] = {
    f"{bci.uid}-{bci.os_version if bci.os_version == OsVersion.TUMBLEWEED else 'sp' + str(bci.os_version) }": bci
    for bci in (
        *PYTHON_3_6_CONTAINERS,
        PYTHON_3_8_TW,
        PYTHON_3_9_SP3,
        PYTHON_3_9_TW,
        PYTHON_3_10_SP4,
        PYTHON_3_10_TW,
        *THREE_EIGHT_NINE_DS_CONTAINERS,
        *NGINX_CONTAINERS,
        *PCP_CONTAINERS,
        *REGISTRY_CONTAINERS,
        *RMT_CONTAINERS,
        *RUST_CONTAINERS,
        *GOLANG_IMAGES,
        *RUBY_CONTAINERS,
        *NODE_CONTAINERS,
        *OPENJDK_CONTAINERS,
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
ALL_CONTAINER_IMAGE_NAMES.pop("golang-1.19-sp3")

SORTED_CONTAINER_IMAGE_NAMES = sorted(
    ALL_CONTAINER_IMAGE_NAMES,
    key=lambda bci: str(ALL_CONTAINER_IMAGE_NAMES[bci].os_version),
)

if __name__ == "__main__":
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
