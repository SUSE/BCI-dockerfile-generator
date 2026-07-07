"""
This module contains classes and functions related to updating and generating Dockerfiles for NVIDIA driver containers.

NVIDIA drivers are taken from CUDA repositories and use the GA kernel.
"""

import textwrap
from functools import lru_cache
from pathlib import Path

import requests
from jinja2 import Template
from version_utils import rpm

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
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
from bci_build.package.versions import get_all_pkg_version
from bci_build.repomdparser import RpmPackage

_NVIDIA_REPOS = {
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
    OsVersion.SL16_0: [
        ThirdPartyRepo(
            name="cuda-sles15-x86_64",
            arch=Arch.X86_64,
            url="https://developer.download.nvidia.com/compute/cuda/repos/suse16/x86_64/",
            key_url="https://developer.download.nvidia.com/compute/cuda/repos/suse16/x86_64/3A8B5622.pub",
        ),
        ThirdPartyRepo(
            name="cuda-sles15-sbsa",
            arch=Arch.AARCH64,
            url="https://developer.download.nvidia.com/compute/cuda/repos/suse16/sbsa/",
            key_url="https://developer.download.nvidia.com/compute/cuda/repos/suse16/sbsa/3A8B5622.pub",
        ),
    ],
}

# we need to support all versions supported by the gpu operator
# https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html#gpu-operator-component-matrix
# we should support versions only for data center
# https://docs.nvidia.com/datacenter/tesla/index.html
_NVIDIA_DRIVER_VERSIONS: list[str] = [
    # G07
    "595.71.05",
    "590.48.01",
    # G06
    "580.173.02",
    "575.57.08",
    "570.211.01",
    "550.163.01",
    # G05 - Legacy
    # 535 and older are not planned
]

# we need to build a container for each kernel variant
# azure is skipped for now because the kABI is not stable
_NVIDIA_OS_VERSIONS: list[tuple] = [
    (OsVersion.SP7, "default", [Arch.X86_64, Arch.AARCH64]),
    (OsVersion.SP7, "64kb", [Arch.AARCH64]),
    (OsVersion.SL16_0, "default", [Arch.X86_64, Arch.AARCH64]),
    (OsVersion.SL16_0, "64kb", [Arch.AARCH64]),
]

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

