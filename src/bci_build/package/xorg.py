"""Build descriptions for the xorg container."""

from pathlib import Path

from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check

from .kiosk import KIOSK_EXCLUSIVE_ARCH
from .kiosk import KioskRegistry

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
        ]
        # FIXME: unavailable on SLES
        + (["xsession"] if os_version.is_tumbleweed else []),
        replacements_via_service=[
            Replacement(
                xorg_server_re,
                package_name="xorg-x11-server",
                parse_version=ParseVersion.MINOR,
            )
        ],
        extra_files=_XORG_FILES,
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        custom_end=generate_package_version_check(
            "xorg-x11-server", tag_ver, ParseVersion.MAJOR
        )
        + """
RUN useradd -m user -u 1000
COPY preferences /etc/icewm/preferences
COPY xinitrc /etc/X11/xinit/xinitrc
COPY xorg.conf /etc/X11/xorg.conf.d/xorg.conf

ENV XDG_SESSION_TYPE=x11

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
