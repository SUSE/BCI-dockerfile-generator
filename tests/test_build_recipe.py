from datetime import date

import pytest

from bci_build.package import Arch
from bci_build.package import BuildType
from bci_build.package import DevelopmentContainer
from bci_build.package import OsContainer
from bci_build.package import OsVersion
from bci_build.package import Package
from bci_build.package import PackageType
from bci_build.package import SupportLevel
from bci_build.templates import DOCKERFILE_TEMPLATE
from bci_build.templates import KIWI_TEMPLATE


@pytest.mark.parametrize(
    "dockerfile,kiwi_xml,image",
    [
        (
            """# SPDX-License-Identifier: MIT
# Copyright header

#!BuildTag: bci/test:27
#!BuildTag: bci/test:27-%RELEASE%
#!BuildName: bci-test-27
#!BuildVersion: 15.6.27
FROM bci/bci-base:15.6

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.authors="SUSE LLC (https://www.suse.com/)"
LABEL org.opencontainers.image.title="SLE BCI Test"
LABEL org.opencontainers.image.description="Test container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="27"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="27-%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/test:27-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.supportlevel.until="2024-02-01"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix
LABEL org.opencontainers.image.base.name="%BASE_SLE15_REFERENCE%"
LABEL org.opencontainers.image.base.digest="%BASE_SLE15_DIGEST%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL%/README.md"

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; ##LOGCLEAN##
COPY test.el .
RUN emacs -Q --batch test.el
""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: bci/test:27 bci/test:27-%RELEASE% -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="7.4" name="test-27-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>SUSE LLC</author>
    <contact>https://www.suse.com/</contact>
    <specification>SLE BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/bci/bci-base#15.6">
      <containerconfig
          name="bci/test"
          tag="27"
          additionaltags="27-%RELEASE%">
        <labels>
          <suse_label_helper:add_prefix prefix="com.suse.bci.test">
            <label name="org.opencontainers.image.authors" value="SUSE LLC (https://www.suse.com/)"/>
            <label name="org.opencontainers.image.title" value="SLE BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the SLE Base Container Image."/>
            <label name="org.opencontainers.image.version" value="27"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="SUSE LLC"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.suse.com/products/base-container-images/"/>
            <label name="org.opencontainers.image.ref.name" value="27-%RELEASE%"/>
            <label name="org.opensuse.reference" value="registry.suse.com/bci/test:27-%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="techpreview"/>
            <label name="com.suse.supportlevel.until" value="2024-02-01"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="released"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"/>
          </suse_label_helper:add_prefix>
          <label name="org.opencontainers.image.base.name" value="%BASE_SLE15_REFERENCE%"/>
          <label name="org.opencontainers.image.base.digest" value="%BASE_SLE15_DIGEST%"/>
          <label name="io.artifacthub.package.readme-url" value="%SOURCEURL%/README.md"/>
        </labels>
      </containerconfig>
    </type>
    <version>15.6.0</version>
    <packagemanager>zypper</packagemanager>
    <rpm-check-signatures>false</rpm-check-signatures>
    <rpm-excludedocs>true</rpm-excludedocs>
  </preferences>
  <repository type="rpm-md">
    <source path="obsrepositories:/"/>
  </repository>
  <packages type="image">
    <package name="gcc"/>
    <package name="emacs"/>
  </packages>

</image>""",
            DevelopmentContainer(
                name="test",
                pretty_name="Test",
                supported_until=date(2024, 2, 1),
                package_list=["gcc", "emacs"],
                package_name="test-image",
                os_version=OsVersion.SP6,
                version="27",
                custom_end="""COPY test.el .
RUN emacs -Q --batch test.el
""",
            ),
        ),
        (
            """# SPDX-License-Identifier: MIT
# Copyright header

#!BuildTag: bci/test:stable
#!BuildTag: bci/test:stable-1.%RELEASE%
#!BuildTag: bci/test:%%emacs_ver%%
#!BuildTag: bci/test:%%emacs_ver%%-1.%RELEASE%
#!BuildName: bci-test-stable
#!BuildVersion: 15.5
FROM bci/bci-base:15.5

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.authors="SUSE LLC (https://www.suse.com/)"
LABEL org.opencontainers.image.title="SLE BCI Test"
LABEL org.opencontainers.image.description="Test container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%emacs_ver%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="%%emacs_ver%%-1.%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/test:%%emacs_ver%%-1.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix
LABEL org.opencontainers.image.base.name="%BASE_SLE15_REFERENCE%"
LABEL org.opencontainers.image.base.digest="%BASE_SLE15_DIGEST%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL%/README.md"

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; ##LOGCLEAN##
""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: bci/test:stable bci/test:stable-1.%RELEASE% bci/test:%%emacs_ver%% bci/test:%%emacs_ver%%-1.%RELEASE% -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="7.4" name="test-%%emacs_ver%%-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>SUSE LLC</author>
    <contact>https://www.suse.com/</contact>
    <specification>SLE BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/bci/bci-base#15.5">
      <containerconfig
          name="bci/test"
          tag="stable"
          additionaltags="stable-1.%RELEASE%,%%emacs_ver%%,%%emacs_ver%%-1.%RELEASE%">
        <labels>
          <suse_label_helper:add_prefix prefix="com.suse.bci.test">
            <label name="org.opencontainers.image.authors" value="SUSE LLC (https://www.suse.com/)"/>
            <label name="org.opencontainers.image.title" value="SLE BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the SLE Base Container Image."/>
            <label name="org.opencontainers.image.version" value="%%emacs_ver%%"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="SUSE LLC"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.suse.com/products/base-container-images/"/>
            <label name="org.opencontainers.image.ref.name" value="%%emacs_ver%%-1.%RELEASE%"/>
            <label name="org.opensuse.reference" value="registry.suse.com/bci/test:%%emacs_ver%%-1.%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="techpreview"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="released"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"/>
          </suse_label_helper:add_prefix>
          <label name="org.opencontainers.image.base.name" value="%BASE_SLE15_REFERENCE%"/>
          <label name="org.opencontainers.image.base.digest" value="%BASE_SLE15_DIGEST%"/>
          <label name="io.artifacthub.package.readme-url" value="%SOURCEURL%/README.md"/>
        </labels>
      </containerconfig>
    </type>
    <version>15.5.0</version>
    <packagemanager>zypper</packagemanager>
    <rpm-check-signatures>false</rpm-check-signatures>
    <rpm-excludedocs>true</rpm-excludedocs>
  </preferences>
  <repository type="rpm-md">
    <source path="obsrepositories:/"/>
  </repository>
  <packages type="image">
    <package name="gcc"/>
    <package name="emacs"/>
  </packages>

</image>""",
            DevelopmentContainer(
                name="test",
                pretty_name="Test",
                package_list=["gcc", "emacs"],
                package_name="test-image",
                stability_tag="stable",
                os_version=OsVersion.SP5,
                version="%%emacs_ver%%",
            ),
        ),
        (
            """# SPDX-License-Identifier: MIT
# Copyright header

#!BuildTag: bci/test:29
#!BuildTag: bci/test:29-%RELEASE%
#!BuildName: bci-test-29
#!BuildVersion: 15.6.29
FROM bci/bci-base:15.6

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.authors="SUSE LLC (https://www.suse.com/)"
LABEL org.opencontainers.image.title="SLE BCI Test"
LABEL org.opencontainers.image.description="Test container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="29"
LABEL org.opencontainers.image.url="https://www.suse.com/products/base-container-images/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="29-%RELEASE%"
LABEL org.opensuse.reference="registry.suse.com/bci/test:29-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix
LABEL org.opencontainers.image.base.name="%BASE_SLE15_REFERENCE%"
LABEL org.opencontainers.image.base.digest="%BASE_SLE15_DIGEST%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL%/README.md"

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; ##LOGCLEAN##
USER emacs""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: bci/test:29 bci/test:29-%RELEASE% -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="7.4" name="test-29-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>SUSE LLC</author>
    <contact>https://www.suse.com/</contact>
    <specification>SLE BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/bci/bci-base#15.6">
      <containerconfig
          name="bci/test"
          tag="29"
          additionaltags="29-%RELEASE%"
          user="emacs">
        <labels>
          <suse_label_helper:add_prefix prefix="com.suse.bci.test">
            <label name="org.opencontainers.image.authors" value="SUSE LLC (https://www.suse.com/)"/>
            <label name="org.opencontainers.image.title" value="SLE BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the SLE Base Container Image."/>
            <label name="org.opencontainers.image.version" value="29"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="SUSE LLC"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.suse.com/products/base-container-images/"/>
            <label name="org.opencontainers.image.ref.name" value="29-%RELEASE%"/>
            <label name="org.opensuse.reference" value="registry.suse.com/bci/test:29-%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="techpreview"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="released"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"/>
          </suse_label_helper:add_prefix>
          <label name="org.opencontainers.image.base.name" value="%BASE_SLE15_REFERENCE%"/>
          <label name="org.opencontainers.image.base.digest" value="%BASE_SLE15_DIGEST%"/>
          <label name="io.artifacthub.package.readme-url" value="%SOURCEURL%/README.md"/>
        </labels>
      </containerconfig>
    </type>
    <version>15.6.0</version>
    <packagemanager>zypper</packagemanager>
    <rpm-check-signatures>false</rpm-check-signatures>
    <rpm-excludedocs>true</rpm-excludedocs>
  </preferences>
  <repository type="rpm-md">
    <source path="obsrepositories:/"/>
  </repository>
  <packages type="image">
    <package name="gcc"/>
    <package name="emacs"/>
  </packages>

</image>""",
            DevelopmentContainer(
                name="test",
                pretty_name="Test",
                package_list=["gcc", "emacs"],
                package_name="emacs-image",
                os_version=OsVersion.SP6,
                entrypoint_user="emacs",
                version="29",
            ),
        ),
        (
            """# SPDX-License-Identifier: BSD
# Copyright header
#!ExclusiveArch: x86_64 s390x
#!BuildTag: opensuse/bci/test:28.2
#!BuildTag: opensuse/bci/test:28.2-%RELEASE%
#!BuildTag: opensuse/bci/test:28
#!BuildTag: opensuse/bci/test:28-%RELEASE%
#!BuildTag: opensuse/bci/test:latest
#!BuildTag: opensuse/bci/emacs:28.2
#!BuildTag: opensuse/bci/emacs:28.2-%RELEASE%
#!BuildTag: opensuse/bci/emacs:28
#!BuildTag: opensuse/bci/emacs:28-%RELEASE%
#!BuildTag: opensuse/bci/emacs:latest

FROM suse/base:18

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.bci.test
LABEL org.opencontainers.image.authors="invalid@suse.com"
LABEL org.opencontainers.image.title="openSUSE Tumbleweed BCI Test"
LABEL org.opencontainers.image.description="Test container based on the openSUSE Tumbleweed Base Container Image."
LABEL org.opencontainers.image.version="28.2"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL org.opencontainers.image.ref.name="28.2-%RELEASE%"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/bci/test:28.2-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL org.opensuse.lifecycle-url="https://en.opensuse.org/Lifetime#openSUSE_BCI"
LABEL org.opensuse.release-stage="released"
# endlabelprefix
LABEL org.opencontainers.image.base.name="%BASE_BASE_REFERENCE%"
LABEL org.opencontainers.image.base.digest="%BASE_BASE_DIGEST%"
LABEL io.artifacthub.package.readme-url="https://raw.githubusercontent.com/SUSE/BCI-dockerfile-generator/Tumbleweed/test-image/README.md"
LABEL io.artifacthub.package.logo-url="https://suse.com/assets/emacs-logo.svg"
LABEL emacs_version="28"
LABEL GCC_version="15"

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; ##LOGCLEAN##
ENV EMACS_VERSION="28"
ENV GPP_path="/usr/bin/g++"

ENTRYPOINT ["/usr/bin/emacs"]
CMD ["/usr/bin/gcc"]
EXPOSE 22 1111
RUN emacs -Q --batch
VOLUME /bin/ /usr/bin/""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: BSD -->
<!-- Copyright header-->
<!-- OBS-AddTag: opensuse/bci/test:28.2 opensuse/bci/test:28.2-%RELEASE% opensuse/bci/test:28 opensuse/bci/test:28-%RELEASE% opensuse/bci/test:latest opensuse/bci/emacs:28.2 opensuse/bci/emacs:28.2-%RELEASE% opensuse/bci/emacs:28 opensuse/bci/emacs:28-%RELEASE% opensuse/bci/emacs:latest -->
<!-- OBS-ExclusiveArch: x86_64 s390x -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="7.4" name="test-28.2-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>openSUSE Project</author>
    <contact>https://www.suse.com/</contact>
    <specification>openSUSE Tumbleweed BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/suse/base#18">
      <containerconfig
          name="opensuse/bci/test"
          tag="28.2"
          additionaltags="28.2-%RELEASE%,28,28-%RELEASE%,latest">
        <labels>
          <suse_label_helper:add_prefix prefix="org.opensuse.bci.test">
            <label name="org.opencontainers.image.authors" value="invalid@suse.com"/>
            <label name="org.opencontainers.image.title" value="openSUSE Tumbleweed BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the openSUSE Tumbleweed Base Container Image."/>
            <label name="org.opencontainers.image.version" value="28.2"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="openSUSE Project"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.opensuse.org"/>
            <label name="org.opencontainers.image.ref.name" value="28.2-%RELEASE%"/>
            <label name="org.opensuse.reference" value="registry.opensuse.org/opensuse/bci/test:28.2-%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="org.opensuse.release-stage" value="released"/>
            <label name="org.opensuse.lifecycle-url" value="https://en.opensuse.org/Lifetime#openSUSE_BCI"/>
            <label name="emacs_version" value="28"/>
            <label name="GCC_version" value="15"/>
          </suse_label_helper:add_prefix>
          <label name="org.opencontainers.image.base.name" value="%BASE_BASE_REFERENCE%"/>
          <label name="org.opencontainers.image.base.digest" value="%BASE_BASE_DIGEST%"/>
          <label name="io.artifacthub.package.readme-url" value="https://raw.githubusercontent.com/SUSE/BCI-dockerfile-generator/Tumbleweed/test-image/README.md"/>
          <label name="io.artifacthub.package.logo-url" value="https://suse.com/assets/emacs-logo.svg"/>
        </labels>
        <subcommand execute="/usr/bin/gcc"/>
        <entrypoint execute="/usr/bin/emacs"/>
        <volumes>
          <volume name="/bin/" />
          <volume name="/usr/bin/" />
        </volumes>
        <expose>
          <port number="22" />
          <port number="1111" />
        </expose>
        <environment>
          <env name="EMACS_VERSION" value="28"/>
          <env name="GPP_path" value="/usr/bin/g++"/>
        </environment>

      </containerconfig>
    </type>
    <version>__CURRENT_YEAR__</version>
    <packagemanager>zypper</packagemanager>
    <rpm-check-signatures>false</rpm-check-signatures>
    <rpm-excludedocs>true</rpm-excludedocs>
  </preferences>
  <repository type="rpm-md">
    <source path="obsrepositories:/"/>
  </repository>
  <packages type="image">
    <package name="gcc"/>
    <package name="emacs"/>
  </packages>

</image>""".replace("__CURRENT_YEAR__", str(date.today().year)),
            DevelopmentContainer(
                exclusive_arch=[Arch.X86_64, Arch.S390X],
                name="test",
                pretty_name="Test",
                package_list=["gcc", "emacs"],
                package_name="test-image",
                os_version=OsVersion.TUMBLEWEED,
                is_latest=True,
                from_image="suse/base:18",
                entrypoint=["/usr/bin/emacs"],
                cmd=["/usr/bin/gcc"],
                maintainer="invalid@suse.com",
                logo_url="https://suse.com/assets/emacs-logo.svg",
                volumes=["/bin/", "/usr/bin/"],
                # does nothing on TW
                supported_until=date(2024, 2, 1),
                exposes_tcp=[22, 1111],
                license="BSD",
                version="28.2",
                additional_names=["emacs"],
                additional_versions=["28"],
                extra_labels={"emacs_version": "28", "GCC_version": "15"},
                env={"EMACS_VERSION": 28, "GPP_path": "/usr/bin/g++"},
                custom_end="""RUN emacs -Q --batch""",
            ),
        ),
    ],
)
def test_build_recipe_templates(
    dockerfile: str, kiwi_xml: str, image: DevelopmentContainer
) -> None:
    assert (
        DOCKERFILE_TEMPLATE.render(
            DOCKERFILE_RUN="RUN",
            image=image,
            INFOHEADER="# Copyright header",
            LOG_CLEAN="##LOGCLEAN##",
        )
        == dockerfile
    )
    assert KIWI_TEMPLATE.render(image=image, INFOHEADER="Copyright header") == kiwi_xml


