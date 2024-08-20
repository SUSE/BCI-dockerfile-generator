import pytest

from bci_build.package import OsVersion
from staging.project_setup import ProjectType
from staging.project_setup import generate_meta

_OSC_USERNAME = "foobar"


@pytest.mark.parametrize(
    "os_version, project_type, branch_name, expected_prj_name, expected_meta",
    [
        (
            OsVersion.SP6,
            ProjectType.DEVEL,
            None,
            "devel:BCI:SLE-15-SP6",
            """<project name="devel:BCI:SLE-15-SP6">
  <title>BCI Development project for SLE 15 SP6</title>
  <description>BCI Development project for SLE 15 SP6</description>
  <person userid="avicenzi" role="maintainer"/>
  <person userid="dirkmueller" role="maintainer"/>
  <person userid="dancermak" role="maintainer"/>
  <person userid="favogt" role="maintainer"/>
  <person userid="fcrozat" role="maintainer"/>
  <person userid="pvlasin" role="maintainer"/>

  <build>
    <enable/>
  </build>
  <publish>
    <enable/>
  </publish>
  <debuginfo>
    <enable/>
  </debuginfo>
  <repository name="standard">
    <path project="SUSE:Registry" repository="standard"/>
    <path project="SUSE:SLE-15-SP6:Update" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="images">
    <path project="devel:BCI:SLE-15-SP6" repository="containerfile"/>
    <path project="devel:BCI:SLE-15-SP6" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="helmcharts">
    <path project="devel:BCI:SLE-15-SP6" repository="standard"/>
    <arch>x86_64</arch>
  </repository>
  <repository name="containerfile">
    <path project="devel:BCI:SLE-15-SP6" repository="images"/>
    <path project="devel:BCI:SLE-15-SP6" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
</project>""",
        ),
        (
            OsVersion.SP5,
            ProjectType.CR,
            None,
            (prj_name := f"home:{_OSC_USERNAME}:BCI:CR:SLE-15-SP5"),
            f"""<project name="{prj_name}">
  <title>Continuous Rebuild project for SLE 15 SP5</title>
  <description>Continuous Rebuild project for SLE 15 SP5</description>
  <person userid="avicenzi" role="maintainer"/>
  <person userid="dancermak" role="maintainer"/>
  <person userid="{_OSC_USERNAME}" role="maintainer"/>

  <scmsync>https://github.com/SUSE/bci-dockerfile-generator#sle15-sp5</scmsync>
  <build>
    <enable/>
  </build>
  <publish>
    <enable/>
  </publish>
  <debuginfo>
    <enable/>
  </debuginfo>
  <repository name="standard">
    <path project="SUSE:Registry" repository="standard"/>
    <path project="SUSE:SLE-15-SP5:Update" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="images">
    <path project="{prj_name}" repository="containerfile"/>
    <path project="{prj_name}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="containerfile">
    <path project="{prj_name}" repository="images"/>
    <path project="{prj_name}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
</project>""",
        ),
        (
            OsVersion.SLE16_0,
            ProjectType.DEVEL,
            None,
            (prj_name := "devel:BCI:16.0"),
            f"""<project name="{prj_name}">
  <title>BCI Development project for SLE 16</title>
  <description>BCI Development project for SLE 16</description>
  <person userid="avicenzi" role="maintainer"/>
  <person userid="dirkmueller" role="maintainer"/>
  <person userid="dancermak" role="maintainer"/>
  <person userid="favogt" role="maintainer"/>
  <person userid="fcrozat" role="maintainer"/>
  <person userid="pvlasin" role="maintainer"/>

  <build>
    <enable/>
  </build>
  <publish>
    <enable/>
  </publish>
  <debuginfo>
    <enable/>
  </debuginfo>
  <repository name="standard">
    <path project="SUSE:SLFO:Products:SLES:16.0" repository="standard"/>
    <path project="SUSE:SLFO:Main:Build" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="images">
    <path project="{prj_name}" repository="containerfile"/>
    <path project="{prj_name}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="containerfile">
    <path project="{prj_name}" repository="images"/>
    <path project="{prj_name}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
</project>""",
        ),
        (
            OsVersion.SLE16_0,
            ProjectType.STAGING,
            (branch := "pr-404"),
            (prj_name := f"home:{_OSC_USERNAME}:BCI:Staging:16.0:{branch}"),
            f"""<project name="{prj_name}">
  <title>Staging project for SLE 16</title>
  <description>Staging project for https://github.com/SUSE/BCI-dockerfile-generator/tree/{branch} for SLE 16</description>
  <person userid="avicenzi" role="maintainer"/>
  <person userid="dancermak" role="maintainer"/>
  <person userid="{_OSC_USERNAME}" role="maintainer"/>

  <build>
    <enable/>
  </build>
  <publish>
    <enable/>
  </publish>
  <debuginfo>
    <enable/>
  </debuginfo>
  <repository name="standard">
    <path project="SUSE:SLFO:Products:SLES:16.0" repository="standard"/>
    <path project="SUSE:SLFO:Main:Build" repository="standard"/>
    <path project="devel:BCI:16.0" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="images">
    <path project="{prj_name}" repository="containerfile"/>
    <path project="{prj_name}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
  <repository name="containerfile">
    <path project="{prj_name}" repository="images"/>
    <path project="{prj_name}" repository="standard"/>
    <arch>x86_64</arch>
    <arch>aarch64</arch>
    <arch>s390x</arch>
    <arch>ppc64le</arch>
  </repository>
</project>""",
        ),
    ],
)
def test_project_meta(
    os_version: OsVersion,
    project_type: ProjectType,
    branch_name: str | None,
    expected_prj_name: str,
    expected_meta: str,
) -> None:
    prj_name, prj_meta = generate_meta(
        os_version, project_type, _OSC_USERNAME, branch_name
    )
    assert prj_name == expected_prj_name
    assert prj_meta == expected_meta
