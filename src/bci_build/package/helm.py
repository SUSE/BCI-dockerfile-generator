"""BCI Container definition for the helm container."""

from bci_build.container_attributes import ARCH_ONLY_64BIT
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_SLFO_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_SLFO_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

HELM_CONTAINERS = [
    ApplicationStackContainer(
        name="helm",
        pretty_name="Helm (Kubernetes Package Manager)",
        exclusive_arch=ARCH_ONLY_64BIT,
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_SLFO_OS_VERSION,
        is_singleton_image=True,
        version="%%helm_version%%",
        tag_version=format_version(
            helm_ver := get_pkg_version("helm", os_version), ParseVersion.MINOR
        ),
        additional_versions=[
            format_version(helm_ver, ParseVersion.MAJOR),
        ],
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        build_stage_custom_end=generate_package_version_check(
            "helm", helm_ver, use_target=True
        ),
        version_in_uid=False,
        min_release_counter={OsVersion.SL16_0: 70},
        license="Apache-2.0",
        package_list=[
            "ca-certificates-mozilla",
            "helm",
        ],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%helm_version%%",
                package_name="helm",
                parse_version=ParseVersion.PATCH,
            )
        ],
        entrypoint=["/usr/bin/helm"],
        cmd=["help"],
        support_level=SupportLevel.L3,
    )
    for os_version in ALL_NONBASE_SLFO_OS_VERSIONS
]
