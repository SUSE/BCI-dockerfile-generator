"""Registry classes for container images."""

from abc import ABC
from abc import abstractmethod


class RegistryABC(ABC):
    """Abstract Base Class for defining Registry specific content."""

    @abstractmethod
    def registry(self) -> str:
        pass

    @abstractmethod
    def url(self, container) -> str:
        pass

    @abstractmethod
    def vendor(self) -> str:
        pass


class ApplicationCollectionRegistry(RegistryABC):
    """Registry for the Rancher Application Collection Distribution Platform."""

    @property
    def registry(self) -> str:
        return "dp.apps.rancher.io"

    def url(self, container) -> str:
        return f"https://apps.rancher.io/applications/{container.name}"

    @property
    def vendor(self) -> str:
        return "SUSE LLC"


class SUSERegistry(RegistryABC):
    """Registry for the SUSE Registry."""

    @property
    def registry(self) -> str:
        return "registry.suse.com"

    def url(self, container) -> str:
        if container.os_version.is_ltss:
            return "https://www.suse.com/products/long-term-service-pack-support/"
        return "https://www.suse.com/products/base-container-images/"

    @property
    def vendor(self) -> str:
        return "SUSE LLC"


class openSUSERegistry(RegistryABC):
    """Registry for the openSUSE registry."""

    @property
    def registry(self) -> str:
        return "registry.opensuse.org"

    def url(self, container) -> str:
        return "https://www.opensuse.org"

    @property
    def vendor(self) -> str:
        return "openSUSE Project"


def get_registry(container) -> RegistryABC:
    """Return the appropriate registry for the container."""
    if container.os_version.is_tumbleweed:
        return openSUSERegistry()
    return SUSERegistry()
