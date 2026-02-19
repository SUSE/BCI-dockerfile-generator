from dataclasses import dataclass

import requests
from jinja2 import Template

from bci_build.container_attributes import Arch
from bci_build.container_attributes import BuildType
from bci_build.repomdparser import RepoMDParser
from bci_build.repomdparser import RpmPackage

CUSTOM_END_TEMPLATE = Template(
    """RUN mkdir -p /tmp/

{%- for pkg in packages %}
#!RemoteAssetUrl: {{ pkg.url }} sha256:{{ pkg.checksum }}
COPY {{ pkg.filename }} /tmp/
{%- endfor %}

{% for repo in image.third_party_repos -%}
COPY {{ repo.name }}.gpg.key /tmp/{{ repo.key_filename }}
RUN rpm --import /tmp/{{ repo.key_filename }}
{% endfor %}
{% for arch in image.exclusive_arch %}
{%- with pkgs=get_packages_for_arch(arch) %}
RUN if [ "$(uname -m)" = "{{ arch }}" ]; then \\
        zypper -n install \\
        {%- for pkg in pkgs %}
            /tmp/{{ pkg.filename }}{% if loop.last %};{% endif %} \\
        {%- endfor %}
    fi
{%- endwith %}
{%- endfor %}

{% for repo in image.third_party_repos -%}
COPY {{ repo.name }}.repo /etc/zypp/repos.d/{{ repo.repo_filename }}
{% endfor %}
RUN rm -rf /tmp/*
"""
)

REPO_FILE = """[{repo_name}]
name={repo_name}
baseurl={base_url}
enabled=1
gpgcheck=1
gpgkey={gpg_key}
"""

ARCH_FILENAME_MAP = {
    Arch.X86_64: ["x86_64", "x86", "noarch"],
    Arch.AARCH64: ["aarch64", "noarch"],
    Arch.PPC64LE: ["ppc64le", "noarch"],
    Arch.S390X: ["s390x", "noarch"],
}


@dataclass(frozen=True)
class ThirdPartyPackage:
    name: str
    arch: Arch = None
    version: str = None

    def __str__(self) -> str:
        return self.name


@dataclass
class ThirdPartyRepo:
    name: str
    url: str
    key: str = None
    key_url: str = None
    arch: Arch = None
    repo_name: str = None
    repo_filename: str = None
    key_filename: str = None


class ThirdPartyRepoParser:
    def __init__(self, repos: list[ThirdPartyRepo]):
        self.repos = repos
        self._repos = []
        self._repo_map = {}

        for repo in self.repos:
            self._repo_map[repo.url] = repo
            self._repos.append(RepoMDParser(repo.url))

    def query(self, *args, **kwargs) -> list[RpmPackage]:
        result = []

        for repo_parser in self._repos:
            pkgs = repo_parser.query(*args, **kwargs)
            result.extend(pkgs)

        return result


class ThirdPartyRepoMixin:
    """A mixin to be used by images that require a third party repository."""

    def __init__(
        self,
        third_party_repos: list[ThirdPartyRepo],
        third_party_package_list: list[str | RpmPackage],
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.third_party_repos = third_party_repos
        self.third_party_package_list = third_party_package_list

        for repo in self.third_party_repos:
            if not repo.key:
                res = requests.get(repo.key_url)
                res.raise_for_status()
                repo.key = res.text

            if not repo.repo_name:
                repo.repo_name = repo.name

            if not repo.repo_filename:
                repo.repo_filename = f"{repo.name}.repo"

            if not repo.key_filename:
                repo.key_filename = f"{repo.name}.gpg.key"

            self.extra_files.update(
                {
                    f"{repo.name}.gpg.key": repo.key,
                    f"{repo.name}.repo": REPO_FILE.format(
                        repo_name=repo.repo_name,
                        base_url=repo.url,
                        gpg_key=repo.key_url,
                    ),
                }
            )

        self._repo = ThirdPartyRepoParser(self.third_party_repos)
        self._rpms: list[RpmPackage] = []

    def fetch_rpm_package(
        self, pkg: ThirdPartyPackage, latest: bool = True
    ) -> list[RpmPackage]:
        """Fetches the packages that match `pkg` from the repository.

        If `latest` is set to True, it returns just the latest package.

        Returns:
            list of :py:class:`RpmPackage` representing the downloaded rpms
        """
        pkgs = self._repo.query(name=pkg.name, version=pkg.version, latest=latest)

        if self.exclusive_arch:
            allowed_arch = list(
                dict.fromkeys(
                    arch
                    for e_arch in self.exclusive_arch
                    for arch in ARCH_FILENAME_MAP[e_arch]
                )
            )
            pkgs = [p for p in pkgs if p.arch in allowed_arch]

        if self.exclusive_arch:
            for arch in self.exclusive_arch:
                pkgs_found_for_arch = [
                    p for p in pkgs if p.arch in ARCH_FILENAME_MAP[arch]
                ]
                found_for_arch = len(pkgs_found_for_arch)

                if found_for_arch > 1:
                    raise Exception(
                        f"It should have found 1 package '{pkg.name}' for '{arch}' in the repository, but found {found_for_arch}"
                    )
                elif found_for_arch == 0:
                    if pkg.arch is not None and pkg.arch != arch:
                        continue
                    raise Exception(
                        f"It should have found 1 package '{pkg.name}' for '{arch}' in the repository, but found none"
                    )

        return pkgs

    def fetch_rpm_packages(self) -> list[RpmPackage]:
        """Fetches all the required packages from the repository.

        Returns:
            list of :py:class:`RpmPackage` representing the downloaded rpms
        """
        if not self._rpms:
            for pkg in self.third_party_package_list:
                if isinstance(pkg, ThirdPartyPackage):
                    p = pkg
                else:
                    p = ThirdPartyPackage(name=pkg)

                self._rpms.extend(self.fetch_rpm_package(p))

            repo_urls = tuple([repo.url for repo in self.third_party_repos])

            for pkg in self._rpms:
                assert "/" not in pkg.name, (
                    f"Bad package name in repository: {pkg.name}"
                )
                assert pkg.url.startswith(repo_urls), (
                    f"Package download URL does not match repository: {pkg.name}"
                )

        return self._rpms

    def prepare_template(self) -> None:
        """Prepare the custom template used in the build_stage_custom_end."""
        assert self.build_recipe_type == BuildType.DOCKER, (
            f"Build type '{self.build_recipe_type}' is not supported for Third Party images"
        )
        assert len(self.third_party_package_list) > 0, (
            "The `third_party_package_list` is empty"
        )

        pkgs = self.fetch_rpm_packages()

        assert not self.build_stage_custom_end, (
            "Can't use `build_stage_custom_end` for ThirdPartyRepoMixin."
        )

        self.build_stage_custom_end = CUSTOM_END_TEMPLATE.render(
            image=self,
            packages=pkgs,
            get_packages_for_arch=lambda arch: [
                pkg for pkg in pkgs if pkg.arch in ARCH_FILENAME_MAP[arch]
            ],
        )

        super().prepare_template()
