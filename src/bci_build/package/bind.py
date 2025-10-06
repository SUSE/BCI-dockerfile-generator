"""Build recipe for the ISC Bind 9 container image."""

import textwrap
from pathlib import Path

from bci_build.container_attributes import NetworkPort
from bci_build.container_attributes import NetworkProtocol
from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package.helpers import generate_from_image_tag
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

_BIND_FILES = {
    "entrypoint.sh": (
        (_bind_dir := Path(__file__).parent / "bind") / "entrypoint.sh"
    ).read_text(),
}

_BIND_PATCH_RE = "%%bind_major_minor_patch%%"

BIND_CONTAINERS = [
    ApplicationStackContainer(
        name="bind",
        os_version=os_version,
        is_latest=os_version in CAN_BE_LATEST_OS_VERSION,
        is_singleton_image=True,
        version=_BIND_PATCH_RE,
        tag_version="9",
        pretty_name="ISC BIND 9",
        from_target_image=generate_from_image_tag(os_version, "bci-micro"),
        version_in_uid=False,
        # dig: used by the health check
        package_list=["bind", "bind-utils"],
        exposes_ports=[
            NetworkPort(53),
            NetworkPort(53, NetworkProtocol.UDP),
            NetworkPort(953),
            NetworkPort(853),
            NetworkPort(443),
        ],
        additional_versions=[
            (_bind_minor_re := "%%bind_major_minor%%"),
        ],
        replacements_via_service=[
            Replacement(_bind_minor_re, "bind", parse_version=ParseVersion.MINOR),
            Replacement(_BIND_PATCH_RE, "bind", parse_version=ParseVersion.PATCH),
        ],
        extra_files=_BIND_FILES,
        env={
            # copy-pasta from /etc/sysconfig/named
            "RNDC_KEYSIZE": "512",
            "NAMED_ARGS": "",
            "NAMED_INITIALIZE_SCRIPTS": "",
            # need to set this one so that we can override it
            "NAMED_CONF": "/etc/named.conf",
        },
        build_stage_custom_end=textwrap.dedent(rf"""
            # patch named.prep to not call logger (provided by systemd)
            # and just log to stdout
            {DOCKERFILE_RUN} \
                mkdir -p /target/usr/local/lib/bind; \
                cp /target/{os_version.libexecdir}bind/named.prep {(_named_prep := "/target/usr/local/lib/bind/named.prep")}; \
                sed -i -e 's|logger "Warning: \$1"|echo "Warning: \$1" >\&2|' -e '/\. \$SYSCONFIG_FILE/d' {_named_prep}
            """),
        custom_end=textwrap.dedent(rf"""
            COPY entrypoint.sh {(_entrypoint := "/usr/local/bin/entrypoint.sh")}
            {DOCKERFILE_RUN} chmod +x {_entrypoint}

            # create directories that tmpfiles.d would create for us
            {DOCKERFILE_RUN} \
            """)
        + (" \\\n").join(
            (
                f"    install -d -m {mode} -o {user.partition(':')[0]} -g {user.partition(':')[2]} {dirname};"
                for dirname, mode, user in (
                    ("/run/named", "1775", "root:named"),
                    ("/var/lib/named", "1775", "root:named"),
                    ("/var/lib/named/dyn", "755", "named:named"),
                    (
                        "/var/lib/named/master",
                        "755",
                        "root:root" if not os_version.is_sle15 else "named:named",
                    ),
                    ("/var/lib/named/slave", "755", "named:named"),
                    ("/var/log/named", "750", "named:named"),
                )
            )
        )
        + textwrap.dedent(f"""
            # create files that tmpfiles.d would create for us
            {DOCKERFILE_RUN} touch /var/lib/named/127.0.0.zone /var/lib/named/localhost.zone /var/lib/named/named.root.key /var/lib/named/root.hint

            ENTRYPOINT ["{_entrypoint}"]
            HEALTHCHECK --interval=10s --timeout=5s --retries=10 CMD dig +retry=0 +short @127.0.0.1 conncheck.opensuse.org >/dev/null && echo OK
"""),
    )
    for os_version in ALL_NONBASE_OS_VERSIONS
]
