"""
This module contains classes and functions related to updating and generating Dockerfiles for .NET development containers.
"""

import datetime
import functools
from typing import Literal

from jinja2 import Template
from packaging import version
from version_utils import rpm

from bci_build.container_attributes import Arch
from bci_build.os_version import CAN_BE_LATEST_OS_VERSION
from bci_build.os_version import OsVersion
from bci_build.package import DevelopmentContainer
from bci_build.package import generate_disk_size_constraints
from bci_build.package.thirdparty import ThirdPartyPackage
from bci_build.package.thirdparty import ThirdPartyRepo
from bci_build.package.thirdparty import ThirdPartyRepoMixin
from bci_build.repomdparser import RpmPackage

MS_REPO_15_KEY_FILE = """-----BEGIN PGP PUBLIC KEY BLOCK-----
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

MS_REPO_16_KEY_FILE = """-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBGVUhiwBEADF3TWX0HMi2+BdQfJrSdQkZTE4qk4vV2ooAMn8vWA2DGI88JOl
k1LwhZGEqJv5TsKTyNEMWb3NXhR1ZZ5uQPvf6iN0806cq83s096F85GUtjzfGLQj
Zo3FhDSKeHz3mhthQ4QP4bwYUmSpWs6e+/ZSFYYc3yU8mInDM4SNzrqr4x2ltmf+
3RWkoYYo1SpG521A9+1zi7xzz6IHpAk6MdIcTj7mHxXd6ovmXkvHUhKbXGkybHPn
iupWokDaJZgV4+q6kc7zVgTVnwmXV7NHQhWSyOm/BmYVcpmrkCSgSH18SArFjR6Q
KyJ9VuUo1mJEUGnEakQSaOn1UAYtO8Mh4cXXD4833G0BLjiFNOL0XRUNh35pKvcT
my/HnXvRXtpzAzTtANPxIbjli/veagU+JRWhtjtfONz0wQ5Bv1zFjnM9ewxFNPPo
7Jp9WCVeUKFZcZJo8r/k7Y4d0Y1WINOPniSCNhKcD0pva3gXLcxfdnZjdMSj++ba
XlAstjw0Oyty0EXoHXCMpelMoa+DQ7KSDGKrOtm5YFAP6Ki4go1Tt2q8nmul36cZ
Zot6eoPG/qKxW+dvmSrWhQCcfd74VbhECbzXiCFLHadq85C1K5rrLM6oVr1u7K6O
jlc1aitGgZECi6fvu61QhpUvHjCegRWzMIhah9qrv4lvxFFcA+a1jwXlnwARAQAB
tEJNaWNyb3NvZnQgQ29ycG9yYXRpb24gLSBHZW5lcmFsIEdQRyBTaWduZXIgPGdw
Z3NpZ25AbWljcm9zb2Z0LmNvbT6JAjgEEwEIACIFAmVUhiwCGwMGCwkIBwMCBhUI
AgkKCwQWAgMBAh4BAheAAAoJEO5Nd5L3SBgrDc0P/0Ubx0vqD/DgyhiP0bIs8euO
iA5BQvOCiroIkhSkFbAw8rT9a/XtRTRM2l4I8c2M1ZX9i/0wWihmFUJhiVHyRxkl
ZcEFv+ieBuhvD1gPOVLZg3To8yOTrcOnHe+FuKqA6u+3xBn2AmAWeck9o0NKhtnm
5ckweos+Qj9NoxaZX8UeGFstOiTBJeyhuJjthQ+3M0BvTxEaRcLXGSXSGSgZ00ii
YSLNgOMPF+C22bXBL/erClEYkIGCctqPvyrhV/GVNnGk2ALyJqdK+BaJeGh9mBJa
ZrP3l6vFxsAI0RNCNU1s5QaFzfFzFkiUnG/aoyuwh4xmsB+uyVkR+KigPK9gfF3S
nU7AqcdhSbUA6A0DGDRkHauHM5Wtc7730LdjiNDXbYwG/yXmDYNasoszmItZzh77
HiQxYA5dNB9r9QJS2rHV/qe+heAJ5Rub5kxcu33DGL30qG7Q9+HRTu0oSEOIUFyT
aOJJnNUiB2D4hoKKnr5U8FYOZ7KvDcG7cDvInqYtGpNfrnIf94VeB9WJY6DbDQSA
F5yHb6X8FS0x3lMT2H1l6RRyr0278kyO18VBudtlnonC+Y1UT7eqAk6WjS5CitPX
T3Hc7jCURugXrc51igKa+p67yAaybEIuVyWF6JaINKRqiUqEPVXnHELXPbBmiHW5
1HwdbKTMzgF8bu1JI+tQ
=lIzW
-----END PGP PUBLIC KEY BLOCK-----
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

