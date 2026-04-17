from jinja2 import Template

from bci_build.container_attributes import Arch
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import ReleaseStage
from bci_build.container_attributes import SupportLevel
from bci_build.containercrate import ContainerCrate
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import _RELEASE_PLACEHOLDER
from bci_build.package import DevelopmentContainer
from bci_build.package import Package
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.thirdparty import ThirdPartyRepo
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.repomdparser import RpmPackage

AMD_REPOS = [
    ThirdPartyRepo(
        name="radeon-sles15sp7-x86_64",
        arch=Arch.X86_64,
        url="https://repo.radeon.com/amdgpu/7.0.3/sle/15.7/main/x86_64/",
        key_url="https://repo.radeon.com/rocm/rocm.gpg.key",
    ),
]


CUSTOM_END_TEMPLATE = Template(
    """
# decompress modules for getKmodsToSign (kmmmodule.go) since it expects uncompressed files
{{ DOCKERFILE_RUN }} \\
    find /lib/modules/{{ kernel_ga }} -name "*.ko.zst" -exec zstd -d --rm {} \\;; \\
    depmod {{ kernel_ga }}

# copy modules to /opt since getKmodsToSign (kmmmodule.go) expects it there
{{ DOCKERFILE_RUN }} \\
    mkdir -p /target/opt/lib/modules/{{ kernel_ga }}/updates/dkms; \\
    cp /lib/modules/{{ kernel_ga }}/updates/amd* /target/opt/lib/modules/{{ kernel_ga }}/updates/dkms; \\
    cp /lib/modules/{{ kernel_ga }}/modules.* /target/opt/lib/modules/{{ kernel_ga }}/; \\
    cp -r /lib/modules/{{ kernel_ga }}/kernel /target/opt/lib/modules/{{ kernel_ga }}/kernel; \\
    depmod -b /target/opt {{ kernel_ga }}

# copy firmware to /firmwareDir
{{ DOCKERFILE_RUN }} \\
    mkdir -p /target/firmwareDir/updates/amdgpu; \\
    cp -r /lib/firmware/updates/amdgpu /target/firmwareDir/updates/amdgpu
"""
)


