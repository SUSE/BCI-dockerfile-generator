"""Registry classes for container images."""

import dataclasses
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Registry(ABC):
    """Abstract Base Class for defining Registry specific content."""

    _: dataclasses.KW_ONLY
    """The base hostname for this registry instance"""
    registry: str
    """The vendor that is put into the ``org.opencontainers.image.vendor`` label"""
    vendor: str

    @abstractmethod
    def url(self, container) -> str:
        pass

    @abstractmethod
    def registry_prefix(self, *, is_application) -> str:
        pass


class ApplicationCollectionRegistry(Registry):
    """Registry for the Rancher Application Collection Distribution Platform."""

    def __init__(self):
        super().__init__(registry="dp.apps.rancher.io", vendor="SUSE LLC")

    def url(self, container) -> str:
        return f"https://apps.rancher.io/applications/{container.name}"

    def registry_prefix(self, *, is_application) -> str:
        return "containers"


class SUSERegistry(Registry):
    """Registry for the SUSE Registry."""

    def __init__(self):
        super().__init__(registry="registry.suse.com", vendor="SUSE LLC")

    def url(self, container) -> str:
        if container.os_version.is_ltss:
            return "https://www.suse.com/products/long-term-service-pack-support/"
        return "https://www.suse.com/products/base-container-images/"

    def registry_prefix(self, *, is_application) -> str:
        return "suse" if is_application else "bci"


class openSUSERegistry(Registry):
    """Registry for the openSUSE registry."""

    def __init__(self):
        super().__init__(registry="registry.opensuse.org", vendor="openSUSE Project")

    def url(self, container) -> str:
        return "https://www.opensuse.org"

    def registry_prefix(self, *, is_application) -> str:
        return "opensuse" if is_application else "opensuse/bci"


def get_registry(container) -> Registry:
    """Return the appropriate registry for the container."""
    if container.os_version.is_tumbleweed:
        return openSUSERegistry()
    return SUSERegistry()
