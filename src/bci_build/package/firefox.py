"""Build description for the Firefox container, which is part of the
SUSE containerized kiosk solution.
"""

import textwrap

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.kiosk import KIOSK_EXCLUSIVE_ARCH
from bci_build.package.kiosk import KIOSK_SUPPORT_ENDS
from bci_build.package.kiosk import KioskRegistry

FIREFOX_CONTAINERS = [
    ApplicationStackContainer(
        name=("kiosk-firefox" if os_version.is_tumbleweed else "firefox-esr"),
        package_name=(None if os_version.is_tumbleweed else "kiosk-firefox-esr-image"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        exclusive_arch=KIOSK_EXCLUSIVE_ARCH,
        version=(ff_ver_re := "%%ff_ver%%"),
        tag_version=None if os_version.is_tumbleweed else "esr",
        is_singleton_image=True,
        version_in_uid=False,
        pretty_name="Mozilla Firefox",
        _publish_registry=(KioskRegistry() if not os_version.is_tumbleweed else None),
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        package_list=(
            [
                "MozillaFirefox",
                # for fonts to actually display
                "xorg-x11-fonts",
                # for puleaudio communication
                "libpulse0",
                # for cjk fonts
                "noto-sans-cjk-fonts",
                # Provides necessary codecs for video/audio playback
                "libavcodec58_134",
            ]
            + (
                ["MozillaFirefox-branding-openSUSE",]
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
        support_level=SupportLevel.L3,
        supported_until=KIOSK_SUPPORT_ENDS,
        cmd=["/bin/bash", "-c", "firefox --kiosk $URL"],
        # TODO add package_version_check and tag_version
        # Ensure that the user is created and Firefox has access to its profile directory.
        build_stage_custom_end=textwrap.dedent(f"""\
            {DOCKERFILE_RUN} useradd -m -u 1000 -U user
            {DOCKERFILE_RUN} mkdir -p /home/user/.mozilla/firefox
            {DOCKERFILE_RUN} chown -R user:user /home/user/.mozilla
            """),
        custom_end=textwrap.dedent("""
            ENV DISPLAY=":0"
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/user /home/user
        """),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
