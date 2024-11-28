"""Container description for the Git application container."""

from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package import Package
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version

GIT_CONTAINERS = [
    ApplicationStackContainer(
        name="git",
        os_version=os_version,
        support_level=SupportLevel.L3,
        pretty_name=f"{os_version.pretty_os_version_no_dash} with Git",
        custom_description="A micro environment with Git {based_on_container}.",
        from_image=generate_from_image_tag(os_version, "bci-micro"),
        build_recipe_type=BuildType.KIWI,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%git_version%%",
        tag_version=format_version(
            get_pkg_version("git", os_version), ParseVersion.MINOR
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
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "git-core",
                "openssh-clients",
            )
            + (() if os_version == OsVersion.TUMBLEWEED else ("skelcd-EULA-bci",))
        ],
        # intentionally empty
        config_sh_script="""
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
