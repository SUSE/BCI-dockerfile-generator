from typing import Literal

from bci_build.container_attributes import Arch
from bci_build.container_attributes import PackageType
from bci_build.os_version import OsVersion
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion
from bci_build.container_attributes import SupportLevel

NVIDIA_REPO_KEY_URL = ""

NVIDIA_REPO_KEY_FILE = """
"""

NVIDIA_REPO_BASEURL = {
    OsVersion.SP7: "https://download.nvidia.com/suse/sle15sp7/",
    OsVersion.SL16_0: "https://download.nvidia.com/suse/sle16/",
}

LICENSE = """
"""


class NvidiaGPUBCI(ThirdPartyRepoMixin, OsContainer):
    def __init__(
        self,
        kernel_version: str,
        driver_version: str,
        is_latest: bool = False,
        **kwargs,
    ):
        if is_latest:
            raise RuntimeError(
                "AMD GPU explicitly requires the kernel version in the tag"
            )

        self.kernel_version = kernel_version
        self.driver_version = driver_version

        super().__init__(**kwargs)

    @property
    def build_tags(self) -> list[str]:
        # the amd-gpu operator expects this tag format
        # sles-15.7-6.4.0-150700.53.19-default-7.0.3
        return [
            f"{self.name}:sles-%OS_VERSION_ID_SP%-{self.kernel_version}-default-{self.driver_version}"
        ]

    @property
    def build_name(self) -> str | None:
        return f"bci-{self.name}-%OS_VERSION_ID_SP%"


_NVIDIA_GPU_VERSIONS_T = Literal["580.126.09"]
_NVIDIA_GPU_VERSIONS: list[_NVIDIA_GPU_VERSIONS_T] = ["580.126.09"]

NVIDIA_GPU_CONTAINERS: list[NvidiaGPUBCI] = []

for os_version in (OsVersion.SL16_0, OsVersion.SP7,):
    for ver in _NVIDIA_GPU_VERSIONS:
        NVIDIA_GPU_CONTAINERS.append(
            NvidiaGPUBCI(
                os_version=os_version,
                kernel_version=(version_replacement := "%%kernel_version%%"),
                driver_version=ver,
                name="amdgpu-driver",
                pretty_name="AMD GPU Driver",
                is_latest=False,
                # from_image=generate_from_image_tag(os_version, "bci-base"),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                package_name=f"amd-gpu-{ver}",
                package_list=[
                    # # these are build requirements for amdgpu-dkms
                    # Package("autoconf", PackageType.BOOTSTRAP),
                    # Package("automake", PackageType.BOOTSTRAP),
                    # Package("bc", PackageType.BOOTSTRAP),
                    # Package("bison", PackageType.BOOTSTRAP),
                    # Package("flex", PackageType.BOOTSTRAP),
                    # Package("kernel-default", PackageType.BOOTSTRAP),
                    # Package("libzstd-devel", PackageType.BOOTSTRAP),
                    # Package("perl", PackageType.BOOTSTRAP),
                    # Package("python3", PackageType.BOOTSTRAP),
                    # Package("python3-setuptools", PackageType.BOOTSTRAP),
                    # Package("python3-wheel", PackageType.BOOTSTRAP),
                    # # this is a runtime requirement to load amdgpu-dkms
                    # Package("kmod", PackageType.IMAGE),

                    # ?
                    Package("awk", PackageType.BOOTSTRAP),
                    Package("curl", PackageType.BOOTSTRAP),
                    Package("kmod", PackageType.BOOTSTRAP),
                    Package("tar", PackageType.BOOTSTRAP),
                    Package("util-linux-systemd", PackageType.BOOTSTRAP),
                    # ?
                    Package("systemd", PackageType.IMAGE),
                    Package("dbus-1", PackageType.IMAGE),
                    Package("kbd", PackageType.IMAGE),
                    Package("libapparmor1", PackageType.IMAGE),
                    Package("libip4tc2", PackageType.IMAGE),
                    Package("libkmod2", PackageType.IMAGE),
                    Package("libseccomp2", PackageType.IMAGE),
                    Package("pam-config", PackageType.IMAGE),
                    Package("pkg-config", PackageType.IMAGE),
                    Package("systemd-default-settings", PackageType.IMAGE),
                    Package("libdbus-1-3", PackageType.IMAGE),
                    Package("libexpat1", PackageType.IMAGE),
                    Package("systemd-default-settings-branding-SLE", PackageType.IMAGE),
                    Package("systemd-presets-branding-SLE", PackageType.IMAGE),
                    Package("systemd-presets-common-SUSE", PackageType.IMAGE),
               ],
                support_level=SupportLevel.UNSUPPORTED,
                exclusive_arch=[Arch.X86_64],
                third_party_repo_url=NVIDIA_REPO_BASEURL[os_version],
                third_party_repo_key_url=NVIDIA_REPO_KEY_URL,
                third_party_repo_key_file=NVIDIA_REPO_KEY_FILE,
                third_party_package_list=[
                    # "nvidia-open-signed-kmp",
                    "nvidia-open-driver-G06-signed-kmp-meta",
                    "nvidia-driver-G06-kmp-default",
                    # "nvidia-gfx",
                    "nvidia-compute-G06",
                    "nvidia-persistenced",
                    "nvidia-compute-utils-G06",
                ],
                replacements_via_service=[
                    Replacement(
                        regex_in_build_description=version_replacement,
                        package_name="kernel-default",
                        parse_version=ParseVersion.RELEASE,
                    )
                ],
            )
        )
