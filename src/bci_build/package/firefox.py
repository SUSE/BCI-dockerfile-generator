"""Build description for the Firefox container for the containerized kiosk
containers.

"""

from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.kiosk import KIOSK_EXCLUSIVE_ARCH

FIREFOX_CONTAINERS = [
    ApplicationStackContainer(
        name=("kiosk-firefox" if os_version.is_tumbleweed else "kiosk-firefox-esr"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        exclusive_arch=KIOSK_EXCLUSIVE_ARCH,
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
