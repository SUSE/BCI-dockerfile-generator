"""KIWI Appliances Builder SDK container for easy appliance building on SLE Micro."""

from bci_build.container_attributes import BuildType
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package import ParseVersion
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version

KIWI_CONTAINERS = []

for os_version in list(set(ALL_NONBASE_OS_VERSIONS) | set((OsVersion.SLE16_0,))):
    kiwi_ver = format_version(
        get_pkg_version("python-kiwi", os_version), ParseVersion.PATCH
    )
    kiwi_major = format_version(kiwi_ver, ParseVersion.MAJOR)
    use_kpartx = int(kiwi_major) >= 10

    KIWI_CONTAINERS.append(
        DevelopmentContainer(
            name="kiwi",
            pretty_name="KIWI Appliance Builder (kiwi)",
            custom_description="{pretty_name} container {based_on_container}. {privileged_only}",
            os_version=os_version,
            is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
            # kiwi is not L3 supported
            # support_level=SupportLevel.L3,
            version=kiwi_ver,
            version_in_uid=False,
            additional_versions=[
                kiwi_major,
                kiwi_minor := format_version(kiwi_ver, ParseVersion.MINOR),
            ],
            license="GPL-3.0-or-later",
            package_list=(
                [
                    "checkmedia",
                    "dracut-kiwi-oem-repart",
                    "enchant-devel",
                    "gcc",
                    "glibc-devel",
                    "iproute2",
                    "java-21-openjdk-headless",
                    "jing",
                    "kiwi-systemdeps-filesystems",
                    "kpartx",
                    "libxml2-devel",
                    "lvm2",
                    "make",
                    "netcat-openbsd",
                    "python3-devel",
                    "python3-kiwi",
                    "python3-pip",
                    "tack",
                    "timezone",
                    "xorriso",
                    "xz",
                    *os_version.release_package_names,
                ]
                + (["kpartx"] if use_kpartx else [])
                + os_version.common_devel_packages
            ),
            custom_end=(
                generate_package_version_check(
                    "python3-kiwi", kiwi_minor, ParseVersion.MINOR
                )
                + r"""
SHELL ["/bin/bash", "-c"]
RUN echo $'mapper: \n\
  - part_mapper: kpartx\n\
' > /etc/kiwi.yml
"""
                if use_kpartx
                else ""
            ),
            build_recipe_type=BuildType.DOCKER,
            _min_release_counter=(15 if os_version.is_sle15 else None),
            extra_labels={
                "usage": "This container requires an openSUSE/SUSE host kernel for full functionality.",
            },
            extra_files={
                # kiwi pulls in a ton of dependencies and fails on 4GB disk workers
                "_constraints": generate_disk_size_constraints(8)
            },
        )
    )
