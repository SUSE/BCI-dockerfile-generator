"""Kubectl BCI container"""

from bci_build.container_attributes import Arch
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag

_KUBECTL_VERSIONS = {
    OsVersion.TUMBLEWEED: ("1.29", "1.30", "1.31", "1.32"),
    OsVersion.SP6: ("1.28",),
    OsVersion.SP7: ("1.28", "1.30"),
}


def _is_latest_kubectl(version: str, os_version: OsVersion) -> bool:
    return (
        version == _KUBECTL_VERSIONS[os_version][-1]
        and os_version in CAN_BE_LATEST_OS_VERSION
    )


KUBECTL_CONTAINERS = [
    ApplicationStackContainer(
        name="kubectl",
        package_name=f"kubectl-{ver}-image",
        pretty_name="kubectl",
        custom_description="Kubernetes CLI for communicating with a Kubernetes cluster's control plane using the Kubernetes API, {based_on_container}.",
        exclusive_arch=[Arch.AARCH64, Arch.PPC64LE, Arch.S390X, Arch.X86_64],
        os_version=os_version,
        is_latest=_is_latest_kubectl(ver, os_version),
        version="%%kubectl_version%%",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        tag_version=ver,
        additional_versions=[ver],
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
    )
    for ver, os_version in (
        [
            (kubectl_version, os_version)
            for os_version in (OsVersion.TUMBLEWEED, OsVersion.SP6, OsVersion.SP7)
            for kubectl_version in _KUBECTL_VERSIONS[os_version]
        ]
    )
]
