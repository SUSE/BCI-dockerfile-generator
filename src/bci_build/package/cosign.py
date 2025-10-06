"""Cosign Application container"""

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package import OsVersion
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

COSIGN_CONTAINERS = [
    ApplicationStackContainer(
        name="cosign",
        pretty_name="cosign",
        custom_description="Signing OCI containers using Sigstore, {based_on_container}.",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version="%%cosign_version%%",
        tag_version=format_version(
            cosign_ver := get_pkg_version("cosign", os_version), ParseVersion.MINOR
        ),
        build_stage_custom_end=generate_package_version_check(
            "cosign", cosign_ver, ParseVersion.MINOR, use_target=True
        ),
        version_in_uid=False,
        additional_versions=[format_version(cosign_ver, ParseVersion.MAJOR)],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%cosign_version%%",
                package_name="cosign",
                parse_version=ParseVersion.PATCH,
            )
        ],
        package_list=["cosign"]
        + (["openSUSE-build-key"] if os_version.is_tumbleweed else ["suse-build-key"]),
        entrypoint=["/usr/bin/cosign"],
        license="Apache-2.0",
        support_level=SupportLevel.L3,
        logo_url="https://raw.githubusercontent.com/sigstore/community/main/artwork/cosign/horizontal/color/sigstore_cosign-horizontal-color.svg",
        min_release_counter={
            OsVersion.SP7: 10,
        },
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
