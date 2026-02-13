from typing import Literal

from bci_build.container_attributes import Arch
from bci_build.container_attributes import PackageType
from bci_build.os_version import OsVersion
from bci_build.package import OsContainer
from bci_build.package import Package
from bci_build.package import _RELEASE_PLACEHOLDER
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.package.thirdparty import ThirdPartyPackage
from bci_build.package.thirdparty import ThirdPartyRepo
from bci_build.package.thirdparty import ARCH_FILENAME_MAP
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion
from bci_build.container_attributes import SupportLevel
from jinja2 import Template
from bci_build.container_attributes import BuildType
from bci_build.package import DOCKERFILE_RUN
from pathlib import Path
from bci_build.repomdparser import RpmPackage

# NVIDIA_REPO_KEY_URL = {
#     OsVersion.SP7: "https://download.nvidia.com/suse/sle15sp7/repodata/repomd.xml.key",
#     OsVersion.SL16_0: "https://download.nvidia.com/suse/sle16/repodata/repomd.xml.key",
# }

# NVIDIA_REPO_BASEURL = {
#     # OsVersion.SP7: "https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/",
#     OsVersion.SP7: "https://download.nvidia.com/suse/sle15sp7/",
#     OsVersion.SL16_0: "https://download.nvidia.com/suse/sle16/",
# }

NVIDIA_REPOS = {
    OsVersion.SP7: [
        ThirdPartyRepo(
            name="nvidia",
            url="https://download.nvidia.com/suse/sle15sp7/",
            key_url="https://download.nvidia.com/suse/sle15sp7/repodata/repomd.xml.key"
        ),
    ],
    OsVersion.SL16_0: [
        ThirdPartyRepo(
            name="nvidia",
            url="https://download.nvidia.com/suse/sle16/",
            key_url="https://download.nvidia.com/suse/sle16/repodata/repomd.xml.key"
        ),
    ],
}



# NVIDIA_REPOS = {
#     OsVersion.SP7: [
#         ThirdPartyRepo(
#             name="cuda-sles15-x86_64",
#             url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/",
#             key_url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/D42D0685.pub",
#         ),
#         ThirdPartyRepo(
#             name="cuda-sles15-sbsa",
#             url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/sbsa/",
#             key_url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/sbsa/D42D0685.pub"
#         ),
#     ],
#     OsVersion.SL16_0: [
#         # there are no CUDA repos for SLE 16 yet
#         ThirdPartyRepo(
#             name="nvidia",
#             url="https://download.nvidia.com/suse/sle16/",
#             key_url="https://download.nvidia.com/suse/sle16/repodata/repomd.xml.key"
#         ),
#     ],
# }