{{ DOCKERFILE_RUN }} if rpm -q dkms >/dev/null 2>&1; then \\
        printf 'compress="zstd"\\n' > /etc/dkms/framework.conf.d/module-compress.conf; \\
        dkms autoinstall -k $(basename /lib/modules/*-{{ image.kernel_variant }}); \\
    fi
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

{{ DOCKERFILE_RUN }} if rpm -q dkms >/dev/null 2>&1; then \\
        printf 'compress="zstd"\\n' > /etc/dkms/framework.conf.d/module-compress.conf; \\
        dkms autoinstall -k $(basename /lib/modules/*-{{ image.kernel_variant }}); \\
    fi
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

{{ DOCKERFILE_RUN }} if rpm --root /target -q compat-usrmerge-tools; then rpm --root /target -e compat-usrmerge-tools; fi
"""
)


class NvidiaDriverBCI(ThirdPartyRepoMixin, DevelopmentContainer):
    def __init__(
        self,
        open_drivers_package_list: list[ThirdPartyPackage],
        closed_drivers_package_list: list[ThirdPartyPackage],
        kernel_variant: str,
        **kwargs,
    ):
        self.open_drivers_package_list = open_drivers_package_list
        self.closed_drivers_package_list = closed_drivers_package_list
        self.kernel_variant = kernel_variant

        third_party_package_list = kwargs.pop("third_party_package_list", [])
        third_party_package_list = sorted(
            self.open_drivers_package_list
            + self.closed_drivers_package_list
            + third_party_package_list,
            key=lambda p: p.name,
        )

        super().__init__(
            third_party_package_list=third_party_package_list,
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
    def labelprefix(self) -> str:
        labelprefix = "com.suse"
        if self.os_version.is_tumbleweed:
            labelprefix = "org.opensuse"
        return f"{labelprefix}.third-party.{(self.custom_labelprefix_end or self.name)}"

    @property
    def registry_prefix(self):
        return "third-party"

    @property
    def build_tags(self) -> list[str]:
        return [
            f"{self.registry_prefix}/nvidia/driver:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}",
            f"{self.registry_prefix}/nvidia/driver:{self.image_ref_name}",
        ] + [
            f"{self.registry_prefix}/nvidia/driver:{v}"
            for v in self.additional_versions
        ]

    @property
    def image_ref_name(self) -> str:
        return f"{self.tag_version}-sles%OS_VERSION_ID_SP%"

    @property
    def build_name(self) -> str:
        return f"{self.name}-{self.tag_version}"

    @property
    def build_version(self) -> str:
        return f"{self.os_version.os_version}.{self.version}"

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

        # ensure we do not ship versions that are not supported by NVIDIA datacenter
        assert _is_datacenter_driver(self.version), (
            f"Version '{self.version}' is not datacenter supported"
        )

        # Find the kernel version used to build the nvidia-kmp driver for branches >= 595
        driver_branch = _get_driver_branch(self.version)
        built_kernel = _get_built_kernel_version(
            self.version, self.os_version, self.kernel_variant, self.exclusive_arch
        )

        pkgs = self.fetch_rpm_packages()
        kernel_packages = []

        kernel_ga_rpms = _get_kernel_ga_rpms(
            self.os_version,
            self.kernel_variant,
            self.exclusive_arch,
            built_kernel=built_kernel,
        )
        pkgs.extend(kernel_ga_rpms)
        kernel_packages += [rpm.name for rpm in kernel_ga_rpms]

        # since 595 we use kmp drivers instead of dkms
        kmp_packages = []
        if driver_branch >= 595:
            nvidia_kmp_rpms = _get_nvidia_kmp_rpms(
                self.version, self.os_version, self.kernel_variant, self.exclusive_arch
            )
            pkgs.extend(nvidia_kmp_rpms)
            kernel_packages += [rpm.name for rpm in nvidia_kmp_rpms]
            kmp_packages += [rpm.name for rpm in nvidia_kmp_rpms]

        open_packages = [p.name for p in self.open_drivers_package_list]
        closed_packages = [p.name for p in self.closed_drivers_package_list]
        ignore_in_target_packages = open_packages + closed_packages + kernel_packages

        self.prepare_extra_files()

        # These packages should only be in the final layer, not in driver build layers
        # Other packages from third_party_package_list (dkms, nvidia-compute-*, etc.) ARE needed
        # in driver build layers for DKMS compilation
        target_layer_only_packages = [
            "libnvidia-nscq",
            "libnvidia-nscq-550",
            "libnvidia-nscq-570",
            "libnvidia-nscq-575",
            "libnvsdm",
            "libnvsdm-570",
            "libnvsdm-575",
            "libnvsdm",
            "nvidia-fabricmanager",
            "nvidia-imex",
            "nvidia-imex-570",
            "nvidia-imex-575",
            "nvidia-imex-550",
            "nvlsm",
        ]

        self.build_stage_custom_end = CUSTOM_END_TEMPLATE.render(
            image=self,
            packages=pkgs,
            DOCKERFILE_RUN=DOCKERFILE_RUN,
            get_open_packages_for_arch=lambda arch: [
                pkg
                for pkg in pkgs
                if pkg.name not in closed_packages
                and pkg.name not in target_layer_only_packages
                and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
            get_closed_packages_for_arch=lambda arch: [
                pkg
                for pkg in pkgs
                if pkg.name not in open_packages
                and pkg.name not in kmp_packages
                and pkg.name not in target_layer_only_packages
                and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
            get_target_packages_for_arch=lambda arch: [
                pkg
                for pkg in pkgs
                if pkg.name not in ignore_in_target_packages
                and pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
        )

        super(DevelopmentContainer, self).prepare_template()


def _get_driver_branch(driver_version: str) -> int:
    """Extract the driver branch from the driver version."""
    try:
        return int(driver_version.split(".")[0])
    except Exception:
        raise ValueError(f"Failed to parse driver branch: {driver_version}")


def _get_open_drivers_packages(
    driver_version: str, kernel_variant: str
) -> list[ThirdPartyPackage]:
    """Select the correct open driver package for each version."""
    driver_branch = _get_driver_branch(driver_version)

    if driver_branch >= 595:
        # use kmp driver for newer versions instead of dkms
        return []

    if driver_branch >= 590:
        return [
            ThirdPartyPackage("nvidia-open-driver-G07", version=driver_version),
        ]

    if driver_branch >= 575:
        return [
            ThirdPartyPackage("nvidia-open-driver-G06", version=driver_version),
        ]

    if driver_branch == 570:
        return [
            ThirdPartyPackage(
                f"nvidia-open-driver-G06-kmp-{kernel_variant}", version=driver_version
            ),
        ]

    if driver_branch == 550:
        # 550 also requires gsp.bin for the open driver
        return [
            ThirdPartyPackage(
                "kernel-firmware-nvidia-gspx-G06", version=driver_version
            ),
            ThirdPartyPackage(
                f"nvidia-open-driver-G06-kmp-{kernel_variant}", version=driver_version
            ),
        ]

    raise ValueError(f"Unknown open driver for {driver_version}")


def _get_closed_drivers_packages(
    driver_version: str, kernel_variant: str
) -> list[ThirdPartyPackage]:
    """Select the correct closed driver package for each version."""
    driver_branch = _get_driver_branch(driver_version)

    if driver_branch >= 590:
        return [
            ThirdPartyPackage("nvidia-driver-G07", version=driver_version),
        ]

    if driver_branch >= 575:
        return [
            ThirdPartyPackage("nvidia-driver-G06", version=driver_version),
        ]

    if driver_branch >= 550:
        return [
            ThirdPartyPackage(
                f"nvidia-driver-G06-kmp-{kernel_variant}", version=driver_version
            ),
        ]

    raise ValueError(f"Unknown closed driver for {driver_version}")


def _get_compute_packages(
    driver_version: str, os_version: OsVersion
) -> list[ThirdPartyPackage]:
    """
    Get the correct common and compute packages an all its depedencies.

    Over the years, packages were split into smaller packages, and for
    this reason, later releases require more packages, while on older releases
    most dependencies were in nvidia-compute-utils.
    """
    driver_branch = _get_driver_branch(driver_version)

    packages: list[ThirdPartyPackage] = [
        # required on all versions and not tied to the driver version
        ThirdPartyPackage("nvidia-driver-assistant"),
        ThirdPartyPackage("nvlsm"),
    ]

    if driver_branch >= 580:
        packages += [
            ThirdPartyPackage("libnvidia-nscq", version=driver_version),
            ThirdPartyPackage("libnvsdm", version=driver_version, arch=Arch.X86_64),
            ThirdPartyPackage("nvidia-imex", version=driver_version),
            ThirdPartyPackage("nvidia-fabricmanager", version=driver_version),
        ]
    else:
        packages += [
            ThirdPartyPackage(
                "libnvidia-nscq-" + str(driver_branch), version=driver_version
            ),
            ThirdPartyPackage(
                "nvidia-imex-" + str(driver_branch), version=driver_version
            ),
        ]
        if driver_branch >= 560:
            packages += [
                ThirdPartyPackage(
                    "libnvsdm-" + str(driver_branch),
                    version=driver_version,
                    arch=Arch.X86_64,
                ),
            ]

    # select the correct compute and common packages for each version
    # these are required on all versions, but package name varies
    if driver_branch >= 590:
        packages += [
            ThirdPartyPackage("nvidia-common-G07", version=driver_version),
            ThirdPartyPackage("nvidia-compute-G07", version=driver_version),
            ThirdPartyPackage("nvidia-compute-utils-G07", version=driver_version),
        ]
    elif driver_branch >= 570:
        packages += [
            ThirdPartyPackage("nvidia-common-G06", version=driver_version),
            ThirdPartyPackage("nvidia-compute-G06", version=driver_version),
            ThirdPartyPackage("nvidia-compute-utils-G06", version=driver_version),
        ]
    elif driver_branch >= 550:
        packages += [
            ThirdPartyPackage("nvidia-compute-G06", version=driver_version),
            ThirdPartyPackage("nvidia-compute-utils-G06", version=driver_version),
        ]
    else:
        raise ValueError(f"Unknown compute package for {driver_version}")

    # since 575 the drivers are dkms-based
    # however, since 595 we use kmp drivers for the open driver,
    # but we still use dkms for the proprietary driver
    if driver_branch >= 575:
        packages += [
            ThirdPartyPackage("dkms"),
        ]

    # since 575 nvidia-compute has these dependencies
    if driver_branch >= 575:
        packages += [
            ThirdPartyPackage("libnvidia-gpucomp", version=driver_version),
        ]

    # since 570 nvidia-compute and nvidia-common have these dependencies
    if driver_branch >= 570:
        packages += [
            ThirdPartyPackage("nvidia-modprobe", version=driver_version),
            ThirdPartyPackage("nvidia-persistenced", version=driver_version),
        ]

        # on the CUDA repository for SLE 16 the libOpenCL1 package does
        # not exists, but it is provided by cuda-toolkit but only on x86_64.
        # for 16.0 we pick from SLE 16 repository as an extra package.
        if os_version == OsVersion.SP7:
            packages += [
                ThirdPartyPackage("libOpenCL1"),
            ]

    # since 580 nvidia-compute has these dependencies
    if driver_branch >= 580:
        packages += [
            ThirdPartyPackage("libnvidia-cfg", version=driver_version),
            ThirdPartyPackage("libnvidia-ml", version=driver_version),
        ]

    if driver_branch == 550:
        # provides libnvidia-cfg.so for nvidia-persistenced
        packages += [
            ThirdPartyPackage("nvidia-gl-G06", version=driver_version),
        ]

    return packages


def _get_packages(os_version: OsVersion):
    packages: list[Package] = [
        # needed by kernel GA packages
        # since kernel GA packages are using RemoteAssetUrl a few dependencies
        # are not solved by zypper automatically
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
        Package("findutils", PackageType.IMAGE),
        Package("grep", PackageType.IMAGE),
        Package("jq", PackageType.IMAGE),
        Package("kmod", PackageType.IMAGE),
        (
            Package("rpm-ndb", PackageType.IMAGE)
            if os_version.is_sle15
            else Package("rpm", PackageType.IMAGE)
        ),
        Package("sed", PackageType.IMAGE),
        Package("util-linux", PackageType.IMAGE),
        Package("util-linux-systemd", PackageType.IMAGE),
        Package("infiniband-diags", PackageType.IMAGE),
    ]

    if os_version == OsVersion.SL16_0:
        packages += [
            # GA kernel explicitly requires gcc13
            Package("gcc13", PackageType.BOOTSTRAP),
            Package("suse-kernel-rpm-scriptlets", PackageType.BOOTSTRAP),
            # not available in the CUDA repository
            # but available in the SLE repository
            Package("libOpenCL1", PackageType.BOOTSTRAP),
            # required by nvidia-persistenced
            Package("libtirpc3", PackageType.BOOTSTRAP),
            Package("libtirpc3", PackageType.IMAGE),
        ]

    return packages


def _get_built_kernel_version(
    driver_version: str,
    os_version: OsVersion,
    kernel_variant: str,
    exclusive_arch: list[Arch],
) -> str | None:
    """Find the kernel version used to build the nvidia-kmp driver for branches >= 595."""
    driver_branch = _get_driver_branch(driver_version)
    if driver_branch < 595:
        return None

    kmp_rpms = _get_nvidia_kmp_rpms(
        driver_version, os_version, kernel_variant, exclusive_arch
    )
    if kmp_rpms:
        kmp_rpm_version = kmp_rpms[0].evr[1]
        if "_k" in kmp_rpm_version:
            built_kernel_raw = kmp_rpm_version.split("_k")[-1]
            return "-".join(built_kernel_raw.split("_", 1))

    return None


def _get_nvidia_kmp_rpms(driver_version, os_version, kernel_variant, exclusive_arch):
    match os_version:
        case OsVersion.SL16_0:
            project = "SUSE:SLFO:1.2"
            repo = "standard"

            match driver_version:
                case "595.71.05":
                    package = "patchinfo.20260504131235888449.187004354831441"
                    name = f"nvidia-open-driver-G07-signed-cuda-kmp-{kernel_variant}"
                    version = "595.71.05_k6.12.0_160000.29"
                    release = "160000.1.1"
                case _:
                    raise ValueError(
                        f"KMP driver not found for '{os_version.os_version}' and '{driver_version}'"
                    )
        case OsVersion.SP7:
            project = "SUSE:SLE-15-SP7:Update"
            repo = "pool"

            match driver_version:
                case "595.71.05":
                    package = "nvidia-open-driver-G07-signed.44120:cuda"
                    name = f"nvidia-open-driver-G07-signed-cuda-kmp-{kernel_variant}"
                    version = "595.71.05_k6.4.0_150700.53.40"
                    release = "150700.16.8.1"
                case _:
                    raise ValueError(
                        f"KMP driver not found for '{os_version.os_version}' and '{driver_version}'"
                    )
        case _:
            raise ValueError(f"KMP driver not found for '{os_version.os_version}'")

    pkgs = []

    for arch in exclusive_arch:
        filename = f"{name}-{version}-{release}.{arch}.rpm"

        pkgs.append(
            RpmPackage(
                name=name,
                arch=str(arch),
                evr=("", version, release),
                filename=filename,
                url=f"https://api.opensuse.org/public/build/{project}/{repo}/{arch}/{package}/{filename}",
            )
        )

    return pkgs


_SL16_0_KERNEL_PATCHINFO_MAP = {
    "6.12.0-160000.29": "patchinfo.20260501095726722273.187004354831441",
}

_SP7_KERNEL_PACKAGE_MAP = {
    "6.4.0-150700.53.40": {
        "kernel-default": "kernel-default.44023",
        "kernel-syms": "kernel-syms.44023",
        "kernel-source": "kernel-source.44023",
        "kernel-64kb": "kernel-64kb.44023",
    },
}


def _get_kernel_ga_rpms(
    os_version: OsVersion,
    kernel_variant: str,
    exclusive_arch: list[Arch],
    built_kernel: str | None = None,
):
    match os_version:
        case OsVersion.SL16_0:
            project = "SUSE:SLFO:1.2"
            repo = "standard"
            if built_kernel:
                version, release_raw = built_kernel.split("-", 1)
                release = f"{release_raw}.1"
                obs_pkg = _SL16_0_KERNEL_PATCHINFO_MAP.get(built_kernel)
                if not obs_pkg:
                    raise ValueError(
                        f"Kernel patchinfo not found for built_kernel '{built_kernel}' in SL16_0"
                    )
                obs_pkg_default = obs_pkg
                obs_pkg_syms = obs_pkg
                obs_pkg_source = obs_pkg
                obs_pkg_64kb = obs_pkg
            else:
                version = "6.12.0"
                release = "160000.5.1"
                obs_pkg_default = "patchinfo.ga"
                obs_pkg_syms = "patchinfo.ga"
                obs_pkg_source = "patchinfo.ga"
                obs_pkg_64kb = "patchinfo.ga"

            match kernel_variant:
                case "default":
                    packages = [
                        (obs_pkg_default, "kernel-default", []),
                        (obs_pkg_default, "kernel-default-devel", []),
                        (obs_pkg_syms, "kernel-syms", []),
                        (obs_pkg_source, "kernel-devel", []),
                        (obs_pkg_source, "kernel-macros", []),
                        # always needed on aarch64 for default
                        (obs_pkg_64kb, "kernel-64kb-devel", [Arch.AARCH64]),
                    ]
                case "64kb":
                    packages = [
                        (obs_pkg_64kb, "kernel-64kb", []),
                        (obs_pkg_64kb, "kernel-64kb-devel", []),
                        (obs_pkg_default, "kernel-default-devel", []),
                        (obs_pkg_syms, "kernel-syms", []),
                        (obs_pkg_source, "kernel-devel", []),
                        (obs_pkg_source, "kernel-macros", []),
                    ]
                case _:
                    raise ValueError(
                        f"Kernel variant '{kernel_variant}' not found for '{os_version.os_version}'"
                    )

        case OsVersion.SP7:
            if built_kernel:
                project = "SUSE:SLE-15-SP7:Update"
                repo = "pool"
                version, release_raw = built_kernel.split("-", 1)
                release = f"{release_raw}.1"
                obs_pkg_map = _SP7_KERNEL_PACKAGE_MAP.get(built_kernel)
                if not obs_pkg_map:
                    raise ValueError(
                        f"Kernel package not found for built_kernel '{built_kernel}' in SP7"
                    )
                obs_pkg_default = obs_pkg_map["kernel-default"]
                obs_pkg_syms = obs_pkg_map["kernel-syms"]
                obs_pkg_source = obs_pkg_map["kernel-source"]
                obs_pkg_64kb = obs_pkg_map["kernel-64kb"]
            else:
                project = "SUSE:SLE-15-SP7:GA"
                repo = "pool"
                version = "6.4.0"
                release = "150700.51.1"
                obs_pkg_default = "kernel-default"
                obs_pkg_syms = "kernel-syms"
                obs_pkg_source = "kernel-source"
                obs_pkg_64kb = "kernel-64kb"

            match kernel_variant:
                case "default":
                    packages = [
                        (obs_pkg_default, "kernel-default", []),
                        (obs_pkg_default, "kernel-default-devel", []),
                        (obs_pkg_syms, "kernel-syms", []),
                        (obs_pkg_source, "kernel-devel", []),
                        (obs_pkg_source, "kernel-macros", []),
                        # always needed on aarch64 for default
                        (obs_pkg_64kb, "kernel-64kb-devel", [Arch.AARCH64]),
                    ]
                case "64kb":
                    packages = [
                        (obs_pkg_64kb, "kernel-64kb", []),
                        (obs_pkg_64kb, "kernel-64kb-devel", []),
                        (obs_pkg_default, "kernel-default-devel", []),
                        (obs_pkg_syms, "kernel-syms", []),
                        (obs_pkg_source, "kernel-devel", []),
                        (obs_pkg_source, "kernel-macros", []),
                    ]
                case _:
                    raise ValueError(
                        f"Kernel variant '{kernel_variant}' not found for '{os_version.os_version}'"
                    )

        case _:
            raise ValueError(f"Kernel GA not found for '{os_version.os_version}'")

    pkgs = []

    for package, subpackage, arches in packages:
        if not arches:
            arches = exclusive_arch

        for arch in arches:
            filename_in_image = f"{subpackage}-{version}-{release}.{arch}.rpm"
            is_no_arch = subpackage in ["kernel-devel", "kernel-macros"]

            if is_no_arch:
                filename_in_repo = f"{subpackage}-{version}-{release}.noarch.rpm"
            else:
                filename_in_repo = f"{subpackage}-{version}-{release}.{arch}.rpm"

            pkgs.append(
                RpmPackage(
                    name=subpackage,
                    arch=str(arch),
                    evr=("", version, release),
                    filename=filename_in_image,
                    url=f"https://api.opensuse.org/public/build/{project}/{repo}/{arch}/{package}/{filename_in_repo}",
                )
            )

    return pkgs


def _get_kernel_versions(variant: str, os_version: OsVersion):
    """Return all kernel versions for a given kernel variant."""
    versions = get_all_pkg_version(f"kernel-{variant}", os_version)
    versions.reverse()
    return versions


@lru_cache(maxsize=1)
def _get_datacenter_driver_versions():
    """
    Return the datacenter driver versions supported by NVIDIA.
    """
    res = requests.get("https://docs.nvidia.com/datacenter/tesla/drivers/releases.json")
    res.raise_for_status()

    data = res.json()

    versions = []

    for branch, info in data.items():
        versions += [release["release_version"] for release in info["driver_info"]]

    return versions


def _is_datacenter_driver(version: str):
    """
    Check if the version is a datacenter driver version supported by NVIDIA.
    """
    versions = _get_datacenter_driver_versions()
    return version in versions


NVIDIA_CONTAINERS: list[NvidiaDriverBCI] = []

for os_version, kernel_variant, exclusive_arch in _NVIDIA_OS_VERSIONS:
    seen_versions = set()

    for ver in _NVIDIA_DRIVER_VERSIONS:
        branch = _get_driver_branch(ver)

        if branch in seen_versions:
            raise ValueError(f"Multiple versions provided for {branch}")
        else:
            seen_versions.add(branch)

        # older drivers are not available for SLE 16
        # skip the image in this case
        if os_version == OsVersion.SL16_0 and branch < 595:
            continue

        if os_version not in _NVIDIA_REPOS:
            raise ValueError(f"Missing CUDA repositories for {os_version}")

        kernel_versions = []

        # Find the kernel version used to build the nvidia-kmp driver for branches >= 595
        built_kernel = _get_built_kernel_version(
            ver, os_version, kernel_variant, exclusive_arch
        )

        # these tags are expected when the container image is precompiled
        # the tag is <driver-branch>-<kernel-version>-<kernel-variant>-<os-tag>
        # e.g. 590-6.4.0-150700.53.6-default-sles15.7
        for kernel_version in _get_kernel_versions(kernel_variant, os_version):
            if built_kernel and rpm.compare_versions(kernel_version, built_kernel) < 0:
                continue

            os_tag = f"sles{os_version.os_version}"
            kernel_versions.append(
                f"{branch}-{kernel_version}-{kernel_variant}-{os_tag}"
            )

        is_default = kernel_variant == "default"

        NVIDIA_CONTAINERS.append(
            NvidiaDriverBCI(
                os_version=os_version,
                version=ver,
                kernel_variant=kernel_variant,
                tag_version=branch if is_default else f"{branch}-{kernel_variant}",
                additional_versions=kernel_versions,
                version_in_uid=True,
                use_build_flavor_in_tag=False,
                build_flavor=(
                    f"driver-{branch}"
                    if is_default
                    else f"driver-{branch}-{kernel_variant}"
                ),
                name="nvidia-driver",
                pretty_name="NVIDIA Driver",
                license="NVIDIA DEEP LEARNING CONTAINER LICENSE",
                is_latest=False,
                from_image=generate_from_image_tag(os_version, "bci-base"),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                package_list=_get_packages(os_version),
                support_level=SupportLevel.L3,
                supported_until="",
                exclusive_arch=exclusive_arch,
                third_party_repos=_NVIDIA_REPOS[os_version],
                open_drivers_package_list=_get_open_drivers_packages(
                    ver, kernel_variant
                ),
                closed_drivers_package_list=_get_closed_drivers_packages(
                    ver, kernel_variant
                ),
                third_party_package_list=_get_compute_packages(ver, os_version),
                entrypoint=["nvidia-driver", "load"],
                env={
                    "DRIVER_VERSION": ver,
                    "DRIVER_TYPE": "passthrough",
                    "DRIVER_BRANCH": str(_get_driver_branch(ver)),
                    "VGPU_LICENSE_SERVER_TYPE": "NLS",
                    "DISABLE_VGPU_VERSION_CHECK": "true",
                    "NVIDIA_VISIBLE_DEVICES": "void",
                    "KERNEL_VERSION": "latest",
                },
            )
        )


NVIDIA_CRATE = ContainerCrate(NVIDIA_CONTAINERS)
