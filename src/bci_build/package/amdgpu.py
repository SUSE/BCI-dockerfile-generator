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

AMD_REPO_KEY_URL = "https://repo.radeon.com/rocm/rocm.gpg.key"

AMD_REPO_KEY_FILE = """-----BEGIN PGP PUBLIC KEY BLOCK-----

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
=4g5r
-----END PGP PUBLIC KEY BLOCK-----
"""

AMD_REPO_BASEURL = "https://repo.radeon.com/amdgpu/7.0.3/sle/15.7/main/x86_64/"

LICENSE = """Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


class AMDGPUBCI(ThirdPartyRepoMixin, OsContainer):
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


_AMD_GPU_VERSIONS_T = Literal["7.0.3"]
_AMD_GPU_VERSIONS: list[_AMD_GPU_VERSIONS_T] = ["7.0.3"]

AMD_GPU_CONTAINERS: list[AMDGPUBCI] = []

for os_version in (OsVersion.SP7,):
    for ver in _AMD_GPU_VERSIONS:
        AMD_GPU_CONTAINERS.append(
            AMDGPUBCI(
                os_version=os_version,
                kernel_version=(version_replacement := "%%kernel_version%%"),
                driver_version=ver,
                name="amdgpu-driver",
                pretty_name="AMD GPU Driver",
                is_latest=False,
                from_image=generate_from_image_tag(
                    os_version, "bci-sle15-kernel-module-devel", False
                ),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                package_name=f"amd-gpu-{ver}",
                package_list=[
                    # these are build requirements for amdgpu-dkms
                    Package("autoconf", PackageType.BOOTSTRAP),
                    Package("automake", PackageType.BOOTSTRAP),
                    Package("bc", PackageType.BOOTSTRAP),
                    Package("bison", PackageType.BOOTSTRAP),
                    Package("flex", PackageType.BOOTSTRAP),
                    Package("kernel-default", PackageType.BOOTSTRAP),
                    Package("libzstd-devel", PackageType.BOOTSTRAP),
                    Package("perl", PackageType.BOOTSTRAP),
                    Package("python3", PackageType.BOOTSTRAP),
                    Package("python3-setuptools", PackageType.BOOTSTRAP),
                    Package("python3-wheel", PackageType.BOOTSTRAP),
                    # this is a runtime requirement to load amdgpu-dkms
                    Package("kmod", PackageType.IMAGE),
                ],
                support_level=SupportLevel.UNSUPPORTED,
                exclusive_arch=[Arch.X86_64],
                third_party_repo_url=AMD_REPO_BASEURL,
                third_party_repo_key_url=AMD_REPO_KEY_URL,
                third_party_repo_key_file=AMD_REPO_KEY_FILE,
                third_party_package_list=[
                    "amdgpu-dkms",
                    "amdgpu-dkms-firmware",
                    "dkms",
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