class AMDDriverBCI(ThirdPartyRepoMixin, DevelopmentContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.extra_files.update(
            {
                "_constraints": generate_disk_size_constraints(4),
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
        # addition tags should match sles-15.7-6.4.0-150700.51-default-7.0.3
        return [
            f"{self.registry_prefix}/amd/amdgpu-driver:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}",
            f"{self.registry_prefix}/amd/amdgpu-driver:{self.image_ref_name}",
        ] + [
            f"{self.registry_prefix}/amd/amdgpu-driver:sles-{self.os_version.os_version}-{v}-default-{self.tag_version}"
            for v in self.additional_versions
        ]

    @property
    def image_ref_name(self) -> str:
        return f"sles-%OS_VERSION_ID_SP%-{self.tag_version}"

    @property
    def build_name(self) -> str:
        return f"{self.name}-{self.tag_version}"

    @property
    def build_version(self) -> str:
        return f"{self.os_version.os_version}.{self.version}"

    @property
    def reference(self) -> str:
        return f"{self.registry}/{self.registry_prefix}/amd/amdgpu-driver:{self.image_ref_name}-{_RELEASE_PLACEHOLDER}"

    @property
    def pretty_reference(self) -> str:
        return f"{self.registry}/{self.registry_prefix}/amd/amdgpu-driver:{self.image_ref_name}"

    def fetch_rpm_packages(self) -> list[RpmPackage]:
        """Fetches all the required packages from the repository.

        Returns:
            list of :py:class:`RpmPackage` representing the downloaded rpms
        """
        if self._rpms:
            return self._rpms

        super().fetch_rpm_packages()

        project = "SUSE:SLE-15-SP7:GA"
        repo = "pool"
        version = "6.4.0"
        release = "150700.51.1"
        arches = self.exclusive_arch
        subpackages = [
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
        ]

        for subpkg in subpackages:
            name = subpkg["name"]
            package = subpkg["package"]
            no_arch = subpkg.get("no_arch", False)

            for arch in arches:
                filename_in_image = f"{name}-{version}-{release}.{arch}.rpm"

                if no_arch:
                    filename_in_repo = f"{name}-{version}-{release}.noarch.rpm"
                else:
                    filename_in_repo = f"{name}-{version}-{release}.{arch}.rpm"

                self._rpms.append(
                    RpmPackage(
                        name=name,
                        arch=str(arch),
                        evr=("", version, release),
                        filename=filename_in_image,
                        url=f"https://api.opensuse.org/public/build/{project}/{repo}/{arch}/{package}/{filename_in_repo}",
                    )
                )

        return self._rpms

    def prepare_template(self) -> None:
        super().prepare_template()

        self.build_stage_custom_end += "\n" + CUSTOM_END_TEMPLATE.render(
            image=self,
            DOCKERFILE_RUN=DOCKERFILE_RUN,
            kernel_ga="6.4.0-150700.51-default",
        )


_AMD_DRIVER_VERSIONS: list[str] = ["7.0.3"]

AMD_CONTAINERS: list[AMDDriverBCI] = []

for os_version in (OsVersion.SP7,):
    for ver in _AMD_DRIVER_VERSIONS:
        AMD_CONTAINERS.append(
            AMDDriverBCI(
                os_version=os_version,
                version=ver,
                tag_version=ver,
                additional_versions=["6.4.0-150700.51"],
                version_in_uid=True,
                use_build_flavor_in_tag=False,
                name="amd-driver",
                pretty_name="AMD GPU Driver",
                license="GPL-2.0 WITH Linux-syscall-note",
                is_latest=False,
                from_image=generate_from_image_tag(os_version, "bci-base"),
                from_target_image=generate_from_image_tag(os_version, "bci-micro"),
                support_level=SupportLevel.TECHPREVIEW,
                supported_until="",
                exclusive_arch=[Arch.X86_64],
                package_list=[
                    (
                        Package("rpm-ndb", PackageType.IMAGE)
                        if os_version.is_sle15
                        else Package("rpm", PackageType.IMAGE)
                    ),
                    # needed by kernel GA packages
                    # since kernel GA packages are using RemoteAssetUrl a few dependencies
                    # are not solved by zypper automatically
                    Package("awk", PackageType.BOOTSTRAP),
                    Package("dwarves", PackageType.BOOTSTRAP),
                    Package("elfutils", PackageType.BOOTSTRAP),
                    Package("gcc", PackageType.BOOTSTRAP),
                    Package("libelf-devel", PackageType.BOOTSTRAP),
                    Package("pesign-obs-integration", PackageType.BOOTSTRAP),
                    Package("zstd", PackageType.BOOTSTRAP),
                    # build requirements for amdgpu-dkms
                    Package("autoconf", PackageType.BOOTSTRAP),
                    Package("automake", PackageType.BOOTSTRAP),
                    Package("bc", PackageType.BOOTSTRAP),
                    Package("bison", PackageType.BOOTSTRAP),
                    Package("dracut", PackageType.BOOTSTRAP),
                    Package("flex", PackageType.BOOTSTRAP),
                    Package("gawk", PackageType.BOOTSTRAP),
                    Package("libzstd-devel", PackageType.BOOTSTRAP),
                    Package("make", PackageType.BOOTSTRAP),
                    Package("mokutil", PackageType.BOOTSTRAP),
                    Package("perl", PackageType.BOOTSTRAP),
                    Package("perl-Bootloader", PackageType.BOOTSTRAP),
                    Package("python3", PackageType.BOOTSTRAP),
                    Package("python3-setuptools", PackageType.BOOTSTRAP),
                    Package("python3-wheel", PackageType.BOOTSTRAP),
                    # runtime requirement to load amdgpu-dkms
                    Package("kmod", PackageType.IMAGE),
                    *os_version.release_package_names,
                ],
                third_party_repos=AMD_REPOS,
                third_party_package_list=[
                    "amdgpu-dkms",
                    "amdgpu-dkms-firmware",
                    "dkms",
                ],
            )
        )

AMD_CRATE = ContainerCrate(AMD_CONTAINERS)
