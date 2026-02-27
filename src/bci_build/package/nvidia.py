"""
This module contains classes and functions related to updating and generating Dockerfiles for NVIDIA driver containers.

NVIDIA drivers are taken from CUDA repositories and use the GA kernel.
"""

import textwrap
from pathlib import Path

from jinja2 import Template

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import ReleaseStage
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import SET_BLKID_SCAN
from bci_build.package import _RELEASE_PLACEHOLDER
from bci_build.package import DevelopmentContainer
from bci_build.package import Package
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.thirdparty import ARCH_FILENAME_MAP
from bci_build.package.thirdparty import ThirdPartyPackage
from bci_build.package.thirdparty import ThirdPartyRepo
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.repomdparser import RpmPackage

NVIDIA_REPOS = {
    OsVersion.SP7: [
        ThirdPartyRepo(
            name="cuda-sles15-x86_64",
            arch=Arch.X86_64,
            url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/",
            key_url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/D42D0685.pub",
        ),
        ThirdPartyRepo(
            name="cuda-sles15-sbsa",
            arch=Arch.AARCH64,
            url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/sbsa/",
            key_url="https://developer.download.nvidia.com/compute/cuda/repos/sles15/sbsa/D42D0685.pub",
        ),
    ],
}

CUSTOM_END_TEMPLATE = Template(
    """RUN mkdir -p /tmp/

{%- for pkg in packages %}
#!RemoteAssetUrl: {{ pkg.url }}{% if not pkg.url.endswith(pkg.filename) %} {{ pkg.filename }}{% endif %}{% if pkg.checksum %} sha256:{{ pkg.checksum }}{% endif %}
COPY {{ pkg.filename }} /tmp/
{%- endfor %}

{% for repo in image.third_party_repos -%}
COPY {{ repo.name }}.repo /etc/zypp/repos.d/{{ repo.repo_filename }}
COPY {{ repo.name }}.gpg.key /tmp/{{ repo.key_filename }}
RUN rpm --import /tmp/{{ repo.key_filename }}
RUN rpm --root /target --import /tmp/{{ repo.key_filename }}
{% endfor -%}

FROM nvidia-driver-builder AS open-driver-builder

{%- for arch in image.exclusive_arch %}
{% with pkgs=get_open_packages_for_arch(arch) -%}
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

{{ DOCKERFILE_RUN }} dkms autoinstall -k $(ls -1 /lib/modules/)
{{ DOCKERFILE_RUN }} cp -rfx /lib/modules/*/updates /opt/open
{{ DOCKERFILE_RUN }} mkdir /opt/lib && cp -rfx /lib/firmware /opt/lib/firmware

FROM nvidia-driver-builder AS closed-driver-builder

{%- for arch in image.exclusive_arch %}
{% with pkgs=get_closed_packages_for_arch(arch) -%}
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

{{ DOCKERFILE_RUN }} dkms autoinstall -k $(ls -1 /lib/modules/)
{{ DOCKERFILE_RUN }} cp -rfx /lib/modules/*/updates /opt/proprietary

FROM nvidia-driver-builder AS builder

COPY --from=open-driver-builder /usr/share/nvidia-driver-assistant/supported-gpus/supported-gpus.json /target/usr/share/nvidia-driver-assistant/supported-gpus/supported-gpus.json
COPY --from=open-driver-builder /opt/lib /target/opt/lib
COPY --from=open-driver-builder /opt/open /target/opt/open
COPY --from=closed-driver-builder /opt/proprietary /target/opt/proprietary

{%- for arch in image.exclusive_arch %}
{% with pkgs=get_target_packages_for_arch(arch) -%}
{{ DOCKERFILE_RUN }} if [ "$(uname -m)" = "{{ arch }}" ]; then \\
        rpm --root /target -Uvh --nodeps \\
        {%- for pkg in pkgs %}
            /tmp/{{ pkg.filename }}{% if loop.last %};{% endif %} \\
        {%- endfor %}
    fi
{%- endwith %}
{%- endfor %}
"""
)


