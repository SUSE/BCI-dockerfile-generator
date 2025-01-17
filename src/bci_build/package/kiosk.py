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

X11_APP_BASE_CONTAINERS = [
    DevelopmentContainer(
        name="x11app-base",
        os_version=os_version,
        # FIXME: no idea what the tag version should be
        tag_version=(tag_ver := "1"),
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=tag_ver,  # (xorg_server_re := "%%xorg_server_ver%%"),
        pretty_name="X11 App Base Development",
        package_list=[
            "xorg-x11-fonts",
            "libX11-xcb1",
            "libgtk-3-0",
            "libpulse0",
            "libasound2",
            "mozilla-nss",
            "libxshmfence1",
            "libdrm",
            "libgdm1",
            "npm-default",
            "nodejs-default",
        ],
        # replacements_via_service=[
        #     Replacement(
        #         xorg_server_re,
        #         package_name="xorg-x11-server",
        #         parse_version=ParseVersion.MINOR,
        #     )
        # ],
        # generate_package_version_check(
        #     "xorg-x11-server", tag_ver, ParseVersion.MAJOR
        # )
        # +
        custom_end="""
RUN useradd -m user -u 1000
ENV DISPLAY=":0"
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
    "system.pa": (Path(__file__).parent / "pulseaudio" / "system.pa").read_text(),
}

PULSEAUDIO_CONTAINERS = [
    ApplicationStackContainer(
        name="pulseaudio",
        os_version=os_version,
        tag_version=(tag_ver := "17"),
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
        pretty_name="Mozilla Firefox",
        package_list=(
            [
                "MozillaFirefox",
                # required by Firefox via /usr/bin/gconftool-2
                # to be fixed via FileProvides
                "gconf2",
            ]
            + (
                ["MozillaFirefox-branding-openSUSE"]
                if os_version.is_tumbleweed
                else ["MozillaFirefox-branding-SLE"]
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
