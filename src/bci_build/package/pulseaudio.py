"""Build description of the pulseaudio container, which is part of the
containerized kiosk

"""

from pathlib import Path

from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import ParseVersion
from bci_build.package import Replacement
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.kiosk import KIOSK_EXCLUSIVE_ARCH

_PULSE_FILES = {
    "client.conf": (
        (_pa_dir := (Path(__file__).parent) / "pulseaudio") / "client.conf"
    ).read_text(),
    "daemon.conf": (_pa_dir / "daemon.conf").read_text(),
    "system.pa": (_pa_dir / "system.pa").read_text(),
    "entrypoint.sh": (_pa_dir / "entrypoint.sh").read_text(),
}

PULSEAUDIO_CONTAINERS = [
    ApplicationStackContainer(
        name="pulseaudio",
        os_version=os_version,
        tag_version=(tag_ver := "17"),
        version_in_uid=False,
        exclusive_arch=KIOSK_EXCLUSIVE_ARCH,
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
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        custom_end=generate_package_version_check(
            "pulseaudio", tag_ver, ParseVersion.MAJOR
        )
        + rf"""
COPY daemon.conf /etc/pulse/
COPY client.conf /etc/pulse/
COPY system.pa /etc/pulse/
COPY entrypoint.sh /usr/local/bin/
{DOCKERFILE_RUN} chmod +x /usr/local/bin/entrypoint.sh;
""",
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
