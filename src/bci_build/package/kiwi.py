"""KIWI Appliances Builder SDK container for easy appliance building on SLE Micro."""

from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import BuildType
from bci_build.package import DevelopmentContainer
from bci_build.package.versions import get_pkg_version
from bci_build.package.versions import to_major_minor_version
from bci_build.package.versions import to_major_version

KIWI_CONTAINERS = [
    DevelopmentContainer(
        name="kiwi",
        package_name="kiwi-image",
        pretty_name="KIWI Appliance Builder (kiwi)",
        custom_description="{pretty_name} container {based_on_container}. {privileged_only}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        # kiwi is not L3 supported
        # support_level=SupportLevel.L3,
        version=(kiwi_ver := get_pkg_version("python3-kiwi", os_version)),
        version_in_uid=False,
        additional_versions=[
            to_major_minor_version(kiwi_ver),
            to_major_version(kiwi_ver),
        ],
        license="GPL-3.0-or-later",
        package_list=[
            "btrfsprogs",
            "checkmedia",
            "dracut-kiwi-oem-repart",
            "e2fsprogs",
            "enchant-devel",
            "gcc",
            "glibc-devel",
            "iproute2",
            "jing",
            "kiwi-systemdeps-core",
            "libxml2-devel",
            "lvm2",
            "make",
            "netcat-openbsd",
            "python3-devel",
            "python3-kiwi",
            "python3-pip",
            "tack",
            "timezone",
            "xfsprogs",
        ],
        build_recipe_type=BuildType.DOCKER,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