CUSTOM_END_TEMPLATE = Template("""
{%- if image.is_sdk -%}
COPY dotnet-host.check /etc/zypp/systemCheck.d/dotnet-host.check

# telemetry opt out: https://docs.microsoft.com/en-us/dotnet/core/tools/telemetry#how-to-opt-out
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
{%- endif %}

{% if not image.is_sdk and image.use_nonprivileged_user -%}
ENV APP_UID=1654 ASPNETCORE_HTTP_PORTS=8080 DOTNET_RUNNING_IN_CONTAINER=true
ENV DOTNET_VERSION={{ image.version }}
RUN useradd --uid=$APP_UID -U -d /app -G '' -ms /bin/bash app
WORKDIR /app
EXPOSE 8080
{%- endif %}
""")


MS_REPOS = {
    OsVersion.SP7: [
        ThirdPartyRepo(
            name="third-party",
            url="https://packages.microsoft.com/sles/15/prod/",
            key=MS_REPO_15_KEY_FILE,
            key_url="https://packages.microsoft.com/sles/15/prod/repodata/repomd.xml.key",
            repo_name="packages-microsoft-com-prod",
            repo_filename="packages-microsoft-com-prod.repo",
            key_filename="microsoft.asc",
        ),
    ],
    OsVersion.SL16_0: [
        ThirdPartyRepo(
            name="third-party",
            url="https://packages.microsoft.com/sles/16/prod/",
            key=MS_REPO_16_KEY_FILE,
            key_url="https://packages.microsoft.com/sles/16/prod/repodata/repomd.xml.key",
            repo_name="packages-microsoft-com-prod",
            repo_filename="packages-microsoft-com-prod.repo",
            key_filename="microsoft.asc",
        ),
    ],
    OsVersion.SL16_1: [
        ThirdPartyRepo(
            name="third-party",
            url="https://packages.microsoft.com/sles/16/prod/",
            key=MS_REPO_16_KEY_FILE,
            key_url="https://packages.microsoft.com/sles/16/prod/repodata/repomd.xml.key",
            repo_name="packages-microsoft-com-prod",
            repo_filename="packages-microsoft-com-prod.repo",
            key_filename="microsoft.asc",
        ),
    ],
}


class DotNetBCI(ThirdPartyRepoMixin, DevelopmentContainer):
    """Represents a .NET development container based on the SLE Base Container Image."""

    #: Specifies whether this package contains the full .Net SDK
    is_sdk: bool

    #: Specifies whether this container needs a nonprivileged user (defaults to True for dotnet 8.0+)
    use_nonprivileged_user: bool

    def __init__(self, is_sdk: bool, use_nonprivileged_user: bool = False, **kwargs):
        self.is_sdk = is_sdk
        self.use_nonprivileged_user = use_nonprivileged_user

        super().__init__(**kwargs)

    def __post_init__(self):
        if self.os_version in (OsVersion.TUMBLEWEED,):
            raise ValueError(".NET is not supported for this os_version")

        super().__post_init__()

        # https://learn.microsoft.com/en-us/dotnet/core/compatibility/containers/8.0/aspnet-port
        self.use_nonprivileged_user = False
        if self.tag_version != "6.0":
            self.use_nonprivileged_user = True

        self.custom_description = (
            f"The {self.pretty_name} {{based_on_container}}. "
            "The .NET packages contained in this image come from a 3rd-party repository https://packages.microsoft.com/. "
            "You can find the respective source code in https://github.com/dotnet. SUSE does not provide any support or warranties."
        )

        ver = version.parse(str(self.tag_version))

        # Set the lifecycle information taken from
        # https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core
        self.supported_until = {
            "8.0": datetime.date(2026, 11, 10),
            "9.0": datetime.date(2026, 11, 10),
            "10.0": datetime.date(2028, 11, 12),
        }.get(str(self.tag_version))
        assert self.supported_until, (
            f".NET version missing in lifecycle information: {self.tag_version}"
        )

        self.extra_files.update(
            {
                "dotnet-host.check": f"requires:dotnet-host < {ver.major}.{ver.minor + 1}",
                "LICENSE": LICENSE,
                "_constraints": generate_disk_size_constraints(8),
            }
        )

        self.custom_labelprefix_end = self.name.replace("-", ".")
        min_release_counter = {"8.0": 60, "9.0": 20, "10.0": 0}[str(self.tag_version)]
        self.min_release_counter = {
            self.os_version: min_release_counter,
        }

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
        assert self.exclusive_arch
        pkgs = []
        for arch in self.exclusive_arch:
            pkgs_per_arch = self._repo.query(
                name="dotnet-host", arch=str(arch), latest=False
            )
            matching_pkg = [
                pkg
                for pkg in pkgs_per_arch
                if pkg.evr[1][: len(str(self.tag_version))] == self.tag_version
            ]
            latest_pkg = sorted(
                matching_pkg,
                key=functools.cmp_to_key(lambda a, b: rpm.labelCompare(a.evr, b.evr)),
            )[-1]
            pkgs.append(latest_pkg)

        return pkgs

    def _guess_version_from_pkglist(self, pkg_list: list[RpmPackage]) -> str | None:
        assert self.exclusive_arch
        versions: dict[Arch, str] = {}
        for arch in self.exclusive_arch:
            for pkg in pkg_list:
                if "dotnet-runtime" in pkg.name and pkg.arch == str(arch):
                    versions[str(arch)] = pkg.evr[1]
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

    def fetch_rpm_package(
        self, pkg: ThirdPartyPackage, latest: bool = True
    ) -> list[RpmPackage]:
        if pkg.name == "dotnet-host":
            return self._fetch_dotnet_host()
        else:
            return super().fetch_rpm_package(pkg, latest)

    def prepare_template(self) -> None:
        pkgs = self.fetch_rpm_packages()

        self.version = self._guess_version_from_pkglist(pkgs)
        self.custom_end = CUSTOM_END_TEMPLATE.render(image=self)

        super().prepare_template()


