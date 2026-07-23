"""Build descriptions for the vnc container, which is part of the
SUSE containerized kiosk solution."""

import textwrap

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import SET_BLKID_SCAN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.kiosk import KIOSK_EXCLUSIVE_ARCH
from bci_build.package.kiosk import KIOSK_SUPPORT_ENDS
from bci_build.package.kiosk import KioskRegistry
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

TIGERVNC_CONTAINERS = [
    ApplicationStackContainer(
        name="tigervnc-x11vnc",
        os_version=os_version,
        exclusive_arch=KIOSK_EXCLUSIVE_ARCH,
        version_in_uid=False,
        tag_version=(tag_ver := "1"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version=(tigervnc_re := "%%tigervnc_ver%%"),
        _publish_registry=(KioskRegistry() if not os_version.is_tumbleweed else None),
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        pretty_name="TigerVNC VNC Server",
        package_list=sorted(
            [
                "tigervnc-x11vnc",
                "gzip",
                "xz",
                "sed",
                "grep",
                "hostname",
                "which",
                "xkeyboard-config",
                "procps",
            ]
            # FIXME: unavailable on SLES
            + (["xsession", "xinput"] if os_version.is_tumbleweed else [])
            # workaround xf86-input-evdev pulling udev/kmod/rpm
            + (["rpm-ndb", "sysvinit-tools"] if os_version.is_sle15 else [])
        ),
        replacements_via_service=[
            Replacement(
                tigervnc_re,
                package_name="tigervnc-x11vnc",
                parse_version=ParseVersion.MINOR,
            )
        ],
        support_level=SupportLevel.L3,
        supported_until=KIOSK_SUPPORT_ENDS,
        entrypoint_user="user",
        cmd=["/usr/bin/x11vnc", "-forever", "-display", ":0", "-alwaysshared"],
        build_stage_custom_end=generate_package_version_check(
            "tigervnc-x11vnc", tag_ver, ParseVersion.MAJOR, use_target=True
        )
        + "\nRUN useradd -m -u 1000 -g 100 user",
        custom_end=textwrap.dedent("""
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/user /home/user
            """)
        + (f"{SET_BLKID_SCAN}\n" if os_version.is_sle15 else ""),
    )
    for os_version in (OsVersion.SP7, OsVersion.TUMBLEWEED)
]
