"""RabbitMQ container image"""

import textwrap
from pathlib import Path

from bci_build.container_attributes import TCP
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import IDEXEC_SCRIPT
from bci_build.package.helpers import generate_from_image_tag
from bci_build.package.helpers import generate_package_version_check
from bci_build.package.helpers import generate_systemd_tmpfiles_command
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_RABBITMQ_VER_RE = "%%rabbitmq_version%%"

_RABBITMQ_FILES = {
    "entrypoint.sh": (
        (_rabbitmq_dir := Path(__file__).parent / "rabbitmq-server") / "entrypoint.sh"
    ).read_text(),
    "10-defaults.conf": (_rabbitmq_dir / "10-defaults.conf").read_text(),
    "20-management_agent.disable_metrics_collector.conf": (
        _rabbitmq_dir / "20-management_agent.disable_metrics_collector.conf"
    ).read_text(),
    "idexec": IDEXEC_SCRIPT,
}

RABBITMQ_CONTAINERS = [
    ApplicationStackContainer(
        name="rabbitmq",
        pretty_name="RabbitMQ message broker supporting AMQP, STOMP and MQTT",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        version=_RABBITMQ_VER_RE,
        tag_version=(rabbitmq_major := "4"),
        is_singleton_image=True,
        version_in_uid=False,
        replacements_via_service=[
            Replacement(
                regex_in_build_description=_RABBITMQ_VER_RE,
                package_name="rabbitmq-server",
                parse_version=ParseVersion.MINOR,
            )
        ],
        license="MPL-2.0",
        package_list=sorted(
            ["hostname", "rabbitmq-server", "glibc-locale-base"]
            + (["systemd", "xz", "grep", "sed"] if os_version.is_tumbleweed else [])
        ),
        build_stage_custom_end=(
            generate_systemd_tmpfiles_command("rabbitmq-server.conf", use_target=True)
            + generate_package_version_check(
                "rabbitmq-server",
                rabbitmq_major,
                parse_version=ParseVersion.MAJOR,
                use_target=True,
            )
            + textwrap.dedent(rf"""

                COPY idexec /target/usr/local/bin/idexec
                {DOCKERFILE_RUN} chmod 755 /target/usr/local/bin/idexec

                COPY entrypoint.sh /target{(_entrypoint := "/usr/local/bin/entrypoint.sh")}
                {DOCKERFILE_RUN} chmod +x /target{_entrypoint}

                # replace gosu calls with idexec
                {DOCKERFILE_RUN} sed -i 's/exec gosu /exec idexec /g' /target/{_entrypoint}
                {DOCKERFILE_RUN} install -d -m 0755 /target/etc/rabbitmq/conf.d/
            """)
        ),
        volumes=["/var/lib/rabbitmq"],
        exposes_ports=[
            TCP(4369),
            TCP(5671),
            TCP(5672),
            TCP(15691),
            TCP(15692),
            TCP(25672),
        ],
        custom_end=textwrap.dedent("""
            ENV HOME=/var/lib/rabbitmq
            ENV LC_ALL=C.UTF-8

            # the rabbitmq-server startup script uses RUNNING_UNDER_SYSTEMD to determine if the erl command
            # should be started via exec, which results in beam.smp becoming PID 1 in the container
            ENV RUNNING_UNDER_SYSTEMD=true
            COPY 10-defaults.conf 20-management_agent.disable_metrics_collector.conf /etc/rabbitmq/conf.d/
        """),
        extra_files=_RABBITMQ_FILES,
        entrypoint=["/usr/local/bin/entrypoint.sh"],
        cmd=["rabbitmq-server"],
        entrypoint_user="rabbitmq",
        # user_chown=StableUser(user_name="rabbitmq", group_name="rabbitmq"),
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
