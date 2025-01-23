"""Build description for the stunnel BCI."""

from pathlib import Path

from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check

STUNNEL_CONTAINERS = [
    ApplicationStackContainer(
        name="stunnel",
        os_version=os_version,
        tag_version=(tag_ver := "5"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version=(stunnel_version_re := "%%stunnel_re%%"),
        pretty_name="Stunnel",
        package_list=["stunnel"],
        replacements_via_service=[
            Replacement(stunnel_version_re, package_name="stunnel")
        ],
        extra_files={
            "entrypoint.sh": (
                (stunnel_dir := Path(__file__).parent / "stunnel") / "entrypoint.sh"
            ).read_bytes(),
            "stunnel.conf": (stunnel_dir / "stunnel.conf").read_bytes(),
        },
        build_stage_custom_end=generate_package_version_check(
            "stunnel", tag_ver, ParseVersion.MAJOR, use_target=True
        ),
        custom_end=f"""COPY entrypoint.sh /usr/local/bin/
COPY stunnel.conf /etc/stunnel/stunnel.conf
{DOCKERFILE_RUN} chmod 0755 /usr/local/bin/entrypoint.sh; \
    chown --recursive stunnel /etc/stunnel
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/sbin/stunnel"]
USER stunnel
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
