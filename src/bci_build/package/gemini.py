"""Gemini CLI BCI container"""

import textwrap

from bci_build.container_attributes import SupportLevel
from bci_build.os_version import OsVersion
from bci_build.package import DOCKERFILE_RUN
from bci_build.package import ApplicationStackContainer
from bci_build.package import _build_tag_prefix
from bci_build.package.helpers import generate_package_version_check
from bci_build.replacement import Replacement
from bci_build.util import ParseVersion

GEMINI_CONTAINERS = [
    ApplicationStackContainer(
        name="gemini-cli",
        pretty_name="Gemini CLI Sandbox with openSUSE additions",
        version=(gemini_ver := "%%gemini_version%%"),
        tag_version=(gemini_tag_ver := "0"),
        is_singleton_image=True,
        version_in_uid=False,
        no_recommends=False,
        os_version=os_version,
        from_target_image=f"{_build_tag_prefix(os_version)}/node:24-micro",
        is_latest=True,
        support_level=SupportLevel.UNSUPPORTED,
        package_list=sorted(
            (
                "gemini-cli",
                "git-core",
                "gzip",
                "hostname",
                "which",
                "build",
                "quilt",
                "rpm-build",
                "zstd",
            )
        ),
        replacements_via_service=[
            Replacement(
                regex_in_build_description=gemini_ver,
                package_name="gemini-cli",
                parse_version=ParseVersion.PATCH,
            )
        ],
        build_stage_custom_end=generate_package_version_check(
            "gemini-cli", gemini_tag_ver, ParseVersion.MAJOR, use_target=True
        )
        + textwrap.dedent(f"""
            {DOCKERFILE_RUN} useradd sandbox -m -u 499 && install -d -m 0750 /home/sandbox/tmp
            """),
        custom_end=textwrap.dedent("""
            COPY --from=builder /etc/passwd /etc/passwd
            COPY --from=builder /etc/group /etc/group
            COPY --from=builder /home/sandbox /home/sandbox
            USER sandbox
            WORKDIR /home/sandbox/tmp
            ENV TERM=xterm-256color
            ENV SANDBOX="openSUSE BCI Sandbox"
            ENTRYPOINT ["/usr/bin/gemini"]
            CMD [""]"""),
        extra_labels={
            "run": r"podman run --rm --userns=keep-id:uid=499 -it -v \${HOME}/.gemini:/home/sandbox/.gemini:Z -v \$PWD:/home/sandbox/tmp:Z \${IMAGE}",
        },
    )
    for os_version in (OsVersion.TUMBLEWEED,)
]
