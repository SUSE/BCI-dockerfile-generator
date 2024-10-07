"""Registry classes for container images."""

import dataclasses
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bci_build.osversion import OsVersion

if TYPE_CHECKING:
    from bci_build.package import BaseContainerImage


@dataclass(frozen=True, kw_only=True)
class Registry(ABC):
    """Abstract Base Class for defining Registry specific content."""

    _: dataclasses.KW_ONLY
    """The base hostname for this registry instance"""
    registry: str
    """The vendor that is put into the ``org.opencontainers.image.vendor`` label"""
    vendor: str

    @staticmethod
    @abstractmethod
    def url(container: "BaseContainerImage") -> str:
        """Generate the url for the given for the given container"""

    @staticmethod
    @abstractmethod
    def registry_prefix(*, is_application: bool) -> str:
        """Return the registry prefix (that is the path between the registries'
        TLD and the container name) for this registry.

        The flag ``is_application`` switches whether to return the registry
        prefix for application containers, which are generally receive a
        different registry prefix then all other container images.

        """


class ApplicationCollectionRegistry(Registry):
    """Registry for the Rancher Application Collection Distribution Platform."""

    def __init__(self):
        super().__init__(registry="dp.apps.rancher.io", vendor="SUSE LLC")

    @staticmethod
    def url(container: "BaseContainerImage") -> str:
        return f"https://apps.rancher.io/applications/{container.name}"

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        return "containers"


class SUSERegistry(Registry):
    """Registry for the SUSE Registry."""

    def __init__(self):
        super().__init__(registry="registry.suse.com", vendor="SUSE LLC")

    @staticmethod
    def url(container: "BaseContainerImage") -> str:
        if container.os_version.is_ltss:
            return "https://www.suse.com/products/long-term-service-pack-support/"
        return "https://www.suse.com/products/base-container-images/"

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        return "suse" if is_application else "bci"


class openSUSERegistry(Registry):
    """Registry for the openSUSE registry."""

    def __init__(self):
        super().__init__(registry="registry.opensuse.org", vendor="openSUSE Project")

    @staticmethod
    def url(container: "BaseContainerImage") -> str:
        return "https://www.opensuse.org"

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        return "opensuse" if is_application else "opensuse/bci"


def publish_registry(
    os_version: OsVersion, *, app_collection: bool = False
) -> Registry:
    """Return the appropriate registry for the operating system version."""
    if os_version.is_tumbleweed:
        return openSUSERegistry()
    if app_collection:
        return ApplicationCollectionRegistry()
    return SUSERegistry()
