"""Build descriptions for the containerized kiosk containers (X11+auxiliary
apps).

"""

from pathlib import Path

from bci_build.container_attributes import Arch
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package import generate_disk_size_constraints
from bci_build.package.helpers import generate_package_version_check

_KIOSK_EXCLUSIVE_ARCH = [Arch.X86_64, Arch.AARCH64]

_XORG_FILES = {
    "preferences": """ShowThemesMenu=0
ShowLogoutMenu=0
ShowFocusModeMenu=0
QuickSwitch=0
""",
    "entrypoint.sh": (
        (_xorg_dir := (_pkg_dir := Path(__file__).parent) / "xorg") / "entrypoint.sh"
    ).read_text(),
    "xinitrc": (_xorg_dir / "xinitrc").read_text(),
    "xorg.conf": (_xorg_dir / "xorg.conf").read_text(),
    "_constraints": generate_disk_size_constraints(4),
}

XORG_CONTAINERS = [
    ApplicationStackContainer(
        name="xorg",
        os_version=os_version,
        exclusive_arch=_KIOSK_EXCLUSIVE_ARCH,
        additional_versions=["notaskbar"],
        version_in_uid=False,
        tag_version=(tag_ver := "21"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=(xorg_server_re := "%%xorg_server_ver%%"),
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


_PULSE_FILES = {
    "client.conf": ((_pa_dir := _pkg_dir / "pulseaudio") / "client.conf").read_text(),
    "daemon.conf": (_pa_dir / "daemon.conf").read_text(),
    "system.pa": (_pa_dir / "system.pa").read_text(),
}

PULSEAUDIO_CONTAINERS = [
    ApplicationStackContainer(
        name="pulseaudio",
        os_version=os_version,
        tag_version=(tag_ver := "17"),
        version_in_uid=False,
        exclusive_arch=_KIOSK_EXCLUSIVE_ARCH,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=(pulseaudio_ver_re := "%%pulseaudio_ver%%"),
        pretty_name="Pulseaudio",
        package_list=["pulseaudio", "pulseaudio-utils"],
        replacements_via_service=[
            Replacement(
                pulseaudio_ver_re,
                package_name="pulseaudio",
                parse_version=ParseVersion.MINOR,
            )
        ],
        extra_files=_PULSE_FILES,
        cmd=["/usr/bin/pulseaudio"],
        custom_end=generate_package_version_check(
            "pulseaudio", tag_ver, ParseVersion.MAJOR
        )
        + """
COPY daemon.conf /etc/pulse/
COPY client.conf /etc/pulse/
COPY system.pa /etc/pulse/
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]


FIREFOX_CONTAINERS = [
    ApplicationStackContainer(
        name=("kiosk-firefox" if os_version.is_tumbleweed else "kiosk-firefox-esr"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        exclusive_arch=_KIOSK_EXCLUSIVE_ARCH,
        version=(ff_ver_re := "%%ff_ver%%"),
        version_in_uid=False,
        pretty_name="Mozilla Firefox",
        package_list=(
            [
                "MozillaFirefox",
                # for fonts to actually display
                "xorg-x11-fonts",
            ]
            + (
                ["MozillaFirefox-branding-openSUSE"]
                if os_version.is_tumbleweed
                else [
                    "MozillaFirefox-branding-SLE",
                    # required by Firefox via /usr/bin/gconftool-2
                    # to be fixed via FileProvides
                    "gconf2",
                ]
            )
        ),
        replacements_via_service=[
            Replacement(
                ff_ver_re,
                package_name="MozillaFirefox",
                parse_version=ParseVersion.MINOR,
            )
        ],
        cmd=["/bin/bash", "-c", "firefox --kiosk $URL"],
        custom_end="""RUN useradd -m user -u 1000
ENV DISPLAY=":0"
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