_DOTNET_EXCLUSIVE_ARCH = [Arch.AARCH64, Arch.X86_64]

_DOTNET_VERSION_T = Literal["8.0", "9.0", "10.0"]

_DOTNET_VERSIONS: list[_DOTNET_VERSION_T] = ["8.0", "9.0", "10.0"]

_LATEST_DOTNET_VERSION = "10.0"

assert _LATEST_DOTNET_VERSION in _DOTNET_VERSIONS
assert _DOTNET_VERSIONS == sorted(_DOTNET_VERSIONS, key=version.parse)
assert _DOTNET_VERSIONS[-1] == _LATEST_DOTNET_VERSION


def _is_latest_dotnet(version: _DOTNET_VERSION_T, os_version: OsVersion) -> bool:
    return version == _LATEST_DOTNET_VERSION and os_version in CAN_BE_LATEST_OS_VERSION


DOTNET_CONTAINERS: list[DotNetBCI] = []

for os_version in (OsVersion.SP7, OsVersion.SL16_0, OsVersion.SL16_1):
    for ver in _DOTNET_VERSIONS:
        package_list = sorted(
            [*os_version.release_package_names, "libopenssl3", "libicu"]
            + (["coreutils"] if os_version.is_sle15 else ["krb5"])
        )

        DOTNET_CONTAINERS.append(
            DotNetBCI(
                os_version=os_version,
                tag_version=ver,
                name="dotnet-sdk",
                pretty_name=f".NET SDK {ver}",
                is_sdk=True,
                is_latest=_is_latest_dotnet(ver, os_version),
                additional_versions=(
                    [f"{ver}-{os_version.dist_id}"] if os_version.dist_id else []
                ),
                package_name=f"dotnet-{ver}",
                exclusive_arch=_DOTNET_EXCLUSIVE_ARCH,
                package_list=package_list,
                third_party_repos=MS_REPOS[os_version],
                third_party_package_list=[
                    "dotnet-host",
                    ThirdPartyPackage(
                        name="netstandard-targeting-pack-2.1", arch=Arch.X86_64
                    ),
                ]
                + [
                    f"{pkg}-{ver}"
                    for pkg in (
                        "dotnet-targeting-pack",
                        "dotnet-hostfxr",
                        "dotnet-runtime-deps",
                        "dotnet-runtime",
                        "dotnet-apphost-pack",
                        "aspnetcore-targeting-pack",
                        "aspnetcore-runtime",
                        "dotnet-sdk",
                    )
                ],
            )
        )

    DOTNET_CONTAINERS.extend(
        [
            DotNetBCI(
                os_version=os_version,
                tag_version=ver,
                name="dotnet-runtime",
                is_sdk=False,
                pretty_name=f".NET Runtime {ver}",
                is_latest=_is_latest_dotnet(ver, os_version),
                package_name=f"dotnet-runtime-{ver}",
                exclusive_arch=_DOTNET_EXCLUSIVE_ARCH,
                additional_versions=(
                    [f"{ver}-{os_version.dist_id}"] if os_version.dist_id else []
                ),
                package_list=package_list,
                third_party_repos=MS_REPOS[os_version],
                third_party_package_list=[
                    "dotnet-host",
                ]
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

    DOTNET_CONTAINERS.extend(
        [
            DotNetBCI(
                tag_version=ver,
                os_version=os_version,
                name="dotnet-aspnet",
                is_sdk=False,
                pretty_name=f"ASP.NET Core Runtime {ver}",
                is_latest=_is_latest_dotnet(ver, os_version),
                package_name=f"aspnet-runtime-{ver}",
                additional_versions=(
                    [f"{ver}-{os_version.dist_id}"] if os_version.dist_id else []
                ),
                exclusive_arch=_DOTNET_EXCLUSIVE_ARCH,
                package_list=package_list,
                third_party_repos=MS_REPOS[os_version],
                third_party_package_list=[
                    "dotnet-host",
                ]
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
