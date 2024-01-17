from datetime import date

import pytest
from bci_build.package import Arch
from bci_build.package import LanguageStackContainer
from bci_build.package import OsVersion
from bci_build.templates import DOCKERFILE_TEMPLATE
from bci_build.templates import KIWI_TEMPLATE


@pytest.mark.parametrize(
    "dockerfile,kiwi_xml,image",
    [
        (
            """# SPDX-License-Identifier: MIT
# Copyright header

#!BuildTag: bci/test:28
#!BuildTag: bci/test:28-%RELEASE%
#!BuildName: bci-test-28
#!BuildVersion: 15.4.28
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.title="SLE BCI Test"
LABEL org.opencontainers.image.description="Test container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="28"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL%/README.md"
LABEL org.opensuse.reference="registry.suse.com/bci/test:28-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.supportlevel.until="2024-02-01"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
COPY test.el .
RUN emacs -Q --batch test.el
""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: bci/test:28 bci/test:28-%RELEASE% -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="6.5" name="test-28-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>SUSE LLC</author>
    <contact>https://www.suse.com/</contact>
    <specification>SLE BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/suse/sle15#15.4">
      <containerconfig
          name="bci/test"
          tag="28"
          maintainer="SUSE LLC (https://www.suse.com/)"
          additionaltags="28-%RELEASE%">
        <labels>
          <suse_label_helper:add_prefix prefix="com.suse.bci.test">
            <label name="org.opencontainers.image.title" value="SLE BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the SLE Base Container Image."/>
            <label name="org.opencontainers.image.version" value="28"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="SUSE LLC"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.suse.com/products/server/"/>
            <label name="io.artifacthub.package.readme-url" value="%SOURCEURL%/README.md"/>
            <label name="org.opensuse.reference" value="registry.suse.com/bci/test:28-%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="techpreview"/>
            <label name="com.suse.supportlevel.until" value="2024-02-01"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="released"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"/>
          </suse_label_helper:add_prefix>
        </labels>
      </containerconfig>
    </type>
    <version>15.4.0</version>
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
            LanguageStackContainer(
                name="test",
                pretty_name="Test",
                supported_until=date(2024, 2, 1),
                package_list=["gcc", "emacs"],
                package_name="test-image",
                os_version=OsVersion.SP4,
                version="28",
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
FROM suse/sle15:15.5

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.title="SLE BCI Test"
LABEL org.opencontainers.image.description="Test container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="%%emacs_ver%%"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL%/README.md"
LABEL org.opensuse.reference="registry.suse.com/bci/test:%%emacs_ver%%-1.%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: bci/test:stable bci/test:stable-1.%RELEASE% bci/test:%%emacs_ver%% bci/test:%%emacs_ver%%-1.%RELEASE% -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="6.5" name="test-%%emacs_ver%%-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>SUSE LLC</author>
    <contact>https://www.suse.com/</contact>
    <specification>SLE BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/suse/sle15#15.5">
      <containerconfig
          name="bci/test"
          tag="stable"
          maintainer="SUSE LLC (https://www.suse.com/)"
          additionaltags="stable-1.%RELEASE%,%%emacs_ver%%,%%emacs_ver%%-1.%RELEASE%">
        <labels>
          <suse_label_helper:add_prefix prefix="com.suse.bci.test">
            <label name="org.opencontainers.image.title" value="SLE BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the SLE Base Container Image."/>
            <label name="org.opencontainers.image.version" value="%%emacs_ver%%"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="SUSE LLC"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.suse.com/products/server/"/>
            <label name="io.artifacthub.package.readme-url" value="%SOURCEURL%/README.md"/>
            <label name="org.opensuse.reference" value="registry.suse.com/bci/test:%%emacs_ver%%-1.%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="techpreview"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="released"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"/>
          </suse_label_helper:add_prefix>
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
            LanguageStackContainer(
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

#!BuildTag: bci/test:28
#!BuildTag: bci/test:28-%RELEASE%
#!BuildName: bci-test-28
#!BuildVersion: 15.4.28
FROM suse/sle15:15.4

MAINTAINER SUSE LLC (https://www.suse.com/)

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=com.suse.bci.test
LABEL org.opencontainers.image.title="SLE BCI Test"
LABEL org.opencontainers.image.description="Test container based on the SLE Base Container Image."
LABEL org.opencontainers.image.version="28"
LABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="SUSE LLC"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL io.artifacthub.package.readme-url="%SOURCEURL%/README.md"
LABEL org.opensuse.reference="registry.suse.com/bci/test:28-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="techpreview"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"
LABEL com.suse.release-stage="released"
# endlabelprefix

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
""",
            """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright header-->
<!-- OBS-AddTag: bci/test:28 bci/test:28-%RELEASE% -->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="6.5" name="test-28-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>SUSE LLC</author>
    <contact>https://www.suse.com/</contact>
    <specification>SLE BCI Test Container Image</specification>
  </description>
  <preferences>
    <type image="docker" derived_from="obsrepositories:/suse/sle15#15.4">
      <containerconfig
          name="bci/test"
          tag="28"
          maintainer="SUSE LLC (https://www.suse.com/)"
          additionaltags="28-%RELEASE%">
        <labels>
          <suse_label_helper:add_prefix prefix="com.suse.bci.test">
            <label name="org.opencontainers.image.title" value="SLE BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the SLE Base Container Image."/>
            <label name="org.opencontainers.image.version" value="28"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="SUSE LLC"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.suse.com/products/server/"/>
            <label name="io.artifacthub.package.readme-url" value="%SOURCEURL%/README.md"/>
            <label name="org.opensuse.reference" value="registry.suse.com/bci/test:28-%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="techpreview"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="released"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle#suse-linux-enterprise-server-15"/>
          </suse_label_helper:add_prefix>
        </labels>
      </containerconfig>
    </type>
    <version>15.4.0</version>
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
            LanguageStackContainer(
                name="test",
                pretty_name="Test",
                package_list=["gcc", "emacs"],
                package_name="emacs-image",
                os_version=OsVersion.SP4,
                version="28",
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

MAINTAINER invalid@suse.com

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix=org.opensuse.bci.test
LABEL org.opencontainers.image.title="openSUSE Tumbleweed BCI Test"
LABEL org.opencontainers.image.description="Test container based on the openSUSE Tumbleweed Base Container Image."
LABEL org.opencontainers.image.version="28.2"
LABEL org.opencontainers.image.url="https://www.opensuse.org"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="openSUSE Project"
LABEL org.opencontainers.image.source="%SOURCEURL%"
LABEL io.artifacthub.package.readme-url="https://raw.githubusercontent.com/SUSE/BCI-dockerfile-generator/Tumbleweed/test-image/README.md"
LABEL io.artifacthub.package.logo-url="https://suse.com/assets/emacs-logo.svg"
LABEL org.opensuse.reference="registry.opensuse.org/opensuse/bci/test:28.2-%RELEASE%"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL org.opensuse.lifecycle-url="https://en.opensuse.org/Lifetime"
LABEL org.opensuse.release-stage="released"

# endlabelprefix
LABEL emacs_version="28"
LABEL GCC_version="15"

RUN zypper -n in --no-recommends gcc emacs; zypper -n clean; rm -rf /var/log/*
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
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="6.5" name="test-28.2-image" xmlns:suse_label_helper="com.suse.label_helper">
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
          maintainer="invalid@suse.com"
          additionaltags="28.2-%RELEASE%,28,28-%RELEASE%,latest">
        <labels>
          <suse_label_helper:add_prefix prefix="org.opensuse.bci.test">
            <label name="org.opencontainers.image.title" value="openSUSE Tumbleweed BCI Test"/>
            <label name="org.opencontainers.image.description" value="Test container based on the openSUSE Tumbleweed Base Container Image."/>
            <label name="org.opencontainers.image.version" value="28.2"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="openSUSE Project"/>
            <label name="org.opencontainers.image.source" value="%SOURCEURL%"/>
            <label name="org.opencontainers.image.url" value="https://www.opensuse.org"/>
            <label name="io.artifacthub.package.readme-url" value="https://raw.githubusercontent.com/SUSE/BCI-dockerfile-generator/Tumbleweed/test-image/README.md"/>
            <label name="io.artifacthub.package.logo-url" value="https://suse.com/assets/emacs-logo.svg"/>
            <label name="org.opensuse.reference" value="registry.opensuse.org/opensuse/bci/test:28.2-%RELEASE%"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>

            <label name="org.opensuse.release-stage" value="released"/>
            <label name="org.opensuse.lifecycle-url" value="https://en.opensuse.org/Lifetime"/>
            <label name="emacs_version" value="28"/>
            <label name="GCC_version" value="15"/>
          </suse_label_helper:add_prefix>
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

</image>""".replace(
                "__CURRENT_YEAR__", str(date.today().year)
            ),
            LanguageStackContainer(
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
    dockerfile: str, kiwi_xml: str, image: LanguageStackContainer
) -> None:
    assert (
        DOCKERFILE_TEMPLATE.render(
            DOCKERFILE_RUN="RUN", image=image, INFOHEADER="# Copyright header"
        )
        == dockerfile
    )
    assert KIWI_TEMPLATE.render(image=image, INFOHEADER="Copyright header") == kiwi_xml
