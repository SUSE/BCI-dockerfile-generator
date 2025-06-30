"""Build descriptions for the xorg container, which is part of the
SUSE containerized kiosk solution."""

import textwrap
from pathlib import Path

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.kiosk import KIOSK_EXCLUSIVE_ARCH
from bci_build.package.kiosk import KIOSK_SUPPORT_ENDS
from bci_build.package.kiosk import KioskRegistry

_XORG_FILES = {
    "entrypoint.sh": (
        (_xorg_dir := (Path(__file__).parent / "xorg")) / "entrypoint.sh"
    ).read_text(),
    "preferences": (_xorg_dir / "preferences").read_text(),
    "xinitrc": (_xorg_dir / "xinitrc").read_text(),
    "xorg.conf": (_xorg_dir / "xorg.conf").read_text(),
    "_constraints": generate_disk_size_constraints(4),
}

XORG_CONTAINERS = [
    ApplicationStackContainer(
        name="xorg",
        os_version=os_version,
        exclusive_arch=KIOSK_EXCLUSIVE_ARCH,
        additional_versions=["notaskbar"],
        version_in_uid=False,
        tag_version=(tag_ver := "21"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version=(xorg_server_re := "%%xorg_server_ver%%"),
        _publish_registry=(KioskRegistry() if not os_version.is_tumbleweed else None),
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        pretty_name="Xorg Server",
        package_list=[
            "hostname",
            "which",
            "xinit",
            "xhost",
            "xorg-x11",
            "xorg-x11-server",
            "xrandr",
            "icewm-lite",
            "xf86-input-evdev",
            "xf86-input-libinput",
            "xkeyboard-config",
            "xinput",
            # indirect dependencies
            "xorg-x11-essentials",
            "xdm",
            # for /sbin/pidof, required by xdm
            "sysvinit-tools",
            "procps",
        ]
        # FIXME: unavailable on SLES
        + (["xsession"] if os_version.is_tumbleweed else [])
        # workaround xf86-input-evdev pulling udev/kmod/rpm
        + (["rpm-ndb"] if os_version.is_sle15 else []),
        replacements_via_service=[
            Replacement(
                xorg_server_re,
                package_name="xorg-x11-server",
                parse_version=ParseVersion.MINOR,
            )
        ],
        extra_files=_XORG_FILES,
        support_level=SupportLevel.L3,
        supported_until=KIOSK_SUPPORT_ENDS,
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        build_stage_custom_end=generate_package_version_check(
            "xorg-x11-server", tag_ver, ParseVersion.MAJOR, use_target=True
        )
        + "\nRUN useradd -m user -u 1000",
        custom_end=textwrap.dedent(f"""
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/user /home/user
            COPY preferences /etc/icewm/preferences
            COPY xinitrc /etc/X11/xinit/xinitrc
            COPY xorg.conf /etc/X11/xorg.conf.d/xorg.conf

            ENV XDG_SESSION_TYPE=x11

            COPY entrypoint.sh /usr/local/bin/entrypoint.sh
            {DOCKERFILE_RUN} chmod +x /usr/local/bin/entrypoint.sh
            """),
    )
    for os_version in {v for v in ALL_NONBASE_OS_VERSIONS if v != OsVersion.SLE16_0}
]

XORG_CLIENT_CONTAINERS = [
    ApplicationStackContainer(
        name="xorg-client",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        exclusive_arch=KIOSK_EXCLUSIVE_ARCH,
        version_in_uid=False,
        version="21",
        tag_version=(tag_ver := "21"),
        is_singleton_image=True,
        pretty_name="Xorg Client",
        _publish_registry=(KioskRegistry() if not os_version.is_tumbleweed else None),
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        package_list=(
            [
                # for fonts to actually display
                "xorg-x11-fonts",
                # for puleaudio communication
                "libpulse0",
                # for cjk fonts
                "noto-sans-cjk-fonts",
                # Provides necessary codecs for video/audio playback
                "libavcodec58_134",
            ]
        ),
        support_level=SupportLevel.L3,
        supported_until=KIOSK_SUPPORT_ENDS,
        # TODO add package_version_check and tag_version
        build_stage_custom_end=textwrap.dedent(f"""\
            {DOCKERFILE_RUN} useradd -m -u 1000 -U user
            """),
        custom_end=textwrap.dedent("""
            ENV DISPLAY=":0"
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/user /home/user
        """),
    )
    for os_version in {v for v in ALL_NONBASE_OS_VERSIONS if v != OsVersion.SLE16_0}
]
