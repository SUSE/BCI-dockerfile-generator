from unittest.mock import Mock
from unittest.mock import patch

from bci_build.container_attributes import Arch
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package.thirdparty import ThirdPartyRepo
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.templates import DOCKERFILE_TEMPLATE
from tests.test_repomdparser import fake_repo_get


class DummyThirdPartyImage(ThirdPartyRepoMixin, DevelopmentContainer):
    pass


def fake_repo_and_key_get(url, *args, **kwargs):
    resp = Mock()
    resp.raise_for_status.return_value = None
    resp.status_code = 200

    match url:
        case "https://packages.example.com/keys/repo.asc":
            resp.text = "GPGKEY"
        case _:
            return fake_repo_get(url, *args, **kwargs)

    return resp


DOCKERFILE_RENDERED_SINGLE = """# SPDX-License-Identifier: MIT

# Copyright

#!UseOBSRepositories
#!ExclusiveArch: x86_64 aarch64
#!BuildTag: bci/dummy-sle-repo:1-%RELEASE%
#!BuildTag: bci/dummy-sle-repo:1
#!BuildTag: bci/dummy-sle-repo:latest
#!BuildName: bci-dummy-sle-repo-1
#!BuildVersion: 15.7.1
FROM registry.suse.com/bci/bci-base:15.7

RUN \\
    zypper -n install --no-recommends wget
RUN mkdir -p /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-1-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-1-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-1-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-1-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-3-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-3-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-3-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-3-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-2-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-2-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-2-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-2-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-5-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-5-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-5-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-5-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-4-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-4-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-4-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-4-1.0.2.x86_64.rpm /tmp/

COPY sle.gpg.key /tmp/dummy-sle-repo.gpg.key
RUN rpm --import /tmp/dummy-sle-repo.gpg.key


RUN if [ "$(uname -m)" = "x86_64" ]; then \\
        zypper -n install \\
            /tmp/dummy-sle-pkg-1-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-3-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-2-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-5-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-4-1.0.2.x86_64.rpm; \\
    fi
RUN if [ "$(uname -m)" = "aarch64" ]; then \\
        zypper -n install \\
            /tmp/dummy-sle-pkg-1-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-3-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-2-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-5-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-4-1.0.2.aarch64.rpm; \\
    fi

COPY sle.repo /etc/zypp/repos.d/dummy-sle-repo.repo

RUN rm -rf /tmp/*

# cleanup logs and temporary files
RUN zypper -n clean -a; \\
    # LOGCLEAN #
# set the day of last password change to empty
RUN sed -i 's/^\\([^:]*:[^:]*:\\)[^:]*\\(:.*\\)$/\\1\\2/' /etc/shadow

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dummy-sle-repo
LABEL org.opencontainers.image.authors="https://github.com/SUSE/bci/discussions"
LABEL org.opencontainers.image.title="Dummy Third Party Image for SUSE Linux Enterprise Server 15 SP7"
LABEL org.opencontainers.image.description="Dummy Third Party Image container based on the SUSE Linux Enterprise Base Container Image."
LABEL org.opencontainers.image.version="1"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="1-%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/dummy-sle-repo:1-%RELEASE%"
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

DOCKERFILE_RENDERED_MULTI = """# SPDX-License-Identifier: MIT

# Copyright

#!UseOBSRepositories
#!ExclusiveArch: x86_64 aarch64
#!BuildTag: bci/dummy-sle-repo:1-%RELEASE%
#!BuildTag: bci/dummy-sle-repo:1
#!BuildTag: bci/dummy-sle-repo:latest
#!BuildName: bci-dummy-sle-repo-1
#!BuildVersion: 15.7.1
FROM registry.suse.com/bci/bci-base:15.7

RUN \\
    zypper -n install --no-recommends wget
RUN mkdir -p /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-1-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-1-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-1-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-1-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.org/opensuse/15.7/Packages/dummy-opensuse-pkg-3-1.0.2.aarch64.rpm sha256:value
COPY dummy-opensuse-pkg-3-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.org/opensuse/15.7/Packages/dummy-opensuse-pkg-3-1.0.2.x86_64.rpm sha256:value
COPY dummy-opensuse-pkg-3-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-2-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-2-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-2-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-2-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.org/opensuse/15.7/Packages/dummy-opensuse-pkg-5-1.0.2.aarch64.rpm sha256:value
COPY dummy-opensuse-pkg-5-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.org/opensuse/15.7/Packages/dummy-opensuse-pkg-5-1.0.2.x86_64.rpm sha256:value
COPY dummy-opensuse-pkg-5-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-4-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-4-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-4-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-4-1.0.2.x86_64.rpm /tmp/

