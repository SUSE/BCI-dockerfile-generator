import logging
from dataclasses import dataclass
from dataclasses import field
from functools import cmp_to_key
from os.path import basename
from typing import ClassVar
from typing import Literal
from urllib.parse import urlparse

import dnf
from jinja2 import Template

from bci_build.logger import LOGGER
from bci_build.package import CAN_BE_LATEST_OS_VERSION
from bci_build.package import DevelopmentContainer
from bci_build.package import OsVersion
from bci_build.package import generate_disk_size_constraints
from staging.build_result import Arch

MS_ASC = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.7 (GNU/Linux)

mQENBFYxWIwBCADAKoZhZlJxGNGWzqV+1OG1xiQeoowKhssGAKvd+buXCGISZJwT
LXZqIcIiLP7pqdcZWtE9bSc7yBY2MalDp9Liu0KekywQ6VVX1T72NPf5Ev6x6DLV
7aVWsCzUAF+eb7DC9fPuFLEdxmOEYoPjzrQ7cCnSV4JQxAqhU4T6OjbvRazGl3ag
OeizPXmRljMtUUttHQZnRhtlzkmwIrUivbfFPD+fEoHJ1+uIdfOzZX8/oKHKLe2j
H632kvsNzJFlROVvGLYAk2WRcLu+RjjggixhwiB+Mu/A8Tf4V6b+YppS44q8EvVr
M+QvY7LNSOffSO6Slsy9oisGTdfE39nC7pVRABEBAAG0N01pY3Jvc29mdCAoUmVs
ZWFzZSBzaWduaW5nKSA8Z3Bnc2VjdXJpdHlAbWljcm9zb2Z0LmNvbT6JATUEEwEC
AB8FAlYxWIwCGwMGCwkIBwMCBBUCCAMDFgIBAh4BAheAAAoJEOs+lK2+EinPGpsH
/32vKy29Hg51H9dfFJMx0/a/F+5vKeCeVqimvyTM04C+XENNuSbYZ3eRPHGHFLqe
MNGxsfb7C7ZxEeW7J/vSzRgHxm7ZvESisUYRFq2sgkJ+HFERNrqfci45bdhmrUsy
7SWw9ybxdFOkuQoyKD3tBmiGfONQMlBaOMWdAsic965rvJsd5zYaZZFI1UwTkFXV
KJt3bp3Ngn1vEYXwijGTa+FXz6GLHueJwF0I7ug34DgUkAFvAs8Hacr2DRYxL5RJ
XdNgj4Jd2/g6T9InmWT0hASljur+dJnzNiNCkbn9KbX7J/qK1IbR8y560yRmFsU+
NdCFTW7wY0Fb1fWJ+/KTsC4=
=J6gs
-----END PGP PUBLIC KEY BLOCK-----
"""

MS_REPO_BASEURL = "https://packages.microsoft.com/sles/15/prod/"

MS_REPO = f"""[packages-microsoft-com-prod]
name=packages-microsoft-com-prod
baseurl={MS_REPO_BASEURL}
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
"""

LICENSE = """Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


README_MD_TEMPLATE = Template(
    """# {{ image.title }}

The .NET packages contained in this image come from a 3rd-party repository:
[packages.microsoft.com](https://packages.microsoft.com).

You can find the respective source code in
[github.com/dotnet](https://github.com/dotnet). SUSE doesn't provide any support
or warranties.
"""
)

CUSTOM_END_TEMPLATE = Template(
    """{% if image.is_sdk %}# telemetry opt out: https://docs.microsoft.com/en-us/dotnet/core/tools/telemetry#how-to-opt-out
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1{% endif %}

RUN mkdir -p /tmp/

{% for pkg in dotnet_packages -%}
#!RemoteAssetUrl: {{ pkg.url }}
COPY {{ pkg.name }} /tmp/
{% endfor %}

# Workaround for https://github.com/openSUSE/obs-build/issues/487
RUN zypper --non-interactive install --no-recommends sles-release

# Importing MS GPG keys
COPY microsoft.asc /tmp
RUN rpm --import /tmp/microsoft.asc

RUN zypper --non-interactive install --no-recommends libicu {# we need to explicitly require openssl 1.1 since SP6 #}{% if image.os_version | string not in ["3", "4", "5"] %}libopenssl1_1 {% endif %}/tmp/*rpm

COPY prod.repo /etc/zypp/repos.d/microsoft-dotnet-prod.repo
RUN zypper -n addlock dotnet-host

RUN rm -rf /tmp/* && zypper clean && rm -rf /var/log/*

{% if not image.is_sdk and image.use_nonprivileged_user %}
ENV APP_UID=1654 ASPNETCORE_HTTP_PORTS=8080 DOTNET_RUNNING_IN_CONTAINER=true
ENV DOTNET_VERSION={{ dotnet_version }}
RUN useradd --uid=$APP_UID -U -d /app -G '' -ms /bin/bash app
WORKDIR /app
EXPOSE 8080
{% endif %}
"""
)


