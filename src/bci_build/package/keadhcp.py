"""KEA DHCP Server BCI container"""

from bci_build.os_version import OsVersion
from bci_build.package import ApplicationStackContainer
from bci_build.package.versions import get_pkg_version

_BASE_PODMAN_KEA_CMD = "podman run --replace -it --privileged --network=host"
_KEA_DHCP4_CONFIG_PATH = "/etc/kea/kea-dhcp4.conf"
_KEA_DHCP6_CONFIG_PATH = "/etc/kea/kea-dhcp6.conf"

KEA_DHCP_CONTAINERS = []

KEA_DHCP_CONTAINERS.append(
    ApplicationStackContainer(
        name="keadhcp",
        os_version=OsVersion.TUMBLEWEED,
        version=get_pkg_version("kea", OsVersion.TUMBLEWEED),
        license="MPL-2.0",
        is_latest=True,
        pretty_name="Kea DHCP Server",
        package_list=["kea", "util-linux"],
        custom_end="""
RUN mkdir -p /var/run/kea
""",
        extra_labels={
            "run": f"{_BASE_PODMAN_KEA_CMD} --name kea-dhcp4 -v /etc/kea:/etc/kea IMAGE kea-dhcp4  -c {_KEA_DHCP4_CONFIG_PATH}",
            "runcwd": f"{_BASE_PODMAN_KEA_CMD} --name kea-dhcp4 -v .:/etc/kea IMAGE kea-dhcp4  -c {_KEA_DHCP4_CONFIG_PATH}",
            "run_dhcp6": f"{_BASE_PODMAN_KEA_CMD} --name kea-dhcp6 -v /etc/kea:/etc/kea IMAGE kea-dhcp6  -c {_KEA_DHCP6_CONFIG_PATH}",
            "runcwd_dhcp6": f"{_BASE_PODMAN_KEA_CMD} --name kea-dhcp6 -v .:/etc/kea IMAGE kea-dhcp6  -c {_KEA_DHCP6_CONFIG_PATH}",
        },
        exposes_ports=["67", "67/udp"],
    )
)