COPY sle.gpg.key /tmp/dummy-sle-repo.gpg.key
RUN rpm --import /tmp/dummy-sle-repo.gpg.key
COPY opensuse.gpg.key /tmp/dummy-opensuse-repo.gpg.key
RUN rpm --import /tmp/dummy-opensuse-repo.gpg.key


RUN if [ "$(uname -m)" = "x86_64" ]; then \\
        zypper -n install \\
            /tmp/dummy-sle-pkg-1-1.0.2.x86_64.rpm \\
            /tmp/dummy-opensuse-pkg-3-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-2-1.0.2.x86_64.rpm \\
            /tmp/dummy-opensuse-pkg-5-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-4-1.0.2.x86_64.rpm; \\
    fi
RUN if [ "$(uname -m)" = "aarch64" ]; then \\
        zypper -n install \\
            /tmp/dummy-sle-pkg-1-1.0.2.aarch64.rpm \\
            /tmp/dummy-opensuse-pkg-3-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-2-1.0.2.aarch64.rpm \\
            /tmp/dummy-opensuse-pkg-5-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-4-1.0.2.aarch64.rpm; \\
    fi

COPY sle.repo /etc/zypp/repos.d/dummy-sle-repo.repo
COPY opensuse.repo /etc/zypp/repos.d/dummy-opensuse-repo.repo

