"""Application Containers for Docker/OCI Distribution registry"""


from bci_build.container_attributes import TCP
from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import SET_BLKID_SCAN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import format_version
from bci_build.package.versions import get_pkg_version
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

REGISTRY_CONTAINERS = [
    ApplicationStackContainer(
        name="registry",
        package_name="distribution-image",
        pretty_name="OCI Container Registry (Distribution)",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version="%%registry_version%%",
        tag_version=(
            distribution_version := format_version(
                get_pkg_version("distribution", os_version), ParseVersion.MINOR
            )
        ),
        version_in_uid=False,
        is_singleton_image=True,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%registry_version%%",
                package_name="distribution-registry",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="Apache-2.0",
        package_list=[
            "apache2-utils",
            "ca-certificates-mozilla",
            "distribution-registry",
        ],
        entrypoint=["/usr/bin/registry"],
        entrypoint_user="registry",
        cmd=["serve", "/etc/registry/config.yml"],
        volumes=["/var/lib/docker-registry"],
        exposes_ports=[TCP(5000)],
        support_level=SupportLevel.L3,
        min_release_counter={
            OsVersion.SP7: 15,
        },
        build_stage_custom_end=generate_package_version_check(
            "distribution-registry", distribution_version, use_target=True
        )
        + (f"\n{SET_BLKID_SCAN}\n" if os_version.is_sle15 else ""),
        custom_end=(
            f"{DOCKERFILE_RUN} install -d -m 0755 -o registry -g registry /var/lib/docker-registry\n"
            if not os_version.is_sle15
            else ""
        )
        + ("COPY --from=builder /etc/blkid.conf /etc\n" if os_version.is_sle15 else ""),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