CUSTOM_END_TEMPLATE = Template(
    """RUN mkdir -p /tmp/

{%- for pkg in packages %}
#!RemoteAssetUrl: {{ pkg.url }} sha256:{{ pkg.checksum }}
COPY {{ pkg.filename }} /tmp/
{%- endfor %}

{% for repo in image.third_party_repos %}
COPY {{ repo.repo_filename }} /etc/zypp/repos.d/{{ repo.repo_filename }}
COPY {{ repo.key_filename }} /tmp/{{ repo.key_filename }}
RUN rpm --import /tmp/{{ repo.key_filename }}
RUN rpm --root /target --import /tmp/{{ repo.key_filename }}
{% endfor %}

{% for arch in image.exclusive_arch %}
{%- with pkgs=get_target_packages_for_arch(arch) %}
{{ DOCKERFILE_RUN }} if [ "$(uname -m)" = "{{ arch }}" ]; then \\
        zypper -n --gpg-auto-import-keys --installroot /target install \\
            --capability \\
            --no-recommends \\
            --auto-agree-with-licenses \\
        {%- for pkg in pkgs %}
            /tmp/{{ pkg.filename }}{% if loop.last %};{% endif %} \\
        {%- endfor %}
    fi
{%- endwith %}
{%- endfor %}

FROM nvidia-driver-builder AS open-driver-builder

{%- for arch in image.exclusive_arch %}
{%- with pkgs=get_open_packages_for_arch(arch) %}
{{ DOCKERFILE_RUN }} if [ "$(uname -m)" = "{{ arch }}" ]; then \\
        zypper -n --gpg-auto-import-keys install \\
            --capability \\
            --no-recommends \\
            --auto-agree-with-licenses \\
            "nvidia-open-driver-G06-signed-kmp = {{ image.driver_version }}" \\
            nvidia-open-driver-G06-signed-kmp-default \\
        {%- for pkg in pkgs %}
            /tmp/{{ pkg.filename }}{% if loop.last %};{% endif %} \\
        {%- endfor %}
    fi
{%- endwith %}
{%- endfor %}

{{ DOCKERFILE_RUN }} cp -rfx /lib/modules/*/updates /opt/open
{{ DOCKERFILE_RUN }} mkdir /opt/lib && cp -rfx /lib/firmware /opt/lib/firmware

FROM nvidia-driver-builder AS closed-driver-builder

{%- for arch in image.exclusive_arch %}
{%- with pkgs=get_closed_packages_for_arch(arch) %}
{{ DOCKERFILE_RUN }} if [ "$(uname -m)" = "{{ arch }}" ]; then \\
        zypper -n --gpg-auto-import-keys install \\
            --capability \\
            --no-recommends \\
            --auto-agree-with-licenses \\
        {%- for pkg in pkgs %}
            /tmp/{{ pkg.filename }}{% if loop.last %};{% endif %} \\
        {%- endfor %}
    fi
{%- endwith %}
{%- endfor %}

{{ DOCKERFILE_RUN }} cp -rfx /lib/modules/*/updates /opt/proprietary

FROM nvidia-driver-builder AS builder

COPY --from=open-driver-builder /opt/lib /target/opt/lib
COPY --from=open-driver-builder /opt/open /target/opt/open
COPY --from=closed-driver-builder /opt/proprietary /target/opt/proprietary
"""
)

CUSTOM_END = rf"""
COPY extract-vmlinux /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/extract-vmlinux

COPY nvidia-driver /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/nvidia-driver
# ensure the variable is set
RUN sed -i '/DRIVER_ARCH=.*TARGETARCH/i TARGETARCH=$(uname -m)' /usr/local/bin/nvidia-driver

{DOCKERFILE_RUN} mkdir /licenses
COPY NGC-DL-CONTAINER-LICENSE /licenses

{DOCKERFILE_RUN} mkdir /drivers
COPY README.md /drivers

WORKDIR /drivers

ENTRYPOINT ["nvidia-driver", "load"]
"""

