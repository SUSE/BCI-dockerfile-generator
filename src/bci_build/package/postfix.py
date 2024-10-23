"""Postfix container for the Application collection."""

from pathlib import Path

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.registry import ApplicationCollectionRegistry

_POSTFIX_FILES = {}
for filename in (
    "entrypoint.sh",
    "entrypoint.sles.sh",
    "smtpd_sender_login_maps",
    "virtual_alias_domains",
    "virtual_alias_maps",
    "virtual_gid_maps",
    "virtual_mailbox_maps",
    "virtual_uid_maps",
):
    if filename.startswith("entrypoint."):
        _POSTFIX_FILES[filename] = (
            Path(__file__).parent / "postfix" / "entrypoint" / filename
        ).read_bytes()
    else:
        _POSTFIX_FILES[filename] = (
            Path(__file__).parent / "postfix" / "entrypoint" / "ldap" / filename
        ).read_bytes()


POSTFIX_CONTAINERS = [
    ApplicationStackContainer(
        name="postfix",
        package_name=None if os_version.is_tumbleweed else "sac-postfix-image",
        _publish_registry=(
            None if os_version.is_tumbleweed else ApplicationCollectionRegistry()
        ),
        pretty_name="Postfix",
        custom_description="Postfix container is fast and secure mail server, {based_on_container}.",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION and os_version.is_tumbleweed,
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version="%%postfix_version%%",
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description="%%postfix_version%%",
                package_name="postfix",
                parse_version=ParseVersion.MINOR,
            )
        ],
        package_list=[
            name
            for name in (
                "ca-certificates-mozilla",
                "curl",
                "cyrus-sasl",
                "cyrus-sasl-plain",
                "ed",
                "findutils",
                "gawk",
                "grep",
                "netcfg",
                "postfix",
                "postfix-ldap",
                "postfix-lmdb",
                "sed",
                "timezone",
            )
            + (
                (
                    "openldap2",
                    "openldap2-client",
                    "mandoc",
                    "spamassassin-spamc",
                    "spamass-milter",
                    "gzip",
                    "tar",
                )
                if os_version == OsVersion.TUMBLEWEED
                else ()
            )
        ],
        entrypoint=["/entrypoint/entrypoint.sh"],
        cmd=["postfix", "start-fg"],
        license="(EPL-2.0 OR IPL-1.0) AND MIT",
        extra_files=_POSTFIX_FILES,
        support_level=SupportLevel.TECHPREVIEW,
        exposes_ports=["25", "465", "587"],
        volumes=["/var/spool/postfix", "/var/spool/vmail", "/etc/pki"],
        custom_end=f"""{DOCKERFILE_RUN} mkdir -p /entrypoint/ldap
COPY {"entrypoint.sh" if os_version == OsVersion.TUMBLEWEED else "entrypoint.sles.sh"} /entrypoint/entrypoint.sh
{DOCKERFILE_RUN} chmod +x /entrypoint/entrypoint.sh
COPY smtpd_sender_login_maps virtual_alias_domains virtual_alias_maps virtual_gid_maps virtual_mailbox_maps virtual_uid_maps /entrypoint/ldap/
HEALTHCHECK --interval=5s --timeout=10s --start-period=30s --retries=3 \
        CMD postfix status
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