@dataclass(frozen=True)
class Package:
    name: str
    arch: Arch

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class RpmPackage(Package):
    version: str
    url: str

    @staticmethod
    def from_dnf_package(pkg: dnf.package.Package, arch: Arch) -> "RpmPackage":
        return RpmPackage(
            arch=arch,
            url=(url := pkg.remote_location()),
            version=pkg.version,
            name=basename(urlparse(url).path),
        )


_DOTNET_EXCLUSIVE_ARCH = [Arch.X86_64]


@dataclass
class DotNetBCI(DevelopmentContainer):
    #: Specifies whether this package contains the full .Net SDK
    is_sdk: bool = False

    #: Specifies whether this container needs a nonprivileged user (defaults to True for dotnet 8.0+)
    use_nonprivileged_user: bool = False

    package_list: list[str | Package] | list[str] = field(default_factory=list)

    _base: ClassVar[dnf.Base | None] = None
    _sle_bci_base: ClassVar[dict[OsVersion, dict[Arch, dnf.Base]]] = {}

    _logger: ClassVar[logging.Logger] = LOGGER

    def __post_init__(self):
        if OsVersion.TUMBLEWEED == self.os_version:
            raise ValueError(".Net BCIs are not supported for openSUSE Tumbleweed")
        super().__post_init__()

        # https://learn.microsoft.com/en-us/dotnet/core/compatibility/containers/8.0/aspnet-port
        self.use_nonprivileged_user = False
        if self.version != "6.0":
            self.use_nonprivileged_user = True

        self.custom_description = f"The {self.pretty_name} based on the SLE Base Container Image. The .NET packages contained in this image come from a 3rd-party repository http://packages.microsoft.com. You can find the respective source code in https://github.com/dotnet. SUSE doesn't provide any support or warranties."

        self.extra_files = {
            "microsoft.asc": MS_ASC,
            "prod.repo": MS_REPO,
            "README.md": README_MD_TEMPLATE.render(image=self),
            "LICENSE": LICENSE,
            "_constraints": generate_disk_size_constraints(8),
        }

        self.custom_labelprefix_end = self.name.replace("-", ".")

        self.exclusive_arch = _DOTNET_EXCLUSIVE_ARCH

    def _fetch_ordinary_package(self, pkg: str | Package) -> list[RpmPackage]:
        """Fetches the package `pkg` from the microsoft .Net repository and
        stores it in the target folder `dest`. The target folder must exist.

        Returns:
            list of :py:class:`RpmPackage` representing the downloaded rpms, one for each architecture
        """
        assert self._base and self.exclusive_arch
        pkgs = []
        pkg_name = str(pkg)

        for arch in self.exclusive_arch:
            if isinstance(pkg, Package) and pkg.arch != arch:
                continue

            pkgs_for_arch = list(
                DotNetBCI._base.sack.query()
                .available()
                .filter(name=pkg_name, latest=True, arch=str(arch))
            )
            self._logger.debug("Found package %s: %s", pkg_name, pkgs_for_arch)
            if len(pkgs_for_arch) != 1:
                raise RuntimeError(
                    f"Repository contains {len(pkgs_for_arch)} packages with name='{pkg_name}' for {str(arch)}"
                )

            pkgs.append(RpmPackage.from_dnf_package(pkg=pkgs_for_arch[0], arch=arch))

        if isinstance(pkg, str):
            assert len(pkgs) == len(
                self.exclusive_arch
            ), "Must find one package per architecture"

        return pkgs

    def _fetch_dotnet_host(self) -> list[RpmPackage]:
        """Fetches the dotnet-host package belonging to this image's major version.

        This function exists due to a peculiarity in the Microsoft .Net
        repository: while most packages have the .Net runtime version (e.g. 5.0)
        included in the name, the ``dotnet-host`` package does not. It exists as
        ``dotnet-host`` with the evr ranging from 2.0.0 to 6.0.0. Thus, to get
        the correct package, we have to query the repository for all available
        versions, manually find the ones with the correct major version and then
        perform a evr comparison to find the most recent one.

        Returns:
            list of :py:class:`RpmPackage` representing the downloaded rpm
        """
        assert self._base and self.exclusive_arch
        pkgs = []
        for arch in self.exclusive_arch:
            pkgs_per_arch = list(
                DotNetBCI._base.sack.query()
                .available()
                .filter(name="dotnet-host", arch=str(arch))
            )
            matching_pkg = [
                pkg
                for pkg in pkgs_per_arch
                if pkg.version[: len(str(self.version))] == self.version
            ]
            self._logger.debug(
                "found the following packages matching dotnet-host version %d: %s",
                self.version,
                matching_pkg,
            )
            latest_pkg = sorted(
                matching_pkg, key=cmp_to_key(lambda p1, p2: p1.evr_cmp(p2))
            )[-1]
            self._logger.debug("latest package versions: %s", latest_pkg)
            pkgs.append(RpmPackage.from_dnf_package(latest_pkg, arch))

        return pkgs

    def _fetch_packages(self) -> list[RpmPackage]:
        """Fetches all packages in self.packages from the Microsoft .Net repo, saves
        them in the target folder `dest` and returns the list of files.

        """
        assert self.exclusive_arch
        rpm_pkgs: list[RpmPackage] = []
        for pkg in self.package_list:
            if pkg == "dotnet-host":
                rpm_pkgs.extend(self._fetch_dotnet_host())
            else:
                rpm_pkgs.extend(self._fetch_ordinary_package(pkg))

        for pkg in rpm_pkgs:
            assert (
                pkg.arch in self.exclusive_arch
                and "/" not in pkg.name
                and pkg.url.startswith(MS_REPO_BASEURL)
            )
        return rpm_pkgs

    def _guess_version_from_pkglist(self, pkg_list: list[RpmPackage]) -> str | None:
        assert self.exclusive_arch
        versions: dict[Arch, str] = {}
        for arch in self.exclusive_arch:
            for pkg in pkg_list:
                if "dotnet-runtime" in pkg.name and pkg.arch == arch:
                    versions[arch] = pkg.version
        if not versions:
            return None
        elif len(versions) != len(self.exclusive_arch):
            raise ValueError(
                f"Obtained a latest version for {versions.keys()} but need a version for all architectures({self.exclusive_arch})"
            )
        else:
            _, ver = versions.popitem()
            while versions:
                if (arch_ver := versions.popitem())[1] != ver:
                    raise ValueError(
                        f"Version miss-match between architectures, expected {ver} but got {arch_ver[1]} for {arch_ver[0]}"
                    )
            return ver

    def generate_custom_end(self) -> None:
        assert self.package_list
        if not DotNetBCI._base:
            DotNetBCI._base = dnf.Base()
            DotNetBCI._base.repos.add_new_repo(
                repoid="packages-microsoft-com-prod",
                conf=DotNetBCI._base.conf,
                baseurl=(MS_REPO_BASEURL,),
            )
            DotNetBCI._base.fill_sack()

        pkgs = self._fetch_packages()

        if new_version := self._guess_version_from_pkglist(pkgs):
            assert not self.additional_versions, f"additional_versions property must be unset, but got {self.additional_versions}"
            self.additional_versions = [new_version]

        self.custom_end = CUSTOM_END_TEMPLATE.render(
            image=self,
            dotnet_packages=pkgs,
            dotnet_version=new_version,
        )
        self.package_list = []


