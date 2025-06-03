"""KIWI Appliances Builder SDK container for easy appliance building on SLE Micro."""

from bci_build.container_attributes import BuildType
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import DevelopmentContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version


def generate_kiwi_10_config():
    """Configure kiwi for run within a container. This includes:
    * force part_mapper to be kpartx rather than the default udev, which we don't run in the image.
    * (temporarily) disabling filesystem checks (https://github.com/OSInside/kiwi/pull/2826 )
    """
    return f"""{DOCKERFILE_RUN} printf "runtime_checks:\\n  - disable:\\n    - check_target_dir_on_unsupported_filesystem\\n\\nmapper:\\n  - part_mapper: kpartx\\n" > /etc/kiwi.yml"""


KIWI_CONTAINERS = [
    DevelopmentContainer(
        name="kiwi",
        pretty_name="KIWI Appliance Builder (kiwi)",
        custom_description="{pretty_name} container {based_on_container}. {privileged_only}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        # kiwi is not L3 supported
        # support_level=SupportLevel.L3,
        version="%%kiwi_version%%",
        tag_version=(
            kiwi_minor := format_version(
                get_pkg_version("python-kiwi", os_version), ParseVersion.MINOR
            )
        ),
        version_in_uid=False,
        additional_versions=[
            format_version(
                get_pkg_version("python-kiwi", os_version), ParseVersion.MAJOR
            ),
        ],
        license="GPL-3.0-or-later",
        package_list=[
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
        + os_version.common_devel_packages,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%kiwi_version%%",
                package_name="python3-kiwi",
                parse_version=ParseVersion.PATCH,
            )
        ],
        custom_end=(
            f"{generate_package_version_check('python3-kiwi', kiwi_minor, ParseVersion.MINOR)}\n"
        )
        + (generate_kiwi_10_config() if float(kiwi_minor) >= 10 else ""),
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
    for os_version in list(set(ALL_NONBASE_OS_VERSIONS) | set((OsVersion.SLE16_0,)))
]