RUN rm -rf /tmp/*

# cleanup logs and temporary files
RUN zypper -n clean -a; \\
    # LOGCLEAN #
# set the day of last password change to empty
RUN sed -i 's/^\\([^:]*:[^:]*:\\)[^:]*\\(:.*\\)$/\\1\\2/' /etc/shadow

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dummy-sle-repo
LABEL org.opencontainers.image.authors="https://github.com/SUSE/bci/discussions"
LABEL org.opencontainers.image.title="Dummy Third Party Image for SUSE Linux Enterprise Server 15 SP7"
LABEL org.opencontainers.image.description="Dummy Third Party Image container based on the SUSE Linux Enterprise Base Container Image."
LABEL org.opencontainers.image.version="1"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="1-%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/dummy-sle-repo:1-%RELEASE%"
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

DOCKERFILE_RENDERED_KEY_FETCH = """# SPDX-License-Identifier: MIT

# Copyright

#!UseOBSRepositories
#!ExclusiveArch: x86_64 aarch64
#!BuildTag: bci/dummy-sle-repo:1-%RELEASE%
#!BuildTag: bci/dummy-sle-repo:1
#!BuildTag: bci/dummy-sle-repo:latest
#!BuildName: bci-dummy-sle-repo-1
#!BuildVersion: 15.7.1
FROM registry.suse.com/bci/bci-base:15.7

RUN \\
    zypper -n install --no-recommends wget
RUN mkdir -p /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-1-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-1-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-1-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-1-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-3-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-3-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-3-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-3-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-2-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-2-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-2-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-2-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-5-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-5-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-5-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-5-1.0.2.x86_64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-4-1.0.2.aarch64.rpm sha256:value
COPY dummy-sle-pkg-4-1.0.2.aarch64.rpm /tmp/
#!RemoteAssetUrl: https://packages.example.com/sles/15.7/Packages/dummy-sle-pkg-4-1.0.2.x86_64.rpm sha256:value
COPY dummy-sle-pkg-4-1.0.2.x86_64.rpm /tmp/

COPY sle.gpg.key /tmp/sle.gpg.key
RUN rpm --import /tmp/sle.gpg.key


RUN if [ "$(uname -m)" = "x86_64" ]; then \\
        zypper -n install \\
            /tmp/dummy-sle-pkg-1-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-3-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-2-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-5-1.0.2.x86_64.rpm \\
            /tmp/dummy-sle-pkg-4-1.0.2.x86_64.rpm; \\
    fi
RUN if [ "$(uname -m)" = "aarch64" ]; then \\
        zypper -n install \\
            /tmp/dummy-sle-pkg-1-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-3-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-2-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-5-1.0.2.aarch64.rpm \\
            /tmp/dummy-sle-pkg-4-1.0.2.aarch64.rpm; \\
    fi

COPY sle.repo /etc/zypp/repos.d/sle.repo

RUN rm -rf /tmp/*

# cleanup logs and temporary files
RUN zypper -n clean -a; \\
    # LOGCLEAN #
# set the day of last password change to empty
RUN sed -i 's/^\\([^:]*:[^:]*:\\)[^:]*\\(:.*\\)$/\\1\\2/' /etc/shadow

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.dummy-sle-repo
LABEL org.opencontainers.image.authors="https://github.com/SUSE/bci/discussions"
LABEL org.opencontainers.image.title="Dummy Third Party Image for SUSE Linux Enterprise Server 15 SP7"
LABEL org.opencontainers.image.description="Dummy Third Party Image container based on the SUSE Linux Enterprise Base Container Image."
LABEL org.opencontainers.image.version="1"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="1-%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/dummy-sle-repo:1-%RELEASE%"
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

SLE_REPO_RENDERED = """[dummy-sle-repo]
name=dummy-sle-repo
baseurl=https://packages.example.com/sles/15.7/
enabled=1
gpgcheck=1
gpgkey=https://packages.example.com/keys/repo.asc
"""

OPENSUSE_REPO_RENDERED = """[dummy-opensuse-repo]
name=dummy-opensuse-repo
baseurl=https://packages.example.org/opensuse/15.7/
enabled=1
gpgcheck=1
gpgkey=https://packages.example.org/keys/repo.asc
"""

KEY_FETCH_REPO_RENDERED = """[sle]
name=sle
baseurl=https://packages.example.com/sles/15.7/
enabled=1
gpgcheck=1
gpgkey=https://packages.example.com/keys/repo.asc
"""


def test_single_third_party_repo_template():
    """Test a single third party repositories."""
    image = DummyThirdPartyImage(
        tag_version="1",
        version="1",
        os_version=OsVersion.SP7,
        name="dummy-sle-repo",
        pretty_name="Dummy Third Party Image",
        is_latest=True,
        package_name="dummy-sle-repo",
        exclusive_arch=[Arch.X86_64, Arch.AARCH64],
        package_list=["wget"],
        third_party_repos=[
            ThirdPartyRepo(
                name="sle",
                url="https://packages.example.com/sles/15.7/",
                key="GPGKEY",
                key_url="https://packages.example.com/keys/repo.asc",
                repo_name="dummy-sle-repo",
                repo_filename="dummy-sle-repo.repo",
                key_filename="dummy-sle-repo.gpg.key",
            ),
        ],
        third_party_package_list=[
            "dummy-sle-pkg-1",
            "dummy-sle-pkg-3",
            "dummy-sle-pkg-2",
            "dummy-sle-pkg-5",
            "dummy-sle-pkg-4",
        ],
    )

    with patch(
        "bci_build.repomdparser.requests.get", side_effect=fake_repo_and_key_get
    ):
        image.prepare_template()

    rendered = DOCKERFILE_TEMPLATE.render(
        image=image,
        INFOHEADER="# Copyright",
        DOCKERFILE_RUN="RUN",
        LOG_CLEAN="# LOGCLEAN #",
        BUILD_FLAVOR=image.build_flavor,
    )

    repo = image.third_party_repos[0]
    assert repo.name == "sle"
    assert repo.url == "https://packages.example.com/sles/15.7/"
    assert repo.key == "GPGKEY"
    assert repo.key_url == "https://packages.example.com/keys/repo.asc"
    assert repo.arch is None
    assert repo.repo_name == "dummy-sle-repo"
    assert repo.repo_filename == "dummy-sle-repo.repo"
    assert repo.key_filename == "dummy-sle-repo.gpg.key"

    assert rendered == DOCKERFILE_RENDERED_SINGLE

    assert image.extra_files.get("sle.gpg.key") == "GPGKEY"
    assert image.extra_files.get("sle.repo") == SLE_REPO_RENDERED


def test_multiple_third_party_repo_template():
    """Test multiple third party repositories."""
    image = DummyThirdPartyImage(
        tag_version="1",
        version="1",
        os_version=OsVersion.SP7,
        name="dummy-sle-repo",
        pretty_name="Dummy Third Party Image",
        is_latest=True,
        package_name="dummy-sle-repo",
        exclusive_arch=[Arch.X86_64, Arch.AARCH64],
        package_list=["wget"],
        third_party_repos=[
            ThirdPartyRepo(
                name="sle",
                url="https://packages.example.com/sles/15.7/",
                key="SLE-GPGKEY",
                key_url="https://packages.example.com/keys/repo.asc",
                repo_name="dummy-sle-repo",
                repo_filename="dummy-sle-repo.repo",
                key_filename="dummy-sle-repo.gpg.key",
            ),
            ThirdPartyRepo(
                name="opensuse",
                url="https://packages.example.org/opensuse/15.7/",
                key="OPENSUSE-GPGKEY",
                key_url="https://packages.example.org/keys/repo.asc",
                repo_name="dummy-opensuse-repo",
                repo_filename="dummy-opensuse-repo.repo",
                key_filename="dummy-opensuse-repo.gpg.key",
            ),
        ],
        third_party_package_list=[
            "dummy-sle-pkg-1",
            "dummy-opensuse-pkg-3",
            "dummy-sle-pkg-2",
            "dummy-opensuse-pkg-5",
            "dummy-sle-pkg-4",
        ],
    )

    with patch(
        "bci_build.repomdparser.requests.get", side_effect=fake_repo_and_key_get
    ):
        image.prepare_template()

    rendered = DOCKERFILE_TEMPLATE.render(
        image=image,
        INFOHEADER="# Copyright",
        DOCKERFILE_RUN="RUN",
        LOG_CLEAN="# LOGCLEAN #",
        BUILD_FLAVOR=image.build_flavor,
    )

    repo = image.third_party_repos[0]
    assert repo.name == "sle"
    assert repo.url == "https://packages.example.com/sles/15.7/"
    assert repo.key == "SLE-GPGKEY"
    assert repo.key_url == "https://packages.example.com/keys/repo.asc"
    assert repo.arch is None
    assert repo.repo_name == "dummy-sle-repo"
    assert repo.repo_filename == "dummy-sle-repo.repo"
    assert repo.key_filename == "dummy-sle-repo.gpg.key"

    repo = image.third_party_repos[1]
    assert repo.name == "opensuse"
    assert repo.url == "https://packages.example.org/opensuse/15.7/"
    assert repo.key == "OPENSUSE-GPGKEY"
    assert repo.key_url == "https://packages.example.org/keys/repo.asc"
    assert repo.arch is None
    assert repo.repo_name == "dummy-opensuse-repo"
    assert repo.repo_filename == "dummy-opensuse-repo.repo"
    assert repo.key_filename == "dummy-opensuse-repo.gpg.key"

    assert rendered == DOCKERFILE_RENDERED_MULTI

    assert image.extra_files.get("sle.gpg.key") == "SLE-GPGKEY"
    assert image.extra_files.get("sle.repo") == SLE_REPO_RENDERED

    assert image.extra_files.get("opensuse.gpg.key") == "OPENSUSE-GPGKEY"
    assert image.extra_files.get("opensuse.repo") == OPENSUSE_REPO_RENDERED


def test_third_party_key_fetch():
    """Test that the GPG key is fetched from the configured url."""
    image = DummyThirdPartyImage(
        tag_version="1",
        version="1",
        os_version=OsVersion.SP7,
        name="dummy-sle-repo",
        pretty_name="Dummy Third Party Image",
        is_latest=True,
        package_name="dummy-sle-repo",
        exclusive_arch=[Arch.X86_64, Arch.AARCH64],
        package_list=["wget"],
        third_party_repos=[
            ThirdPartyRepo(
                name="sle",
                url="https://packages.example.com/sles/15.7/",
                key_url="https://packages.example.com/keys/repo.asc",
            ),
        ],
        third_party_package_list=[
            "dummy-sle-pkg-1",
            "dummy-sle-pkg-3",
            "dummy-sle-pkg-2",
            "dummy-sle-pkg-5",
            "dummy-sle-pkg-4",
        ],
    )

    with patch(
        "bci_build.package.thirdparty.requests.get", side_effect=fake_repo_and_key_get
    ):
        image.prepare_template()

    repo = image.third_party_repos[0]
    assert repo.name == "sle"
    assert repo.url == "https://packages.example.com/sles/15.7/"
    assert repo.key == "GPGKEY"
    assert repo.key_url == "https://packages.example.com/keys/repo.asc"
    assert repo.arch is None
    assert repo.repo_name == "sle"
    assert repo.repo_filename == "sle.repo"
    assert repo.key_filename == "sle.gpg.key"

    rendered = DOCKERFILE_TEMPLATE.render(
        image=image,
        INFOHEADER="# Copyright",
        DOCKERFILE_RUN="RUN",
        LOG_CLEAN="# LOGCLEAN #",
        BUILD_FLAVOR=image.build_flavor,
    )

    assert rendered == DOCKERFILE_RENDERED_KEY_FETCH

    assert image.extra_files.get("sle.gpg.key") == "GPGKEY"
    assert image.extra_files.get("sle.repo") == KEY_FETCH_REPO_RENDERED
