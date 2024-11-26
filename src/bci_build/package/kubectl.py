"""Kubectl BCI container"""

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version

KUBECTL_CONTAINERS = []

KUBECTL_CONTAINERS = [
    ApplicationStackContainer(
        name="kubectl",
        pretty_name="kubectl",
        custom_description="Kuberneted CLI for communicating with a Kubernetes cluster's control plane, using the Kubernetes API.",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%kubectl_version%%",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        tag_version=ver,
        version_in_uid=False,
        additional_versions=[format_version(ver, ParseVersion.MAJOR)],
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%kubectl_version%%",
                package_name=f"kubernetes{ver}-client",
                parse_version=ParseVersion.PATCH,
            )
        ],
        package_list=[f"kubernetes{ver}-client"],
        entrypoint=["kubectl"],
        license="Apache-2.0",
        support_level=SupportLevel.L3,
        logo_url="https://raw.githubusercontent.com/kubernetes/kubernetes/master/logo/logo.png",
        _min_release_counter=0,
        build_stage_custom_end=generate_package_version_check(
            f"kubernetes{ver}-client",
            get_pkg_version(f"kubernetes{ver}", os_version),
            ParseVersion.PATCH,
            use_target=True,
        ),
    )
    for ver, os_version in (
        ("1.31", OsVersion.TUMBLEWEED),
        ("1.28", OsVersion.SP5),
        ("1.28", OsVersion.SP6),
        ("1.28", OsVersion.SP7),
    )
]