_DOTNET_VERSION_T = Literal["6.0", "8.0"]

_DOTNET_VERSIONS: list[_DOTNET_VERSION_T] = ["6.0", "8.0"]

_LATEST_DOTNET_VERSION = "8.0"


def _is_latest_dotnet(version: _DOTNET_VERSION_T, os_version: OsVersion) -> bool:
    return version == _LATEST_DOTNET_VERSION and os_version in CAN_BE_LATEST_OS_VERSION


DOTNET_IMAGES: list[DotNetBCI] = []

for os_version in (OsVersion.SP5, OsVersion.SP6):
    for ver in _DOTNET_VERSIONS:
        package_list: list[Package | str] = [
            "dotnet-host",
            Package(name="netstandard-targeting-pack-2.1", arch=Arch.X86_64),
        ]

        for pkg in (
            "dotnet-targeting-pack",
            "dotnet-hostfxr",
            "dotnet-runtime-deps",
            "dotnet-runtime",
            "dotnet-apphost-pack",
            "aspnetcore-targeting-pack",
            "aspnetcore-runtime",
            "dotnet-sdk",
        ):
            package_list.append(f"{pkg}-{ver}")

        DOTNET_IMAGES.append(
            DotNetBCI(
                os_version=os_version,
                version=ver,
                name="dotnet-sdk",
                pretty_name=f".Net {ver} SDK",
                is_sdk=True,
                is_latest=_is_latest_dotnet(ver, os_version),
                package_name=f"dotnet-{ver}",
                package_list=package_list,
            )
        )

    DOTNET_IMAGES.extend(
        [
            DotNetBCI(
                os_version=os_version,
                version=ver,
                name="dotnet-runtime",
                is_sdk=False,
                pretty_name=f".NET {ver} runtime",
                is_latest=_is_latest_dotnet(ver, os_version),
                package_name=f"dotnet-runtime-{ver}",
                package_list=["dotnet-host"]
                + [
                    f"{pkg}-{ver}"
                    for pkg in (
                        "dotnet-hostfxr",
                        "dotnet-runtime-deps",
                        "dotnet-runtime",
                    )
                ],
            )
            for ver in _DOTNET_VERSIONS
        ]
    )

    DOTNET_IMAGES.extend(
        [
            DotNetBCI(
                version=ver,
                os_version=os_version,
                name="dotnet-aspnet",
                is_sdk=False,
                pretty_name=f"ASP.NET {ver} runtime",
                is_latest=_is_latest_dotnet(ver, os_version),
                package_name=f"aspnet-runtime-{ver}",
                package_list=["dotnet-host"]
                + [
                    f"{pkg}-{ver}"
                    for pkg in (
                        "dotnet-hostfxr",
                        "dotnet-runtime-deps",
                        "dotnet-runtime",
                        "aspnetcore-runtime",
                    )
                ],
            )
            for ver in _DOTNET_VERSIONS
        ]
    )