class NvidiaDriverBCI(ThirdPartyRepoMixin, OsContainer):
    def __init__(self, driver_version: str, open_drivers_package_list: list[ThirdPartyPackage], closed_drivers_package_list: list[ThirdPartyPackage], **kwargs):
        self.driver_version = driver_version
        self.open_drivers_package_list = open_drivers_package_list
        self.closed_drivers_package_list = closed_drivers_package_list

        third_party_package_list = kwargs.pop("third_party_package_list", [])

        super().__init__(
            third_party_package_list=(
                self.open_drivers_package_list +
                self.closed_drivers_package_list +
                third_party_package_list
            ),
            **kwargs
        )

        if self.is_latest:
            raise RuntimeError(
                "NVIDIA explicitly requires the driver version in the tag"
            )

        self.custom_end = CUSTOM_END

        nvidia_dir = Path(__file__).parent / self.name

        self.extra_files.update({
            "NGC-DL-CONTAINER-LICENSE": (nvidia_dir / "NGC-DL-CONTAINER-LICENSE").read_bytes(),
            "README.md": (nvidia_dir / "vGPU-README.md").read_bytes(),
            "extract-vmlinux": (nvidia_dir / "extract-vmlinux").read_bytes(),
            "nvidia-driver": (nvidia_dir / "nvidia-driver").read_bytes(),
            # "_constraints": generate_disk_size_constraints(8),
        })

    @property
    def build_tags(self) -> list[str]:
        return [
            f"{self.registry_prefix}/{self.name}:{self.image_ref_name}",
            f"{self.registry_prefix}/{self.name}:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}",
        ]

    @property
    def image_ref_name(self) -> str:
        # should match 580.126.09-sles15.7
        return f"{self.driver_version}-sles%OS_VERSION_ID_SP%"

    @property
    def build_name(self) -> str | None:
        return f"bci-{self.name}-%OS_VERSION_ID_SP%"

    @property
    def reference(self) -> str:
        return f"{self.registry}/{self.registry_prefix}/{self.name}:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}"

    @property
    def pretty_reference(self) -> str:
        return f"{self.registry}/{self.registry_prefix}/{self.name}:{self.image_ref_name}"

    @property
    def dockerfile_from_line(self) -> str:
        return f"FROM {self.dockerfile_from_target_ref} AS target\nFROM {self._from_image} AS nvidia-driver-builder"

    def prepare_template(self) -> None:
        """Prepare the custom template used in the build_stage_custom_end."""
        assert self.build_recipe_type == BuildType.DOCKER, (
            f"Build type '{self.build_recipe_type}' is not supported for Third Party images"
        )
        assert len(self.third_party_package_list) > 0, (
            "The `third_party_package_list` is empty"
        )

        pkgs = self.fetch_rpm_packages()

        # NVIDIA drivers are built on GA kernel
        for name in ["kernel-default", "kernel-default-devel"]:
            for arch in self.exclusive_arch:
                pkgs.append(
                    RpmPackage(
                        name=name,
                        arch=str(arch),
                        evr=("", "6.4.0", "150700.51.1"),
                        filename=f"{name}-6.4.0-150700.51.1.{arch}.rpm",
                        url=f"https://api.opensuse.org/public/build/SUSE:SLE-15-SP7:GA/pool/{arch}/kernel-default/{name}-6.4.0-150700.51.1.{arch}.rpm"
                    )
                )

        for name in ["kernel-devel", "kernel-macros"]:
            pkgs.append(
                RpmPackage(
                    name=name,
                    arch="noarch",
                    evr=("", "6.4.0", "150700.51.1"),
                    filename=f"{name}-6.4.0-150700.51.1.noarch.rpm",
                    url=f"https://api.opensuse.org/public/build/SUSE:SLE-15-SP7:GA/pool/x86_64/kernel-source/{name}-6.4.0-150700.51.1.noarch.rpm"
                )
            )

        assert not self.build_stage_custom_end, (
            "Can't use `build_stage_custom_end` for ThirdPartyRepoMixin."
        )

        open_packages = [p.name for p in self.open_drivers_package_list]
        closed_packages = [p.name for p in self.closed_drivers_package_list]
        target_packages = open_packages + closed_packages
        # ["nvidia-persistenced", "nvidia-compute-G06", "nvidia-compute-utils-G06", "libOpenCL1", "libnvidia-gpucomp"]

        self.build_stage_custom_end = CUSTOM_END_TEMPLATE.render(
            image=self,
            packages=pkgs,
            DOCKERFILE_RUN=DOCKERFILE_RUN,
            get_open_packages_for_arch=lambda arch: [
                pkg for pkg in pkgs if pkg.name not in closed_packages and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
            get_closed_packages_for_arch=lambda arch: [
                pkg for pkg in pkgs if pkg.name not in open_packages and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
            get_target_packages_for_arch=lambda arch: [
                pkg for pkg in pkgs if pkg.name not in target_packages and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
        )

        super(OsContainer, self).prepare_template()


_NVIDIA_DRIVER_VERSIONS_T = Literal["580.126.09"]
_NVIDIA_DRIVER_VERSIONS: list[_NVIDIA_DRIVER_VERSIONS_T] = ["580.126.09"]

NVIDIA_CONTAINERS: list[NvidiaDriverBCI] = []

for os_version in (OsVersion.SL16_0, OsVersion.SP7,):
    for ver in _NVIDIA_DRIVER_VERSIONS:
        NVIDIA_CONTAINERS.append(
            NvidiaDriverBCI(
                os_version=os_version,
                driver_version=ver,
                name="nvidia-driver",
                pretty_name="NVIDIA Driver",
                is_latest=False,
                from_image=generate_from_image_tag(os_version, "bci-base"),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                package_name=f"nvidia-driver-{ver}",
                package_list=[
                    # needed by kernel GA
                    Package("gcc", PackageType.BOOTSTRAP),
                    Package("libelf-devel", PackageType.BOOTSTRAP),
                    Package("dwarves", PackageType.BOOTSTRAP),
                    Package("elfutils", PackageType.BOOTSTRAP),
                    Package("zstd", PackageType.BOOTSTRAP),
                    # needed by nvidia-driver and nvidia-persistenced
                    Package("mokutil", PackageType.BOOTSTRAP),
                    Package("make", PackageType.BOOTSTRAP),
                    Package("pciutils", PackageType.BOOTSTRAP),
                    Package("perl-Bootloader", PackageType.BOOTSTRAP),
                    Package("systemd", PackageType.BOOTSTRAP),

                    # Package("kernel-default", PackageType.BOOTSTRAP),
                    # Package("kernel-default-devel", PackageType.BOOTSTRAP),
                    # Package("kernel-devel", PackageType.BOOTSTRAP),
                    # Package("kernel-macros", PackageType.BOOTSTRAP),

                    # required by nvidia-driver script
                    Package("awk", PackageType.IMAGE),
                    Package("coreutils", PackageType.IMAGE),
                    Package("findutils", PackageType.IMAGE),
                    Package("grep", PackageType.IMAGE),
                    Package("jq", PackageType.IMAGE),
                    Package("kmod", PackageType.IMAGE),
                    Package("rpm", PackageType.IMAGE),
                    Package("sed", PackageType.IMAGE),
                    Package("util-linux", PackageType.IMAGE),

  # dbus-1 kbd libapparmor1 libdbus-1-3 libexpat1 libip4tc2 libkmod2 liblz4-1 libnvidia-cfg libseccomp2 libsystemd0 nvidia-persistenced pam-config pkg-config systemd systemd-default-settings
  # systemd-default-settings-branding-SLE systemd-presets-branding-SLE systemd-presets-common-SUSE update-alternatives

                ],
                support_level=SupportLevel.UNSUPPORTED,
                # exclusive_arch=[Arch.X86_64],
                exclusive_arch=[Arch.X86_64, Arch.AARCH64],
                third_party_repos=NVIDIA_REPOS[os_version],
                # third_party_repo_url=NVIDIA_REPO_BASEURL[os_version],
                # third_party_repo_key_url=NVIDIA_REPO_KEY_URL[os_version],
                # third_party_repo_key_file=NVIDIA_REPO_KEY_FILE[os_version],
                # third_party_repo_key_file="",
                open_drivers_package_list=[
                    # ThirdPartyPackage("nvidia-open-driver-G06-kmp-default", version=ver),
                    # ThirdPartyPackage("nvidia-open-driver-G06-signed-kmp-default", version=ver),
                    ThirdPartyPackage("nvidia-open-driver-G06-signed-kmp-meta", version=ver),
                ],
                closed_drivers_package_list=[
                    ThirdPartyPackage("nvidia-driver-G06-kmp-default", version=ver),
                    ThirdPartyPackage("nvidia-driver-G06-kmp-meta", version=ver),
                ],
                third_party_package_list=[
                    ThirdPartyPackage("libOpenCL1"),
                    ThirdPartyPackage("libnvidia-gpucomp", version=ver),
                    ThirdPartyPackage("nvidia-common-G06", version=ver),
                    ThirdPartyPackage("nvidia-compute-G06", version=ver),
                    ThirdPartyPackage("nvidia-compute-utils-G06", version=ver),
                    ThirdPartyPackage("nvidia-modprobe", version=ver),
                    ThirdPartyPackage("nvidia-persistenced", version=ver),
                    ThirdPartyPackage("nvidia-userspace-meta-G06", version=ver),
                ],
                entrypoint=["nvidia-driver", "load"],
                env={
                    "DRIVER_VERSION": ver,
                    "DRIVER_TYPE": "passthrough",
                    "DRIVER_BRANCH": ver.split(".")[0],
                    "VGPU_LICENSE_SERVER_TYPE": "NLS",
                    "DISABLE_VGPU_VERSION_CHECK": "true",
                    "NVIDIA_VISIBLE_DEVICES": "void",
                    "KERNEL_VERSION": "latest",
                },
            )
        )
