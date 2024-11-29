"""Crate to handle multibuild containers in the generator."""

import os

from bci_build.util import write_to_file


class ContainerCrateAssigner:
    """ContainerCrateAssigner is allocating ContainerCrates for a given list of containers."""

    def __init__(self, containers: list):
        """Assign the ContainerCrate for every container in the list."""
        all_build_flavors: dict[tuple, set] = {}
        all_containers: dict[tuple, list] = {}

        for container in containers:
            if container.build_flavor:
                all_build_flavors.setdefault(
                    (container.os_version, container.package_name), set()
                ).add(container.build_flavor)
                all_containers.setdefault(
                    (container.os_version, container.package_name), []
                ).append(container)

        for os_version, package_name in all_containers:
            crate = ContainerCrate(
                sorted(all_build_flavors.get((os_version, package_name), [])),
                all_containers[(os_version, package_name)],
            )
            for container in all_containers[(os_version, package_name)]:
                if container.crate is not None:
                    raise ValueError("Container is already part of a ContainerCrate")
                container.crate = crate


class ContainerCrate:
    """ContainerCrate represents a group of containers that share the same os_version/package_name and
    only differ by flavor.

    This provides package-central functions like generating _service and
    _multibuild files.
    """

    def __init__(self, all_build_flavors: list[str], all_containers: list):
        """Assign the crate for every container."""
        self._all_build_flavors = all_build_flavors
        self._all_containers = all_containers

    def all_build_flavors(self) -> list[str]:
        """Return all build flavors for this container in the crate"""
        return self._all_build_flavors

    def default_dockerfile(self, container) -> str:
        buildrelease: str = ""
        if container.build_release:
            buildrelease = f"\n#!BuildVersion: workaround-for-an-obs-bug\n#!BuildRelease: {container.build_release}"
        """Return a default Dockerfile to disable build on default flavor."""
        return f"""#!ExclusiveArch: do-not-build
#!ForceMultiVersion{buildrelease}

# For this container we only build the Dockerfile.$flavor builds.
"""

    def multibuild(self) -> str:
        """Return the _multibuild file string to write for this ContainerCrate."""
        flavors: str = "\n".join(
            " " * 4 + f"<package>{pkg}</package>" for pkg in self.all_build_flavors()
        )
        return f"<multibuild>\n{flavors}\n</multibuild>"

    def services(self) -> str:
        services = f"""<services>
  <service mode="buildtime" name="{self._all_containers[0].build_recipe_type}_label_helper"/>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
"""
        for container in self._all_containers:
            for replacement in container.replacements_via_service:
                services += (
                    "  "
                    + "\n  ".join(
                        str(
                            replacement.to_service(
                                f"Dockerfile.{container.build_flavor}"
                            )
                        ).splitlines()
                    )
                    + "\n"
                )
        services = services + "</services>"
        return services

    async def write_files_to_folder(self, dest: str, container) -> list[str]:
        """Write the files that this crate,container pair needs."""
        files = []

        fname = "Dockerfile"
        await write_to_file(
            os.path.join(dest, fname), self.default_dockerfile(container)
        )
        files.append(fname)

        fname = "_multibuild"
        await write_to_file(os.path.join(dest, fname), self.multibuild())
        files.append(fname)

        fname = "_service"
        await write_to_file(os.path.join(dest, fname), self.services())
        files.append(fname)
        return files
