"""KIWI Appliances Builder SDK container for easy appliance building on SLE Micro."""

from bci_build.package import ALL_NONBASE_OS_VERSIONS
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import BuildType
from bci_build.package import DevelopmentContainer
from bci_build.package import ParseVersion
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version

KIWI_CONTAINERS = [
    DevelopmentContainer(
        name="kiwi",
        pretty_name="KIWI Appliance Builder (kiwi)",
        custom_description="{pretty_name} container {based_on_container}. {privileged_only}",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        # kiwi is not L3 supported
        # support_level=SupportLevel.L3,
        version=(kiwi_ver := get_pkg_version("python-kiwi", os_version)),
        tag_version=format_version(kiwi_ver, ParseVersion.MAJOR),
        version_in_uid=False,
        additional_versions=[
            (kiwi_minor := format_version(kiwi_ver, ParseVersion.MINOR)),
            format_version(kiwi_ver, ParseVersion.PATCH),
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
        ],
        custom_end=f"{generate_package_version_check('python3-kiwi', kiwi_minor, ParseVersion.MINOR)}",
        build_recipe_type=BuildType.DOCKER,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
