import gzip
from unittest.mock import Mock
from unittest.mock import patch

from bci_build.repomdparser import RepoMDParser

_pkg_template = """<package type="rpm">
  <name>{pkg}</name>
  <arch>{arch}</arch>
  <version epoch="0" ver="{ver}" rel="1"/>
  <checksum>value</checksum>
  <summary>{pkg}</summary>
  <description>{pkg}</description>
  <location href="Packages/{pkg}-{ver}.{arch}.rpm"/>
</package>"""

_packages = ""

# add out of order to ensure RepoMDParser.parse sorts it properly
for pkg in [
    "dummy-pkg-3",
    "dummy-pkg-1",
    "dummy-pkg-4",
    "dummy-pkg-2",
    "dummy-pkg-6",
    "dummy-pkg-5",
]:
    for arch in ["x86_64", "aarch64"]:
        for ver in ["1.0.0", "1.0.2", "1.0.1"]:
            s = _pkg_template.format(pkg=pkg, arch=arch, ver=ver)
            _packages += s + "\n"

PRIMARY_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<metadata xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">
{_packages}
</metadata>
"""

REPO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo" xmlns:rpm="http://linux.duke.edu/metadata/rpm">
  <data type="primary">
    <location href="repodata/primary.xml.gz"/>
  </data>
  <data type="filelists">
    <location href="repodata/filelists.xml.gz"/>
  </data>
  <data type="other">
    <location href="repodata/other.xml.gz"/>
  </data>
</repomd>
"""


def fake_repo_get(url, *args, **kwargs):
    resp = Mock()
    resp.raise_for_status.return_value = None

    if url == "https://packages.example.com/sles/15.7/repodata/repomd.xml":
        resp.content = REPO_XML
        resp.status_code = 200
        return resp

    if url == "https://packages.example.com/sles/15.7/repodata/primary.xml.gz":
        resp.content = gzip.compress(PRIMARY_XML.encode("utf-8"))
        resp.status_code = 200
        return resp

    raise ValueError(f"Unexpected URL: {url}")


def test_parse():
    repo = RepoMDParser("https://packages.example.com/sles/15.7/")

    with patch("bci_build.repomdparser.requests.get", side_effect=fake_repo_get):
        repo.parse()

    assert repo.pkgs[0].name == "dummy-pkg-1"
    assert repo.pkgs[0].evr == ("", "1.0.2", "1")
    assert repo.pkgs[0].arch == "aarch64"

    assert repo.pkgs[3].name == "dummy-pkg-1"
    assert repo.pkgs[3].evr == ("", "1.0.2", "1")
    assert repo.pkgs[3].arch == "x86_64"

    assert repo.pkgs[12].name == "dummy-pkg-3"
    assert repo.pkgs[12].evr == ("", "1.0.2", "1")
    assert repo.pkgs[12].arch == "aarch64"

    assert repo.pkgs[15].name == "dummy-pkg-3"
    assert repo.pkgs[15].evr == ("", "1.0.2", "1")
    assert repo.pkgs[15].arch == "x86_64"

    assert repo.pkgs[30].name == "dummy-pkg-6"
    assert repo.pkgs[30].evr == ("", "1.0.2", "1")
    assert repo.pkgs[30].arch == "aarch64"

    assert repo.pkgs[33].name == "dummy-pkg-6"
    assert repo.pkgs[33].evr == ("", "1.0.2", "1")
    assert repo.pkgs[33].arch == "x86_64"


def test_query():
    repo = RepoMDParser("https://packages.example.com/sles/15.7/")

    with patch("bci_build.repomdparser.requests.get", side_effect=fake_repo_get):
        repo.parse()

    pkgs = repo.query("dummy-pkg-3")
    assert len(pkgs) == 6
    assert all(pkg.name == "dummy-pkg-3" for pkg in pkgs)

    pkgs = repo.query("dummy-pkg-2", arch="aarch64")
    assert len(pkgs) == 3
    assert all(pkg.name == "dummy-pkg-2" for pkg in pkgs)
    assert all(pkg.arch == "aarch64" for pkg in pkgs)

    pkgs = repo.query("dummy-pkg-2", arch="x86_64")
    assert len(pkgs) == 3
    assert all(pkg.name == "dummy-pkg-2" for pkg in pkgs)
    assert all(pkg.arch == "x86_64" for pkg in pkgs)

    pkgs = repo.query("dummy-pkg-5", latest=True)
    assert len(pkgs) == 2
    assert pkgs[0].name == "dummy-pkg-5"
    assert pkgs[0].arch == "aarch64"
    assert pkgs[0].evr[1] == "1.0.2"
    assert pkgs[1].name == "dummy-pkg-5"
    assert pkgs[1].arch == "x86_64"
    assert pkgs[1].evr[1] == "1.0.2"

    pkgs = repo.query("dummy-pkg-4", arch="aarch64", latest=True)
    assert len(pkgs) == 1
    assert pkgs[0].arch == "aarch64"
    assert pkgs[0].evr[1] == "1.0.2"

    pkgs = repo.query("dummy-pkg-4", arch="x86_64", latest=True)
    assert len(pkgs) == 1
    assert pkgs[0].arch == "x86_64"
    assert pkgs[0].evr[1] == "1.0.2"


def test_query_not_found():
    repo = RepoMDParser("https://packages.example.com/sles/15.7/")

    with patch("bci_build.repomdparser.requests.get", side_effect=fake_repo_get):
        repo.parse()

    pkgs = repo.query("dummy")
    assert len(pkgs) == 0

    pkgs = repo.query("dummy-pkg")
    assert len(pkgs) == 0

    pkgs = repo.query("dummy-pkg-100")
    assert len(pkgs) == 0

    pkgs = repo.query("dummy-pkg-1", arch="ppc64le")
    assert len(pkgs) == 0
