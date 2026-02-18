"""Parse a repomd repository."""

import functools
import gzip
import importlib.metadata
import os
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests
from version_utils import rpm


@dataclass
class RpmPackage:
    """Represents an RPM package with additional attributes."""

    name: str
    evr: tuple
    arch: str = None
    filename: str = None
    url: str = None
    checksum: str = None

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.url


_REPOMD_NS = {
    "c": "http://linux.duke.edu/metadata/common",
    "repo": "http://linux.duke.edu/metadata/repo",
    "rpm": "http://linux.duke.edu/metadata/rpm",
}

_REPOMD_REQ_HEADERS = {
    "User-Agent": f"BCI-dockerfile-generator/{importlib.metadata.version('bci_dockerfile_generator')}"
}


def cmp_pkg(a, b):
    if a.name != b.name:
        return -1 if a.name > b.name else 1
    if a.arch != b.arch:
        return -1 if a.arch > b.arch else 1
    return rpm.labelCompare(a.evr, b.evr)


class RepoMDParser:
    """A helper class to parse repomd.xml."""

    def __init__(self, baserepo_url: str):
        self.baserepo_url = baserepo_url
        self.pkgs = []

    def parse(self):
        """Parse the repository XML and load the list of packages."""
        repomd: requests.Response = requests.get(
            urllib.parse.urljoin(self.baserepo_url, "repodata/repomd.xml"),
            headers=_REPOMD_REQ_HEADERS,
        )
        repomd.raise_for_status()
        primary_xml_location = None
        for data in ET.fromstring(repomd.content).iterfind("repo:data", _REPOMD_NS):
            if data.get("type") == "primary":
                primary_xml_location = urllib.parse.urljoin(
                    self.baserepo_url,
                    data.find("repo:location", namespaces=_REPOMD_NS).get("href"),
                )
                break

        if not primary_xml_location:
            return None

        assert primary_xml_location.startswith(self.baserepo_url)
        assert primary_xml_location.endswith(".gz")

        primary_xml_response = requests.get(
            urllib.parse.urljoin(self.baserepo_url, primary_xml_location),
            headers=_REPOMD_REQ_HEADERS,
        )
        primary_xml_response.raise_for_status()
        primary_xml: ET.Element[str] = ET.fromstring(
            gzip.decompress(primary_xml_response.content)
        )

        pkgs = []

        for package in primary_xml.iterfind("c:package", _REPOMD_NS):
            ver: ET.Element[str] | None = package.find(
                "c:version", namespaces=_REPOMD_NS
            )

            loc: str = package.find("c:location", namespaces=_REPOMD_NS).get("href")

            rpm_pkg = RpmPackage(
                name=package.findtext("c:name", namespaces=_REPOMD_NS),
                evr=("", ver.get("ver"), ver.get("rel")),
                arch=package.findtext("c:arch", namespaces=_REPOMD_NS),
                filename=os.path.basename(loc),
                url=urllib.parse.urljoin(self.baserepo_url, loc),
                checksum=package.findtext("c:checksum", namespaces=_REPOMD_NS),
            )

            pkgs.append(rpm_pkg)

        # sort reverse so that query for latest just needs to return the first one
        self.pkgs = sorted(
            pkgs,
            key=functools.cmp_to_key(lambda a, b: cmp_pkg(a, b)),
            reverse=True,
        )

    def query(
        self, name: str, arch: str = None, version: str = None, latest: bool = False
    ) -> list[RpmPackage]:
        """
        Query packages in the repository and return the best match.

        Args:
            name: the package name
            arch: the package architecture
            latest: fetch the latest version for a given package

        Returns:
            list[RpmPackage]: List of packages matching the query arguments
        """
        if not self.pkgs:
            self.parse()

        query_result = filter(lambda p: p.name == name, self.pkgs)

        if arch:
            query_result = filter(lambda p: p.arch == arch, query_result)

        if version:
            query_result = filter(
                lambda p: p.evr[1][0 : len(version)] == version, query_result
            )

        if latest:
            # group by arch and filter for the latest version in case there are multiple matches
            # the list is already sorted, just find the first for each arch
            latest_pkgs = []
            seen_arch = set()

            for pkg in query_result:
                if pkg.arch not in seen_arch:
                    latest_pkgs.append(pkg)
                    seen_arch.add(pkg.arch)

            return latest_pkgs
        else:
            return list(query_result)
