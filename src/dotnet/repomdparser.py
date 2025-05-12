"""Parse a repomd repository."""

import functools
import gzip
import importlib.metadata
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests
from version_utils import rpm


@dataclass(frozen=True)
class RpmPackage:
    name: str
    evr: str
    arch: str
    url: str
    checksum: str


_REPOMD_NS = {
    "c": "http://linux.duke.edu/metadata/common",
    "repo": "http://linux.duke.edu/metadata/repo",
    "rpm": "http://linux.duke.edu/metadata/rpm",
}

_REPOMD_REQ_HEADERS = {
    "User-Agent": f"BCI-dockerfile-gnerator/{importlib.metadata.version('bci_dockerfile_generator')}"
}


class RepoMDParser:
    def parse(self, baserepo_url: str):
        """return the list of packages"""

        repomd: requests.Response = requests.get(
            urllib.parse.urljoin(baserepo_url, "repodata/repomd.xml"),
            _REPOMD_REQ_HEADERS,
        )
        repomd.raise_for_status()
        primary_xml_location = None
        for data in ET.fromstring(repomd.content).iterfind("repo:data", _REPOMD_NS):
            if data.get("type") == "primary":
                primary_xml_location = urllib.parse.urljoin(
                    baserepo_url,
                    data.find("repo:location", namespaces=_REPOMD_NS).get("href"),
                )
                break

        if not primary_xml_location:
            return None

        assert primary_xml_location.startswith(baserepo_url)
        assert primary_xml_location.endswith(".gz")

        primary_xml_response = requests.get(
            urllib.parse.urljoin(baserepo_url, primary_xml_location),
            _REPOMD_REQ_HEADERS,
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
            pkgs.append(
                RpmPackage(
                    name=package.findtext("c:name", namespaces=_REPOMD_NS),
                    evr=("", ver.get("ver"), ver.get("rel")),
                    arch=package.findtext("c:arch", namespaces=_REPOMD_NS),
                    url=urllib.parse.urljoin(
                        baserepo_url,
                        package.find("c:location", namespaces=_REPOMD_NS).get("href"),
                    ),
                    checksum=package.findtext("c:checksum", namespaces=_REPOMD_NS),
                )
            )

        # sort reverse so that query for latest just needs to return the first one
        self.pkgs = sorted(
            pkgs,
            key=functools.cmp_to_key(lambda a, b: rpm.labelCompare(a.evr, b.evr)),
            reverse=True,
        )

    def query(self, name: str, arch: str, latest: bool = False):
        assert self.pkgs

        query_result = filter(lambda p: p.name == name and p.arch == arch, self.pkgs)
        first_or_none = next(iter(query_result), None)

        if not first_or_none:
            return []

        if latest:
            return [first_or_none]

        return [first_or_none] + list(iter(query_result))
