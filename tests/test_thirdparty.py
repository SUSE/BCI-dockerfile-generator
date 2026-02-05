from unittest.mock import patch

from bci_build.container_attributes import Arch
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.templates import DOCKERFILE_TEMPLATE
from tests.test_repomdparser import fake_repo_get


class DummyThirdPartyImage(ThirdPartyRepoMixin, DevelopmentContainer):
    pass


DOCKERFILE_RENDERED = """# SPDX-License-Identifier: MIT

# Copyright

#!UseOBSRepositories
#!ExclusiveArch: x86_64 aarch64
#!BuildTag: bci/dummy-third-party-image:1-%RELEASE%
#!BuildTag: bci/dummy-third-party-image:1
#!BuildTag: bci/dummy-third-party-image:latest
#!BuildName: bci-dummy-third-party-image-1
#!BuildVersion: 15.7.1
FROM registry.suse.com/bci/bci-base:15.7

RUN \\
    zypper -n install --no-recommends wget
RUN mkdir -p /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-1-1.0.2.aarch64.rpm sha256:value
COPY dummy-pkg-1-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-1-1.0.2.x86_64.rpm sha256:value
COPY dummy-pkg-1-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-3-1.0.2.aarch64.rpm sha256:value
COPY dummy-pkg-3-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-3-1.0.2.x86_64.rpm sha256:value
COPY dummy-pkg-3-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-2-1.0.2.aarch64.rpm sha256:value
COPY dummy-pkg-2-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-2-1.0.2.x86_64.rpm sha256:value
COPY dummy-pkg-2-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-5-1.0.2.aarch64.rpm sha256:value
COPY dummy-pkg-5-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-5-1.0.2.x86_64.rpm sha256:value
COPY dummy-pkg-5-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-4-1.0.2.aarch64.rpm sha256:value
COPY dummy-pkg-4-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-pkg-4-1.0.2.x86_64.rpm sha256:value
COPY dummy-pkg-4-1.0.2.x86_64.rpm /tmp/

COPY third-party.gpg.key /tmp/dummy-third-party-image.gpg.key
RUN rpm --import /tmp/dummy-third-party-image.gpg.key


RUN if [ "$(uname -m)" = "x86_64" ]; then \\
        zypper -n install \\
            /tmp/dummy-pkg-1-1.0.2.x86_64.rpm \\
            /tmp/dummy-pkg-3-1.0.2.x86_64.rpm \\
            /tmp/dummy-pkg-2-1.0.2.x86_64.rpm \\
            /tmp/dummy-pkg-5-1.0.2.x86_64.rpm \\
            /tmp/dummy-pkg-4-1.0.2.x86_64.rpm; \\
    fi
RUN if [ "$(uname -m)" = "aarch64" ]; then \\
        zypper -n install \\
            /tmp/dummy-pkg-1-1.0.2.aarch64.rpm \\
            /tmp/dummy-pkg-3-1.0.2.aarch64.rpm \\
            /tmp/dummy-pkg-2-1.0.2.aarch64.rpm \\
            /tmp/dummy-pkg-5-1.0.2.aarch64.rpm \\
            /tmp/dummy-pkg-4-1.0.2.aarch64.rpm; \\
    fi

COPY third-party.repo /etc/zypp/repos.d/dummy-third-party-image.repo

RUN rm -rf /tmp/*

# cleanup logs and temporary files
RUN zypper -n clean -a; \\
    # LOGCLEAN #
# set the day of last password change to empty
RUN sed -i 's/^\\([^:]*:[^:]*:\\)[^:]*\\(:.*\\)$/\\1\\2/' /etc/shadow

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dummy-third-party-image
LABEL org.opencontainers.image.authors="https://github.com/SUSE/bci/discussions"
LABEL org.opencontainers.image.title="SLE BCI Dummy Third Party Image"
LABEL org.opencontainers.image.description="Dummy Third Party Image container based on the SUSE Linux Enterprise Base Container Image."
LABEL org.opencontainers.image.version="1"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="1-%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/dummy-third-party-image:1-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix
LABEL org.opencontainers.image.base.name="%BASE_REFNAME%"
LABEL org.opencontainers.image.base.digest="%BASE_DIGEST%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL_WITH(README.md)%"
"""

REPO_RENDERED = """[dummy-third-party-image]
name=dummy-third-party-image
baseurl=https://packages.example.com/sles/15.7/
enabled=1
gpgcheck=1
gpgkey=https://packages.example.com/keys/repo.asc
"""


def test_third_party_template():
    image = DummyThirdPartyImage(
        tag_version="1",
        version="1",
        os_version=OsVersion.SP7,
        name="dummy-third-party-image",
        pretty_name="Dummy Third Party Image",
        is_latest=True,
        package_name="dummy-third-party-image",
        exclusive_arch=[Arch.X86_64, Arch.AARCH64],
        package_list=["wget"],
        third_party_repo_url="https://packages.example.com/sles/15.7/",
        third_party_repo_key_url="https://packages.example.com/keys/repo.asc",
        third_party_repo_key_file="",
        third_party_package_list=[
            "dummy-pkg-1",
            "dummy-pkg-3",
            "dummy-pkg-2",
            "dummy-pkg-5",
            "dummy-pkg-4",
        ],
    )

    with patch("bci_build.repomdparser.requests.get", side_effect=fake_repo_get):
        image.prepare_template()

    rendered = DOCKERFILE_TEMPLATE.render(
        image=image,
        INFOHEADER="# Copyright",
        DOCKERFILE_RUN="RUN",
        LOG_CLEAN="# LOGCLEAN #",
        BUILD_FLAVOR=image.build_flavor,
    )

    assert rendered == DOCKERFILE_RENDERED


def test_third_party_repo():
    image = DummyThirdPartyImage(
        tag_version="1",
        version="1",
        os_version=OsVersion.SP7,
        name="dummy-third-party-image",
        pretty_name="Dummy Third Party Image",
        is_latest=True,
        package_name="dummy-third-party-image",
        exclusive_arch=[Arch.X86_64, Arch.AARCH64],
        package_list=["wget"],
        third_party_repo_url="https://packages.example.com/sles/15.7/",
        third_party_repo_key_url="https://packages.example.com/keys/repo.asc",
        third_party_repo_key_file="GPGKEY",
        third_party_package_list=[
            "dummy-pkg-1",
            "dummy-pkg-3",
            "dummy-pkg-2",
            "dummy-pkg-5",
            "dummy-pkg-4",
        ],
    )

    assert image.repo_filename == "dummy-third-party-image.repo"
    assert image.repo_key_filename == "dummy-third-party-image.gpg.key"
    assert image.extra_files["third-party.gpg.key"] == "GPGKEY"
    assert image.extra_files["third-party.repo"] == REPO_RENDERED
