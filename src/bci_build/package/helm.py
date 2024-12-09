"""BCI Container definition for the helm container."""

from bci_build.container_attributes import BuildType
from bci_build.container_attributes import PackageType
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package import Package
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.versions import get_pkg_version

HELM_CONTAINERS = [
    ApplicationStackContainer(
        name="helm",
        pretty_name="Kubernetes Package Manager",
        from_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=get_pkg_version("helm", os_version),
        version_in_uid=False,
        license="Apache-2.0",
        package_list=[
            Package(name, pkg_type=PackageType.BOOTSTRAP)
            for name in (
                "ca-certificates-mozilla",
                "helm",
            )
        ],
        entrypoint=["/usr/bin/helm"],
        cmd=["help"],
        build_recipe_type=BuildType.KIWI,
        support_level=SupportLevel.L3,
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
