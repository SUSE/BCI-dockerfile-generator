"""Parse a repomd repository."""

import gzip
import importlib.metadata
import os
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import total_ordering

import requests
from version_utils import rpm


@total_ordering
@dataclass(frozen=True)
class RpmPackage:
    name: str
    version: str = None
    release: str = None
    arch: str = None
    filename: str = None
    url: str = None
    checksum: str = None

    def __eq__(self, other):
        return rpm.compare_versions(self.version, other.version) == 0

    def __lt__(self, other):
        return rpm.compare_versions(self.version, other.version) == -1


_REPOMD_NS = {
    "c": "http://linux.duke.edu/metadata/common",
    "repo": "http://linux.duke.edu/metadata/repo",
    "rpm": "http://linux.duke.edu/metadata/rpm",
}

_REPOMD_REQ_HEADERS = {
    "User-Agent": f"BCI-dockerfile-gnerator/{importlib.metadata.version('bci_dockerfile_generator')}"
}


class RepoMDParser:
    def __init__(self, baserepo_url: str):
        self.baserepo_url = baserepo_url
        self.pkgs = []

    def parse(self):
        """return the list of packages"""
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
                version=ver.get("ver"),
                release=ver.get("ver"),
                arch=package.findtext("c:arch", namespaces=_REPOMD_NS),
                filename=os.path.basename(loc),
                url=urllib.parse.urljoin(self.baserepo_url, loc),
                checksum=package.findtext("c:checksum", namespaces=_REPOMD_NS),
            )

            pkgs.append(rpm_pkg)

        # reverse sort for latest packages to be the first
        self.pkgs = sorted(pkgs, reverse=True)

    def query(
        self, name: str, version: str = None, arch: str = None, latest: bool = False
    ):
        if not self.pkgs:
            self.parse()

        query_result = filter(lambda p: p.name == name, self.pkgs)

        if version:
            size = len(version)
            query_result = filter(lambda p: p.version[:size] == version, query_result)

        if arch:
            query_result = filter(lambda p: p.arch == arch, query_result)

        if latest:
            # group by arch and filter for the latest version in case there are multiple matches
            # the list is already sorted, just find the first for each arch
            # return [next(g) for _, g in groupby(query_result, key=lambda p: p.arch)]
            latest_pkgs = []
            seen_arch = set()

            for pkg in query_result:
                if pkg.arch not in seen_arch:
                    latest_pkgs.append(pkg)
                    seen_arch.add(pkg.arch)

            return latest_pkgs
        else:
            return list(query_result)
