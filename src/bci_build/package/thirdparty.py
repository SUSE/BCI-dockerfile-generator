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

COPY third-party.gpg.key /tmp/{{ image.repo_key_filename }}
RUN rpm --import /tmp/{{ image.repo_key_filename }}

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

COPY third-party.repo /etc/zypp/repos.d/{{ image.repo_filename }}

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


class ThirdPartyRepoMixin:
    """A mixin to be used by images that require a third party repository."""

    def __init__(
        self,
        third_party_repo_url: str,
        third_party_repo_key_url: str,
        third_party_repo_key_file: str,
        third_party_package_list: list[str | RpmPackage],
        **kwargs,
    ):
        self.third_party_repo_url = third_party_repo_url
        self.third_party_repo_key_url = third_party_repo_key_url
        self.third_party_repo_key_file = third_party_repo_key_file
        self.third_party_package_list = third_party_package_list

        if not self.third_party_repo_key_file:
            res = requests.get(third_party_repo_key_url)
            res.raise_for_status()
            self.third_party_repo_key_file = res.text

        super().__init__(**kwargs)

        self.extra_files.update(
            {
                "third-party.gpg.key": self.third_party_repo_key_file,
                "third-party.repo": REPO_FILE.format(
                    repo_name=self.repo_filename.rpartition(".")[0],
                    repo_filename=self.repo_filename,
                    base_url=self.third_party_repo_url,
                    gpg_key=self.third_party_repo_key_url,
                ),
            }
        )

        self._repo_parser = RepoMDParser(self.third_party_repo_url)
        self._rpms: list[RpmPackage] = []

    @property
    def repo_filename(self):
        return f"{self.name}.repo"

    @property
    def repo_key_filename(self):
        return f"{self.name}.gpg.key"

    def fetch_rpm_package(
        self, pkg: ThirdPartyPackage, latest: bool = True
    ) -> list[RpmPackage]:
        """Fetches the packages that match `pkg` from the repository.

        If `latest` is set to True, it returns just the latest package.

        Returns:
            list of :py:class:`RpmPackage` representing the downloaded rpms
        """
        pkgs = self._repo_parser.query(name=pkg.name, arch=pkg.arch, version=pkg.version, latest=latest)

        if pkg.arch:
            exclusive_arch = [pkg.arch]
        else:
            exclusive_arch = self.exclusive_arch

        for arch in exclusive_arch:
            pkgs_found_for_arch = [
                p for p in pkgs if p.arch in ARCH_FILENAME_MAP[arch]
            ]
            found = len(pkgs_found_for_arch)

            if found > 1:
                raise Exception(
                    f"Found {found} packages for '{pkg.name}' and '{arch}': {pkgs_found_for_arch}"
                )
            elif found == 0:
                if pkg.arch is not None and pkg.arch != arch:
                    continue
                raise Exception(
                    f"Found no packages for '{pkg.name}' and '{arch}'."
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

            for pkg in self._rpms:
                assert "/" not in pkg.name, (
                    f"Bad package name in repository: {pkg.name}"
                )
                assert pkg.url.startswith(self.third_party_repo_url), (
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
