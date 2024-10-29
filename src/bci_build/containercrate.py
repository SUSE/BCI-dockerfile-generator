"""Crate to handle multibuild containers in the generator."""


class ContainerCrate:
    """ContainerCrate is combining multiple container build flavors.

    This provides package-central functions like generating _service and
    _multibuild files.
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
