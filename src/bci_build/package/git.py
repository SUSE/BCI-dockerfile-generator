"""Container description for the Git application container."""

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

GIT_CONTAINERS = [
    ApplicationStackContainer(
        name="git",
        os_version=os_version,
        support_level=SupportLevel.L3,
        pretty_name=f"{os_version.pretty_os_version_no_dash} with Git",
        custom_description="A micro environment with Git {based_on_container}.",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version="%%git_version%%",
        tag_version=format_version(
            git_version := get_pkg_version("git", os_version), ParseVersion.MINOR
        ),
        additional_versions=["%%git_major_version%%"],
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%git_version%%",
                package_name="git-core",
            ),
            Replacement(
                regex_in_build_description="%%git_major_version%%",
                package_name="git-core",
                parse_version=ParseVersion.MAJOR,
            ),
        ],
        license="GPL-2.0-only",
        package_list=[
            "git-core",
            "openssh-clients",
        ],
        build_stage_custom_end=generate_package_version_check(
            "git-core", git_version, ParseVersion.MINOR, use_target=True
        ),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
