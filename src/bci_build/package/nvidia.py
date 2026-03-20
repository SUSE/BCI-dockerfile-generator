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
        ] + [
            f"{self.registry_prefix}/nvidia/driver:{v}"
            for v in self.additional_versions
        ]

    @property
    def image_ref_name(self) -> str:
        # tag should match 580.126.09-sles15.7
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

        pkgs = self.fetch_rpm_packages()

        repo_info = {
            # GA kernel for SP7 is in the pool repo under multiple packages
            OsVersion.SP7: {
                "project": "SUSE:SLE-15-SP7:GA",
                "repo": "pool",
                "version": "6.4.0",
                "package": "!unset!",
                "release": "150700.51.1",
                "arch": self.exclusive_arch,
                "subpackages": {
                    "default": [
                        {
                            "name": "kernel-default",
                            "package": "kernel-default",
                        },
                        {
                            "name": "kernel-default-devel",
                            "package": "kernel-default",
                        },
                        {
                            "name": "kernel-syms",
                            "package": "kernel-syms",
                        },
                        {
                            "name": "kernel-devel",
                            "package": "kernel-source",
                            "no_arch": True,
                        },
                        {
                            "name": "kernel-macros",
                            "package": "kernel-source",
                            "no_arch": True,
                        },
                        # always needed on aarch64 for default
                        {
                            "name": "kernel-64kb-devel",
                            "package": "kernel-64kb",
                            "arch": [Arch.AARCH64],
                        },
                    ],
                    "64kb": [
                        {
                            "name": "kernel-64kb",
                            "package": "kernel-64kb",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-64kb-devel",
                            "package": "kernel-64kb",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-default-devel",
                            "package": "kernel-default",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-syms",
                            "package": "kernel-syms",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-devel",
                            "package": "kernel-source",
                            "no_arch": True,
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-macros",
                            "package": "kernel-source",
                            "no_arch": True,
                            "arch": [Arch.AARCH64],
                        },
                    ],
                },
            },
            # GA kernel for 16.0 is in SLFO under patchinfo.ga
            OsVersion.SL16_0: {
                "project": "SUSE:SLFO:1.2",
                "repo": "standard",
                "package": "patchinfo.ga",
                "version": "6.12.0",
                "release": "160000.5.1",
                "arch": self.exclusive_arch,
                "subpackages": {
                    "default": [
                        {
                            "name": "kernel-default",
                        },
                        {
                            "name": "kernel-default-devel",
                        },
                        {
                            "name": "kernel-syms",
                        },
                        {
                            "name": "kernel-devel",
                            "no_arch": True,
                        },
                        {
                            "name": "kernel-macros",
                            "no_arch": True,
                        },
                        # always needed on aarch64
                        {
                            "name": "kernel-64kb-devel",
                            "arch": [Arch.AARCH64],
                        },
                    ],
                    "64kb": [
                        {
                            "name": "kernel-64kb",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-64kb-devel",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-default-devel",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-syms",
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-devel",
                            "no_arch": True,
                            "arch": [Arch.AARCH64],
                        },
                        {
                            "name": "kernel-macros",
                            "no_arch": True,
                            "arch": [Arch.AARCH64],
                        },
                    ],
                },
            },
        }

        if self.os_version not in repo_info:
            raise ValueError(
                f"Unknown GA kernel packages for {self.os_version.os_version}"
            )

        os_info = repo_info[self.os_version]

        if self.kernel_variant not in os_info["subpackages"]:
            raise ValueError(
                f"Unknown GA kernel versions for {self.os_version.os_version} and {self.kernel_variant}"
            )

        project = os_info["project"]
        repo = os_info["repo"]
        subpackages = os_info["subpackages"][self.kernel_variant]

        for subpkg in subpackages:
            name = subpkg["name"]
            # if a subpackage defines a custom value
            # override the default value for the OS
            package = subpkg.get("package", os_info["package"])
            arches = subpkg.get("arch", os_info["arch"])
            version = subpkg.get("version", os_info["version"])
            release = subpkg.get("release", os_info["release"])
            no_arch = subpkg.get("no_arch", False)

            for arch in arches:
                filename_in_image = f"{name}-{version}-{release}.{arch}.rpm"

                if no_arch:
                    filename_in_repo = f"{name}-{version}-{release}.noarch.rpm"
                else:
                    filename_in_repo = f"{name}-{version}-{release}.{arch}.rpm"

                pkgs.append(
                    RpmPackage(
                        name=name,
                        arch=str(arch),
                        evr=("", version, release),
                        filename=filename_in_image,
                        url=f"https://api.opensuse.org/public/build/{project}/{repo}/{arch}/{package}/{filename_in_repo}",
                    )
                )

        open_packages = [p.name for p in self.open_drivers_package_list]
        closed_packages = [p.name for p in self.closed_drivers_package_list]
        kernel_packages = [pkg["name"] for pkg in subpackages]
        ignore_in_target_packages = open_packages + closed_packages + kernel_packages

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
    # and nvidia-compute has these dependencies
    if driver_branch >= 575:
        packages += [
            ThirdPartyPackage("dkms"),
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
        Package("coreutils", PackageType.IMAGE),
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


def _get_kernel_versions(variant: str, os_version: OsVersion):
    """Return all kernel versions for a given kernel variant."""

    # TODO: This should be moved to the package_versions.json
    #       otherwise a new kernel version needs to be added here
    #       for every release.
    #       Azure is not currently included becuase the kABI is not
    #       stable, and it would require a container for each version.
    if os_version == OsVersion.SL16_0:
        if variant in ["default", "64kb"]:
            return [
                "6.12.0-160000.26.1",
                "6.12.0-160000.9.1",
                "6.12.0-160000.8.1",
                "6.12.0-160000.7.1",
                "6.12.0-160000.6.1",
                "6.12.0-160000.5.1",  # GA
            ]

    if os_version == OsVersion.SP7:
        if variant in ["default", "64kb"]:
            return [
                "6.4.0-150700.53.31.1",
                "6.4.0-150700.53.28.1",
                "6.4.0-150700.53.25.1",
                "6.4.0-150700.53.22.1",
                "6.4.0-150700.53.19.1",
                "6.4.0-150700.53.16.1",
                "6.4.0-150700.53.11.1",
                "6.4.0-150700.53.6.1",
                "6.4.0-150700.53.3.1",
                "6.4.0-150700.51.1",  # GA
            ]

    raise ValueError(f"Unknown kernel versions for '{variant}' on '{os_version}'")


# we need to support all versions supported by the gpu operator
# https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html#gpu-operator-component-matrix
_NVIDIA_DRIVER_VERSIONS: list[tuple] = [
    # G07
    ("595.45.04", True),
    ("590.48.01", True),
    # G06
    ("580.126.16", True),
    ("580.126.09", False),
    ("580.105.08", False),
    ("580.95.05", False),
    ("580.82.07", False),
    ("575.57.08", True),
    ("570.211.01", True),
    ("570.195.03", False),
    ("550.163.01", True),
    # G05 - Legacy
    # ("535.288.01", True),
    # ("535.274.02", False),
]

# we need to build a container for each kernel variant
# azure is skipped for now because the kABI is not stable
_NVIDIA_OS_VERSIONS: list[tuple] = [
    (OsVersion.SP7, "default", [Arch.X86_64, Arch.AARCH64]),
    (OsVersion.SP7, "64kb", [Arch.AARCH64]),
    (OsVersion.SL16_0, "default", [Arch.X86_64, Arch.AARCH64]),
    (OsVersion.SL16_0, "64kb", [Arch.AARCH64]),
]

NVIDIA_CONTAINERS: list[NvidiaDriverBCI] = []

for os_version, kernel_variant, exclusive_arch in _NVIDIA_OS_VERSIONS:
    for ver, is_latest_branch in _NVIDIA_DRIVER_VERSIONS:
        driver_branch = _get_driver_branch(ver)

        # older drivers are not available for SLE 16
        # skip the image in this case
        if os_version == OsVersion.SL16_0 and driver_branch < 595:
            continue

        if os_version not in NVIDIA_REPOS:
            raise ValueError(f"Missing CUDA repositories for {os_version}")

        kernel_versions = []

        # the latest image in a given branch should also include the tags
        # expected when the container image is precompiled
        # the expected tag is <driver-branch>-<kernel-version>-<kernel-variant>-<os-tag>
        # e.g. 590-6.4.0-150700.53.6.1-default-sles15.7
        if is_latest_branch:
            for kernel_version in _get_kernel_versions(kernel_variant, os_version):
                os_tag = f"sles{os_version.os_version}"
                kernel_versions.append(
                    f"{driver_branch}-{kernel_version}-{kernel_variant}-{os_tag}"
                )

        is_default = kernel_variant == "default"

        NVIDIA_CONTAINERS.append(
            NvidiaDriverBCI(
                os_version=os_version,
                version=ver,
                kernel_variant=kernel_variant,
                tag_version=ver if is_default else f"{ver}-{kernel_variant}",
                additional_versions=kernel_versions,
                version_in_uid=True,
                use_build_flavor_in_tag=False,
                build_flavor=(
                    f"driver-{ver}" if is_default else f"driver-{ver}-{kernel_variant}"
                ),
                name="nvidia-driver",
                pretty_name="NVIDIA Driver",
                license="NVIDIA DEEP LEARNING CONTAINER LICENSE",
                is_latest=False,
                from_image=generate_from_image_tag(os_version, "bci-base"),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                package_list=_get_packages(os_version),
                support_level=SupportLevel.TECHPREVIEW,
                supported_until="",
                exclusive_arch=exclusive_arch,
                third_party_repos=NVIDIA_REPOS[os_version],
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