@pytest.mark.parametrize(
    "kiwi_xml,image",
    [
        (
            """<?xml version="1.0" encoding="utf-8"?>\n<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: opensuse/bci/bci-test:%OS_VERSION_ID_SP% opensuse/bci/bci-test:%OS_VERSION_ID_SP%.%RELEASE% opensuse/bci/bci-test:latest -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="7.4" name="test-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>openSUSE Project</author>
    <contact>https://www.suse.com/</contact>
    <specification>openSUSE Tumbleweed BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker">
      <containerconfig
          name="opensuse/bci/bci-test"
          tag="%OS_VERSION_ID_SP%"
          additionaltags="%OS_VERSION_ID_SP%.%RELEASE%,latest">
        <labels>
          <suse_label_helper:add_prefix prefix="org.opensuse.bci.test">
            <label name="org.opencontainers.image.authors" value="openSUSE (https://www.opensuse.org/)"/>
            <label name="org.opencontainers.image.title" value="openSUSE Tumbleweed BCI Test"/>
            <label name="org.opencontainers.image.description" value="A test environment for containers."/>
            <label name="org.opencontainers.image.version" value="%OS_VERSION_ID_SP%.%RELEASE%"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="openSUSE Project"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.opensuse.org"/>
            <label name="org.opencontainers.image.ref.name" value="%OS_VERSION_ID_SP%.%RELEASE%"/>
            <label name="org.opensuse.reference" value="registry.opensuse.org/opensuse/bci/bci-test:%OS_VERSION_ID_SP%.%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="org.opensuse.release-stage" value="released"/>
            <label name="org.opensuse.lifecycle-url" value="https://en.opensuse.org/Lifetime#openSUSE_BCI"/>
          </suse_label_helper:add_prefix>
          <label name="io.artifacthub.package.readme-url" value="https://raw.githubusercontent.com/SUSE/BCI-dockerfile-generator/Tumbleweed/test-image/README.md"/>
          <label name="io.artifacthub.package.logo-url" value="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg"/>
        </labels>
      </containerconfig>
    </type>
    <version>__CURRENT_YEAR__</version>
    <packagemanager>zypper</packagemanager>
    <rpm-check-signatures>false</rpm-check-signatures>
    <rpm-excludedocs>true</rpm-excludedocs>
  </preferences>
  <repository type="rpm-md">
    <source path="obsrepositories:/"/>
  </repository>
  <packages type="bootstrap">
    <package name="bash"/>
    <package name="ca-certificates-mozilla-prebuilt"/>
    <package name="coreutils"/>
    <package name="skelcd-EULA-test"/>
    <package name="Test-release"/>
  </packages>

</image>""".replace("__CURRENT_YEAR__", str(date.today().year)),
            OsContainer(
                name="test",
                os_version=OsVersion.TUMBLEWEED,
                support_level=SupportLevel.L3,
                package_name="test-image",
                logo_url="https://opensource.suse.com/bci/SLE_BCI_logomark_green.svg",
                is_latest=True,
                pretty_name=f"{OsVersion.TUMBLEWEED.pretty_os_version_no_dash} Test",
                custom_description="A test environment for containers.",
                from_image=None,
                build_recipe_type=BuildType.KIWI,
                package_list=[
                    Package(name, pkg_type=PackageType.BOOTSTRAP)
                    for name in (
                        "bash",
                        "ca-certificates-mozilla-prebuilt",
                        # ca-certificates-mozilla-prebuilt requires /bin/cp, which is otherwise not resolved…
                        "coreutils",
                    )
                    + tuple(("skelcd-EULA-test",))
                    + tuple(("Test-release",))
                ],
                # intentionally empty
                config_sh_script="""
""",
            ),
        ),
    ],
)
def test_os_build_recipe_templates(kiwi_xml: str, image: OsContainer) -> None:
    assert KIWI_TEMPLATE.render(image=image, INFOHEADER="Copyright header") == kiwi_xml
