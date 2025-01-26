"""Build descriptions for the containerized kiosk containers (X11+auxiliary
apps).

"""

from pathlib import Path

from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package import DevelopmentContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.versions import get_pkg_version

_X11_FILES = {
    "preferences": """ShowThemesMenu=0
ShowLogoutMenu=0
ShowFocusModeMenu=0
QuickSwitch=0
""",
    "entrypoint.sh": (
        (_x11_dir := (_pkg_dir := Path(__file__).parent) / "x11") / "entrypoint.sh"
    ).read_text(),
    "xinitrc": (_x11_dir / "xinitrc").read_text(),
    "xorg.conf": (_x11_dir / "xorg.conf").read_text(),
}

X11_CONTAINERS = [
    DevelopmentContainer(
        name="x11",
        os_version=os_version,
        additional_versions=["notaskbar"],
        version_in_uid=False,
        tag_version=(tag_ver := "21"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=(xorg_server_re := "%%xorg_server_ver%%"),
        pretty_name="X11 Server",
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
        extra_files=_X11_FILES,
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
    "client.conf": """autospawn = no
auto-connect-localhost = yes
""",
    "daemon.conf": """daemonize = no
fail = no
; allow-module-loading = yes
allow-exit = no
use-pid-file = no
system-instance = yes
""",
    "system.pa": (_pkg_dir / "pulseaudio" / "system.pa").read_text(),
}

PULSEAUDIO_CONTAINERS = [
    ApplicationStackContainer(
        name="pulseaudio",
        os_version=os_version,
        tag_version=(tag_ver := "17"),
        version_in_uid=False,
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
    DevelopmentContainer(
        name="firefox",
        os_version=os_version,
        tag_version=(ff_ver := get_pkg_version("MozillaFirefox", os_version)),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=(ff_ver_re := "%%ff_ver%%"),
        version_in_uid=False,
        pretty_name="Mozilla Firefox",
        package_list=(
            ["MozillaFirefox"]
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
        custom_end=generate_package_version_check(
            "MozillaFirefox", ff_ver, ParseVersion.MINOR
        )
        + """
RUN useradd -m user -u 1000
ENV DISPLAY=":0"
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