class NvidiaDriverBCI(ThirdPartyRepoMixin, DevelopmentContainer):
    def __init__(
        self,
        open_drivers_package_list: list[ThirdPartyPackage],
        closed_drivers_package_list: list[ThirdPartyPackage],
        **kwargs,
    ):
        self.open_drivers_package_list = open_drivers_package_list
        self.closed_drivers_package_list = closed_drivers_package_list

        third_party_package_list = kwargs.pop("third_party_package_list", [])

        super().__init__(
            third_party_package_list=(
                self.open_drivers_package_list
                + self.closed_drivers_package_list
                + third_party_package_list
            ),
            **kwargs,
        )

        if self.is_latest:
            raise RuntimeError(
                "NVIDIA explicitly requires the driver version in the tag"
            )

        self.custom_end = textwrap.dedent(f"""
            COPY extract-vmlinux /usr/local/bin/
            {DOCKERFILE_RUN} chmod +x /usr/local/bin/extract-vmlinux

            COPY nvidia-driver /usr/local/bin/
            {DOCKERFILE_RUN} chmod +x /usr/local/bin/nvidia-driver

            COPY nvidia-driver-selector.sh /usr/local/bin/
            {DOCKERFILE_RUN} chmod +x /usr/local/bin/nvidia-driver-selector.sh

            {DOCKERFILE_RUN} mkdir /licenses
            COPY NGC-DL-CONTAINER-LICENSE /licenses

            {DOCKERFILE_RUN} mkdir /drivers
            COPY vGPU-README.md /drivers/README.md

            WORKDIR /drivers

            ENTRYPOINT ["nvidia-driver", "load"]\n""") + (
            SET_BLKID_SCAN if os_version.is_sle15 else ""
        )

        nvidia_dir = Path(__file__).parent / self.name

        self.extra_files.update(
            {
                "NGC-DL-CONTAINER-LICENSE": (
                    nvidia_dir / "NGC-DL-CONTAINER-LICENSE"
                ).read_bytes(),
                "vGPU-README.md": (nvidia_dir / "vGPU-README.md").read_bytes(),
                "extract-vmlinux": (nvidia_dir / "extract-vmlinux").read_bytes(),
                "nvidia-driver": (nvidia_dir / "nvidia-driver").read_bytes(),
                "nvidia-driver-selector.sh": (
                    nvidia_dir / "nvidia-driver-selector.sh"
                ).read_bytes(),
                "_constraints": generate_disk_size_constraints(8),
            }
        )

    @property
    def release_stage(self) -> ReleaseStage:
        # TODO: Remove once the image is completed with all driver versions
        return ReleaseStage.BETA

    @property
    def registry_prefix(self):
        return "third-party"

    @property
    def build_tags(self) -> list[str]:
        return [
            f"{self.registry_prefix}/nvidia/driver:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}",
            f"{self.registry_prefix}/nvidia/driver:{self.image_ref_name}",
        ]

    @property
    def image_ref_name(self) -> str:
        # tag should match 580.126.09-sles15.7
        return f"{self.version}-sles%OS_VERSION_ID_SP%"

    @property
    def build_name(self) -> str | None:
        return f"{self.name}-{self.version}"

    @property
    def reference(self) -> str:
        return f"{self.registry}/{self.registry_prefix}/nvidia/driver:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}"

    @property
    def pretty_reference(self) -> str:
        return f"{self.registry}/{self.registry_prefix}/nvidia/driver:{self.image_ref_name}"

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
        assert not self.build_stage_custom_end, (
            "Can't use `build_stage_custom_end` for ThirdPartyRepoMixin."
        )

        pkgs = self.fetch_rpm_packages()

        kernel_packages = [
            ("kernel-default", "kernel-default", self.exclusive_arch),
            ("kernel-default-devel", "kernel-default", self.exclusive_arch),
            ("kernel-syms", "kernel-syms", self.exclusive_arch),
            ("kernel-devel", "kernel-source", self.exclusive_arch),
            ("kernel-macros", "kernel-source", self.exclusive_arch),
            # needed only for aarch64
            ("kernel-64kb-devel", "kernel-64kb", [Arch.AARCH64]),
        ]

        for name, pkg_name, exclusive_arch in kernel_packages:
            for arch in exclusive_arch:
                # NVIDIA drivers are built on GA kernel version
                filename_in_image = f"{name}-6.4.0-150700.51.1.{arch}.rpm"
                filename_in_repo = f"{name}-6.4.0-150700.51.1.{arch}.rpm"

                if pkg_name == "kernel-source":
                    filename_in_repo = f"{name}-6.4.0-150700.51.1.noarch.rpm"

                pkgs.append(
                    RpmPackage(
                        name=name,
                        arch=str(arch),
                        evr=("", "6.4.0", "150700.51.1"),
                        filename=filename_in_image,
                        url=f"https://api.opensuse.org/public/build/SUSE:SLE-15-SP7:GA/pool/{arch}/{pkg_name}/{filename_in_repo}",
                    )
                )

        open_packages = [p.name for p in self.open_drivers_package_list]
        closed_packages = [p.name for p in self.closed_drivers_package_list]
        ignore_in_target_packages = (
            open_packages + closed_packages + [pkg[0] for pkg in kernel_packages]
        )

        self.build_stage_custom_end = CUSTOM_END_TEMPLATE.render(
            image=self,
            packages=pkgs,
            DOCKERFILE_RUN=DOCKERFILE_RUN,
            get_open_packages_for_arch=lambda arch: [
                pkg
                for pkg in pkgs
                if pkg.name not in closed_packages
                and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
            get_closed_packages_for_arch=lambda arch: [
                pkg
                for pkg in pkgs
                if pkg.name not in open_packages and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
            get_target_packages_for_arch=lambda arch: [
                pkg
                for pkg in pkgs
                if pkg.name not in ignore_in_target_packages
                and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
        )

        super(DevelopmentContainer, self).prepare_template()


# We need to support all versions for GPU Operator Version v25.10.1
# https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html#gpu-operator-component-matrix
_NVIDIA_DRIVER_VERSIONS = [
    # TODO: Only 580 for now
    # "590.48.01",
    "580.126.16",
    "580.126.09",
    "580.105.08",
    "580.95.05",
    "580.82.07",
    # "575.57.08",
    # "570.211.01",
    # "570.195.03",
    # "550.163.01",
    # "535.288.01",
    # "535.274.02",
]

NVIDIA_CONTAINERS: list[NvidiaDriverBCI] = []

for os_version in (OsVersion.SP7,):
    for ver in _NVIDIA_DRIVER_VERSIONS:
        NVIDIA_CONTAINERS.append(
            NvidiaDriverBCI(
                os_version=os_version,
                version=ver,
                tag_version=ver,
                version_in_uid=True,
                use_build_flavor_in_tag=False,
                build_flavor=f"driver-{ver}",
                name="nvidia-driver",
                pretty_name="NVIDIA Driver",
                license="NVIDIA DEEP LEARNING CONTAINER LICENSE",
                is_latest=False,
                from_image=generate_from_image_tag(os_version, "bci-base"),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                package_list=[
                    # needed by kernel packages
                    Package("dwarves", PackageType.BOOTSTRAP),
                    Package("elfutils", PackageType.BOOTSTRAP),
                    Package("gcc", PackageType.BOOTSTRAP),
                    Package("libelf-devel", PackageType.BOOTSTRAP),
                    Package("pesign-obs-integration", PackageType.BOOTSTRAP),
                    Package("zstd", PackageType.BOOTSTRAP),
                    # needed by nvidia packages
                    Package("dracut", PackageType.BOOTSTRAP),
                    Package("gcc-c++", PackageType.BOOTSTRAP),
                    Package("make", PackageType.BOOTSTRAP),
                    Package("mokutil", PackageType.BOOTSTRAP),
                    Package("pciutils", PackageType.BOOTSTRAP),
                    Package("perl-Bootloader", PackageType.BOOTSTRAP),
                    Package("python3", PackageType.BOOTSTRAP),
                    Package("systemd", PackageType.BOOTSTRAP),
                    Package("xz", PackageType.BOOTSTRAP),
                    # needed by nvidia-driver script
                    Package("awk", PackageType.IMAGE),
                    Package("coreutils", PackageType.IMAGE),
                    Package("findutils", PackageType.IMAGE),
                    Package("grep", PackageType.IMAGE),
                    Package("jq", PackageType.IMAGE),
                    Package("kmod", PackageType.IMAGE),
                    Package("rpm", PackageType.IMAGE),
                    Package("sed", PackageType.IMAGE),
                    Package("util-linux", PackageType.IMAGE),
                    Package("util-linux-systemd", PackageType.IMAGE),
                ],
                support_level=SupportLevel.TECHPREVIEW,
                exclusive_arch=[Arch.X86_64, Arch.AARCH64],
                third_party_repos=NVIDIA_REPOS[os_version],
                open_drivers_package_list=[
                    ThirdPartyPackage("nvidia-open-driver-G06", version=ver),
                ],
                closed_drivers_package_list=[
                    ThirdPartyPackage("nvidia-driver-G06", version=ver),
                ],
                third_party_package_list=[
                    # cuda package relation
                    # nvidia-compute-utils-G06
                    #   nvidia-compute-G06
                    #     libnvidia-cfg
                    #     libnvidia-gpucomp
                    #     libnvidia-ml
                    #     libOpenCL1
                    #     nvidia-common-G06
                    #       nvidia-modprobe
                    #       nvidia-open-driver-G06
                    #         dmks
                    #       nvidia-driver-G06
                    #         dmks
                    #     nvidia-persistenced
                    #       libnvidia-cfg
                    #   libnvidia-ml
                    # nvidia-driver-assistant
                    ThirdPartyPackage("dkms"),
                    ThirdPartyPackage("nvidia-driver-assistant"),
                    ThirdPartyPackage("libnvidia-cfg", version=ver),
                    ThirdPartyPackage("libnvidia-gpucomp", version=ver),
                    ThirdPartyPackage("libnvidia-ml", version=ver),
                    ThirdPartyPackage("libOpenCL1"),
                    ThirdPartyPackage("nvidia-common-G06", version=ver),
                    ThirdPartyPackage("nvidia-compute-G06", version=ver),
                    ThirdPartyPackage("nvidia-compute-utils-G06", version=ver),
                    ThirdPartyPackage("nvidia-modprobe", version=ver),
                    ThirdPartyPackage("nvidia-persistenced", version=ver),
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


NVIDIA_CRATE = ContainerCrate(NVIDIA_CONTAINERS)
