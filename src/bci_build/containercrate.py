"""Crate to handle multibuild containers in the generator."""

import xml.etree.ElementTree as ET
from xml.dom import minidom

from bci_build.service import Service


class ContainerCrate:
    """ContainerCrate combines container build flavors into a single OBS multibuild

    The class provides functions like generating _service and
    _multibuild files for all containers in the crate.
    """

    def __init__(self, containers: list):
        """Assign the crate for every container."""
        self._all_build_flavors: dict[tuple, set] = {}
        for container in containers:
            if container.build_flavor:
                self._all_build_flavors.setdefault(
                    (container.os_version, container.package_name), set()
                ).add(container.build_flavor)

        for container in containers:
            if container.crate is not None:
                raise ValueError("Container is already part of a ContainerCrate")
            container.crate = self

    def all_build_flavors(self, container) -> list[str]:
        """Return all build flavors for this container in the crate"""
        return sorted(
            self._all_build_flavors.get(
                (container.os_version, container.package_name), [""]
            )
        )

    def default_dockerfile(self, container) -> str:
        buildrelease: str = ""
        if container.build_release:
            buildrelease = f"\n#!BuildVersion: workaround-for-an-obs-bug\n#!BuildRelease: {container.build_release}"
        """Return a default Dockerfile to disable build on default flavor."""
        return f"""#!ExclusiveArch: do-not-build
#!ForceMultiVersion{buildrelease}

# For this container we only build the Dockerfile.$flavor builds.
"""

    def multibuild(self, container) -> str:
        """Return the _multibuild file string to write for this ContainerCrate."""
        flavors: str = "\n".join(
            " " * 4 + f"<package>{pkg}</package>"
            for pkg in self.all_build_flavors(container)
        )
        return f"<multibuild>\n{flavors}\n</multibuild>"

    def service(self, container) -> str:
        """Return the _service file string to write for this ContainerCrate."""
        from bci_build.package import ALL_CONTAINER_IMAGE_NAMES

        root = ET.Element("services")
        root.append(
            Service(name=f"{container.build_recipe_type}_label_helper").as_xml_element()
        )
        root.append(Service(name="kiwi_metainfo_helper").as_xml_element())
        all_bcis = list(ALL_CONTAINER_IMAGE_NAMES.values())
        all_bcis.sort(key=lambda bci: bci.uid)
        for c in filter(
            lambda bci: bci.crate == self and bci.os_version == container.os_version,
            all_bcis,
        ):
            for r in c.replacements_via_service:
                rtree = r.to_service(f"Dockerfile.{c.build_flavor}").as_xml_element()
                root.append(rtree)

        return minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(
            indent="  "
        )
