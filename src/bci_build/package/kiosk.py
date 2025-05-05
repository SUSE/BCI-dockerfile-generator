from bci_build.container_attributes import Arch
from bci_build.registry import SUSERegistry

KIOSK_EXCLUSIVE_ARCH = [Arch.X86_64, Arch.AARCH64]


class KioskRegistry(SUSERegistry):
    """Registry for Kiosk containers."""

    @staticmethod
    def registry_prefix(*, is_application: bool) -> str:
        if not is_application:
            raise RuntimeError("Kiosk containers must be Application Containers")
        return "suse/kiosk"
