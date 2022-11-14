import enum
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field

from staging.util import get_obs_project_url


@enum.unique
class Arch(enum.Enum):
    """Architectures of packages on OBS"""

    X86_64 = "x86_64"
    AARCH64 = "aarch64"
    PPC64LE = "ppc64le"
    S390X = "s390x"
    LOCAL = "local"

    def __str__(self) -> str:
        return self.value


@enum.unique
class PackageStatusCode(enum.Enum):
    """Possible package states"""

    FAILED = "failed"
    SUCCEEDED = "succeeded"
    UNRESOLVABLE = "unresolvable"
    EXCLUDED = "excluded"
    BUILDING = "building"
    FINISHED = "finished"
    SCHEDULED = "scheduled"
    SIGNING = "signing"
    BLOCKED = "blocked"
    BROKEN = "broken"

    def __str__(self) -> str:
        return self.value

    def pretty_print(self):
        """Returns the value of this enum with an emoji visualizing the status."""
        _emoji: dict[PackageStatusCode, str] = {
            PackageStatusCode.FAILED: "❌",
            PackageStatusCode.SUCCEEDED: "✅",
            PackageStatusCode.UNRESOLVABLE: "🚫",
            PackageStatusCode.EXCLUDED: "⛔",
            PackageStatusCode.BUILDING: "🛻",
            PackageStatusCode.FINISHED: "🏁",
            PackageStatusCode.SCHEDULED: "⏱",
            PackageStatusCode.SIGNING: "🔑",
            PackageStatusCode.BLOCKED: "✋",
            PackageStatusCode.BROKEN: "💥",
        }
        return f"{_emoji[self]} {self}"


@dataclass
class PackageBuildResult:
    """The build result of a single package."""

    #: The package name
    name: str

    #: build status of the package
    code: PackageStatusCode

    #: an optional message providing additional details, e.g. on which worker
    #: this package is being built or why it is not resolvable
    detail_message: str | None = None


@dataclass
class RepositoryBuildResult:
    """The build results of a repository for a specific architecture."""

    #: name of the project to which this repository belongs
    project: str
    #: repository name
    repository: str
    #: repository architecture
    arch: Arch
    #: status code (usually equals to :py:attr:`~RepositoryBuildResult.state`)
    code: str
    #: repository status
    state: str
    #: state of all packages in this repository & arch
    packages: list[PackageBuildResult] = field(default_factory=list)
    #: if a repository is dirty, then it is still processing build jobs and has
    #: not been fully published yet
    dirty: bool = False

    @staticmethod
    def _from_result(result: ET.Element) -> "RepositoryBuildResult":
        assert (
            result.tag == "result"
        ), f"Invalid element passed, expected '<result>' but got: {ET.tostring(result).decode()}"
        attr = result.attrib
        for attr_name in ("project", "repository", "arch", "code", "state"):
            if attr_name not in attr:
                raise ValueError(
                    f"Missing property {attr_name} in '<result> element: {ET.tostring(result).decode()}'"
                )

        pkgs = []
        for pkg in result:
            if pkg.tag != "status":
                continue

            msg = ""
            for child in pkg:
                if child.tag == "details" and child.text:
                    msg += child.text

            pkg_build_res = PackageBuildResult(
                name=pkg.attrib["package"], code=PackageStatusCode(pkg.attrib["code"])
            )
            if msg:
                pkg_build_res.detail_message = msg
            pkgs.append(pkg_build_res)

        build_res = RepositoryBuildResult(
            project=attr["project"],
            repository=attr["repository"],
            arch=Arch(attr["arch"]),
            code=attr["code"],
            state=attr["state"],
            packages=pkgs,
        )

        if "dirty" in attr:
            build_res.dirty = attr["dirty"] == "true"

        return build_res

    @staticmethod
    def from_resultlist(obs_api_reply: str) -> "list[RepositoryBuildResult]":
        """Creates a list of :py:class`RepositoryBuildResult` from the xml API reply
        received from OBS via :command:`osc results --xml`.

        """
        tree = ET.fromstring(obs_api_reply)
        build_results = []

        for result in tree:
            if result.tag == "result":
                build_results.append(RepositoryBuildResult._from_result(result))

        return build_results


def _get_package_live_log_url(
    project_name: str,
    package_name: str,
    repository_name: str,
    repository_architecture: Arch,
    base_url: str = "https://build.opensuse.org/",
) -> str:
    base = base_url if base_url[-1] != "/" else base_url[:-1]

    return f"{base}/package/live_build_log/{project_name}/{package_name}/{repository_name}/{repository_architecture}"


def is_build_failed(build_results: list[RepositoryBuildResult]) -> bool:
    """Returns ``True`` if any package in the list of build results is either
    unresolvable or failed to build. The repositories must **not** be dirty,
    otherwise a :py:class:`ValueError` is raised.

    """
    for build_res in build_results:
        if build_res.dirty:
            raise ValueError(
                f"Repository {build_res.repository} for {build_res.project} and {build_res.arch} must not be dirty"
            )

        for pkg_res in build_res.packages:
            assert pkg_res.code in (
                PackageStatusCode.EXCLUDED,
                PackageStatusCode.FAILED,
                PackageStatusCode.SUCCEEDED,
                PackageStatusCode.UNRESOLVABLE,
            ), f"package {pkg_res.name} (from repository {build_res.repository} for {build_res.project} and {build_res.arch}) has unfinished state {pkg_res.code}"

            if pkg_res.code in (
                PackageStatusCode.FAILED,
                PackageStatusCode.UNRESOLVABLE,
            ):
                return True

    return False


def render_as_markdown(
    results: list[RepositoryBuildResult], base_url: str = "https://build.opensuse.org/"
) -> str:
    try:
        if is_build_failed(results):
            build_res = "Build failed ❌"
        else:
            build_res = "Build succeeded ✅"
    except ValueError:
        build_res = "Still building 🛻"

    res = f"""
{build_res}
<details>
<summary>Build Results</summary>

"""

    for repo_res in results:
        res += (
            f"Repository `{repo_res.repository}` in "
            + f"[{repo_res.project}]({get_obs_project_url(repo_res.project, base_url)})"
            + f" for `{repo_res.arch}`: current state: {repo_res.state}"
        )
        if repo_res.dirty:
            res += " (repository is **dirty**)"

        res += "\n"
        if not repo_res.packages:
            res += "No packages\n"
        else:
            no_detail = all(not pkg.detail_message for pkg in repo_res.packages)

            res += f"""Build results:
package name | status {'' if no_detail else '| detail '}| build log
-------------|--------{'' if no_detail else '|--------'}|----------
"""
            for package_res in repo_res.packages:
                if no_detail:
                    assert not package_res.detail_message
                    detail = ""
                elif package_res.detail_message:
                    detail = f" {package_res.detail_message} |"
                else:
                    detail = " |"

                res += (
                    f"""{package_res.name} | {package_res.code.pretty_print()} |"""
                    + detail
                    + f""" [live log]({_get_package_live_log_url(repo_res.project, package_res.name, repo_res.repository, repo_res.arch, base_url)})
"""
                )
        res += "\n"

    return (
        res
        + f"""
</details>

{build_res}
"""
    )
