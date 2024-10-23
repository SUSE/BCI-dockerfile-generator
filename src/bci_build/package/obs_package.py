"""This module contains the classes for the ObsPackage container, which bundles
together multiple base container images into a single package.

"""

import abc
import asyncio
import os.path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING
from typing import Coroutine
from typing import Sequence

from bci_build.container_attributes import BuildType
from bci_build.os_version import OsVersion
from bci_build.service import Service
from bci_build.util import write_to_file

if TYPE_CHECKING:
    from bci_build.package import BaseContainerImage


@dataclass(kw_only=True)
class ObsPackage(abc.ABC):
    """Abstract base class of the ObsPackage and the BaseContainerImage."""

    #: The name of the package in the Build Service
    package_name: str | None = None

    #: The OS version to which this package belongs
    os_version: OsVersion

    #: Define whether this container image is built using docker or kiwi.
    #: If not set, then the build type will default to docker from SP4 onwards.
    build_recipe_type: BuildType | None = None

    def __post_init__(self) -> None:
        if self.build_recipe_type is None:
            self.build_recipe_type = (
                BuildType.KIWI if self.os_version == OsVersion.SP3 else BuildType.DOCKER
            )

    @property
    @abc.abstractmethod
    def uid(self) -> str:
        """unique identifier of this package, either its name or ``$name-$tag_version``."""

    @property
    @abc.abstractmethod
    def services(self) -> tuple[Service, ...]:
        """The source services that are part of this package."""

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The title of this package."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """The description of this package."""

    @abc.abstractmethod
    async def write_files_to_folder(
        self, dest: str, *, with_service_file: bool = True
    ) -> list[str]:
        """Write all files belonging to this package into the directory
        ``dest``.

        If ``with_service_file`` is ``False``, then the :file:`_service` will
        not be written to ``dest``.

        """

    @property
    def _service_file_contents(self) -> str:
        root = ET.Element("services")
        for service in [
            Service(name=f"{self.build_recipe_type}_label_helper"),
            Service(name="kiwi_metainfo_helper"),
        ] + list(self.services):
            root.append(service.as_xml_element())

        tree = ET.ElementTree(root)
        ET.indent(tree)
        io = BytesIO()
        tree.write(io, encoding="utf-8")
        io.seek(0)
        return io.read().decode("utf-8")

    async def _write_service_file(self, dest: str) -> list[str]:
        await write_to_file(os.path.join(dest, "_service"), self._service_file_contents)
        return ["_service"]


@dataclass(kw_only=True)
class MultiBuildObsPackage(ObsPackage):
    """ObsPackage is a container for combining multiple container images with
    different build flavors into a single package.

    """

    bcis: list["BaseContainerImage"]

    #: Optional custom title of this package. If unset, then the title of the
    #: first bci is used.
    custom_title: str | None = None

    #: Optional custom description of this package. If unset, then the
    #: description of the first bci is used.
    custom_description: str | None = None

    @staticmethod
    def from_bcis(
        bcis: Sequence["BaseContainerImage"], package_name: str | None = None
    ) -> "MultiBuildObsPackage":
        pkg_names: set[str] = set()
        os_versions: set[OsVersion] = set()
        multibuild_flavors: list[str | None] = []

        for bci in bcis:
            if bci.package_name:
                pkg_names.add(bci.package_name)
            os_versions.add(bci.os_version)
            multibuild_flavors.append(bci.build_flavor)

        if len(pkg_names) != 1 and not package_name:
            raise ValueError(f"got a non unique package name: {pkg_names}")

        if len(os_versions) != 1:
            raise ValueError(f"got a non unique os_version: {os_versions}")

        if len(set(multibuild_flavors)) != len(multibuild_flavors):
            raise ValueError(
                f"The multibuild flavors are not unique: {multibuild_flavors}"
            )

        if not package_name:
            package_name = pkg_names.pop()

        return MultiBuildObsPackage(
            package_name=package_name, os_version=os_versions.pop(), bcis=list(bcis)
        )

    def __post_init__(self) -> None:
        super().__post_init__()

        # we only support Dockerfile based multibuild at the moment
        self.build_recipe_type = BuildType.DOCKER

        if not self.package_name:
            raise ValueError("A package name must be provided")

        for bci in self.bcis:
            if not bci.build_flavor:
                raise ValueError(f"Container {bci.name} has no build flavor defined")

            if bci.build_recipe_type != BuildType.DOCKER:
                raise ValueError(f"Container {bci.name} is not built from a Dockerfile")

    @property
    def uid(self) -> str:
        return self.package_name

    @property
    def services(self) -> tuple[Service, ...]:
        return tuple(service for bci in self.bcis for service in bci.services)

    async def write_files_to_folder(
        self, dest: str, *, with_service_file=True
    ) -> list[str]:
        async def write_file_to_dest(fname: str, contents: str) -> list[str]:
            await write_to_file(os.path.join(dest, fname), contents)
            return [fname]

        tasks: list[Coroutine[None, None, list[str]]] = []
        for bci in self.bcis:
            tasks.append(bci.write_files_to_folder(dest, with_service_file=False))

        tasks.append(write_file_to_dest("Dockerfile", self.default_dockerfile))
        tasks.append(write_file_to_dest("_multibuild", self.multibuild))
        if with_service_file:
            tasks.append(self._write_service_file(dest))

        return [f for file_list in await asyncio.gather(*tasks) for f in file_list]

    @property
    def title(self) -> str:
        return self.custom_title or self.bcis[0].title

    @property
    def description(self) -> str:
        return self.custom_description or self.bcis[0].description

    @property
    def default_dockerfile(self) -> str:
        """Return a default :file:`Dockerfile` to disable the build for the
        default flavor.

        """
        return """#!ExclusiveArch: do-not-build

# For this container we only build the Dockerfile.$flavor builds.
"""

    @property
    def multibuild(self) -> str:
        """Return the contents of the :file:`_multibuild` file for this
        package.

        """
        flavors: str = "\n".join(
            " " * 4 + f"<package>{pkg.build_flavor}</package>" for pkg in self.bcis
        )
        return f"<multibuild>\n{flavors}\n</multibuild>"
