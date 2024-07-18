"""Application Collection Containers that are generated with the BCI tooling"""

from dataclasses import dataclass

from bci_build.package import ApplicationStackContainer
from bci_build.package import Arch


@dataclass
class ApplicationCollectionContainer(ApplicationStackContainer):
    """Containers for the Rancher Application Collection Distribution Platform."""

    @property
    def _registry_prefix(self) -> str:
        if self.os_version.is_tumbleweed:
            return super()._registry_prefix
        return "containers"

    @property
    def registry(self) -> str:
        if self.os_version.is_tumbleweed:
            return super().registry
        return "dp.apps.rancher.io"

    @property
    def url(self) -> str:
        if self.os_version.is_tumbleweed:
            return super().url
        return f"https://apps.rancher.io/applications/{self.name}"

    @property
    def title(self) -> str:
        if self.os_version.is_tumbleweed:
            return super().title
        return self.pretty_name

    def __post_init__(self) -> None:
        super().__post_init__()
        # Limit Appcollection stuff to aarch64 and x86_64
        if not self.os_version.is_tumbleweed and not self.exclusive_arch:
            self.exclusive_arch = [Arch.AARCH64, Arch.X86_64]
