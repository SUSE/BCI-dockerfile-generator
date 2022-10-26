from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.templates import DOCKERFILE_TEMPLATE


def test_dockerfile_template_without_env():
    assert (
        DOCKERFILE_TEMPLATE.render(
            DOCKERFILE_RUN="RUN",
            image=LanguageStackContainer(
                name="test",
                pretty_name="Test",
                package_list=["gcc", "emacs"],
                package_name="test-image",
                os_version=OsVersion.SP4,
                version="28",
                custom_end="""COPY test.el .
RUN emacs -Q --batch test.el
""",
            ),
        )
        == """# SPDX-License-Identifier: MIT
#!BuildTag: bci/test:28
#!BuildTag: bci/test:28-%RELEASE%
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.title="SLE BCI Test Container Image"
LABEL org.opencontainers.image.description="Test based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="28"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/test:28-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
COPY test.el .
RUN emacs -Q --batch test.el
"""
    )


def test_simple_dockerfile_template():
    assert (
        DOCKERFILE_TEMPLATE.render(
            DOCKERFILE_RUN="RUN",
            image=LanguageStackContainer(
                name="test",
                pretty_name="Test",
                package_list=["gcc", "emacs"],
                package_name="test-image",
                os_version=OsVersion.SP4,
                version="28",
            ),
        )
        == """# SPDX-License-Identifier: MIT
#!BuildTag: bci/test:28
#!BuildTag: bci/test:28-%RELEASE%
#!BuildVersion: 15.4
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.title="SLE BCI Test Container Image"
LABEL org.opencontainers.image.description="Test based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="28"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/test:28-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
"""
    )


def test_dockerfile_template():
    c = LanguageStackContainer(
        name="test",
        pretty_name="Test",
        package_list=["gcc", "emacs"],
        package_name="test-image",
        os_version=OsVersion.SP4,
        is_latest=True,
        from_image="suse/base:18",
        entrypoint=["/usr/bin/emacs"],
        cmd=["/usr/bin/gcc"],
        maintainer="invalid@suse.com",
        volumes=["/bin/", "/usr/bin/"],
        exposes_tcp=[22, 1111],
        license="BSD",
        version="28.2",
        additional_names=["emacs"],
        additional_versions=["28"],
        extra_labels={"emacs_version": "28", "GCC_version": "15"},
        env={"EMACS_VERSION": 28, "GPP_path": "/usr/bin/g++"},
        custom_end="""RUN emacs -Q --batch""",
    )
    assert (
        DOCKERFILE_TEMPLATE.render(image=c, DOCKERFILE_RUN="RUN")
        == """# SPDX-License-Identifier: BSD
#!BuildTag: bci/test:28.2
#!BuildTag: bci/test:latest
#!BuildTag: bci/test:28.2-%RELEASE%
#!BuildTag: bci/test:28
#!BuildTag: bci/emacs:28.2
#!BuildTag: bci/emacs:latest
#!BuildTag: bci/emacs:28.2-%RELEASE%
#!BuildTag: bci/emacs:28
#!BuildVersion: 15.4
FROM suse/base:18

MAINTAINER invalid@suse.com

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.title="SLE BCI Test Container Image"
LABEL org.opencontainers.image.description="Test based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="28.2"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opensuse.reference="registry.suse.com/bci/test:28.2-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="sle-bci"
LABEL com.suse.release-stage="released"
# endlabelprefix
LABEL emacs_version="28"
LABEL GCC_version="15"

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
ENV EMACS_VERSION="28"
ENV GPP_path="/usr/bin/g++"

ENTRYPOINT ["/usr/bin/emacs"]
CMD ["/usr/bin/gcc"]
VOLUME /bin/ /usr/bin/
EXPOSE 22 1111
RUN emacs -Q --batch"""
    )
