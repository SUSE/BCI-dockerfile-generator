import asyncio
import itertools
import os
import random
import string
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from functools import reduce
from typing import Callable
from typing import ClassVar
from typing import Coroutine
from typing import Generator
from typing import Iterable
from typing import Literal
from typing import TypedDict

import aiofiles.os
import aiofiles.tempfile
import aiohttp
import git
from bci_build.logger import LOGGER
from bci_build.package import ALL_CONTAINER_IMAGE_NAMES
from bci_build.package import BaseContainerImage
from bci_build.package import OsVersion
from bci_build.update import get_bci_project_name
from dotnet.updater import DOTNET_IMAGES
from dotnet.updater import DotNetBCI
from obs_package_update.util import CommandError
from obs_package_update.util import CommandResult
from obs_package_update.util import retry_async_run_cmd
from obs_package_update.util import RunCommand
from staging.build_result import Arch
from staging.build_result import PackageBuildResult
from staging.build_result import PackageStatusCode
from staging.build_result import RepositoryBuildResult
from staging.user import User
from staging.util import ensure_absent
from staging.util import get_obs_project_url

_CONFIG_T = Literal["meta", "prjconf"]
_CONF_TO_ROUTE: dict[_CONFIG_T, str] = {"meta": "_meta", "prjconf": "_config"}


_DEFAULT_REPOS = ["images", "containerfile"]

#: environment variable name from which the osc username for the bot is read
OSC_USER_ENVVAR_NAME = "OSC_USER"

BRANCH_NAME_ENVVAR_NAME = "BRANCH_NAME"

OS_VERSION_ENVVAR_NAME = "OS_VERSION"

#: environment variable from which the password of the bot's user is taken
OSC_PASSWORD_ENVVAR_NAME = "OSC_PASSWORD"

_GIT_COMMIT_ENV = {
    "GIT_COMMITTER_NAME": "SUSE Update Bot",
    "GIT_COMMITTER_EMAIL": "bci-internal@suse.de",
}


async def _fetch_bci_devel_project_config(
    os_version: OsVersion, config_type: _CONFIG_T = "prjconf"
) -> str:
    """Fetches the prjconf for the specified ``os_version``"""
    prj_name = get_bci_project_name(os_version, build_service_target="obs")

    route = f"https://api.opensuse.org/public/source/{prj_name}/{_CONF_TO_ROUTE[config_type]}"

    async with aiohttp.ClientSession() as session:
        async with session.get(route) as response:
            return await response.text()


class _ProjectConfigs(TypedDict):
    meta: ET.Element
    prjconf: str


@dataclass
class StagingBot:
    """Bot that creates a staging project for the BCI images in the Open Build
    Service via the git scm bridge.

    This bot creates a new worktree based on the "deployment branch" (see
    :py:attr:`deployment_branch_name`) and writes all build recipes into it. If
    this results in a change, then the changes are committed and pushed to
    github.

    A new staging project with the name :py:attr:`staging_project_name` is then
    created where all packages that were **changed** are inserted via the scm
    bridge.

    The bot needs to know the name of the user as whom it should act. The
    username has to be set via the attribute :py:attr:`osc_username`. This is
    unfortunately necessary, as :command:`osc` does not provide a
    straightforward way how to get the default username...

    Additionally, the bot stores its current settings in an environment file
    (with the file name :py:attr:`DOTENV_FILE_NAME`), which can be either
    sourced directly in bash or used to create an instance of the bot via
    :py:func:`StagingBot.from_env_file`.

    The bot supports running all actions as a user that is not configured in
    :command:`osc`'s configuration file. All you have to do is to set the
    environment variable :py:const:`OSC_PASSWORD_ENVVAR_NAME` to the password of
    the user that is going to be used. The :py:meth:`setup` function will then
    create a temporary configuration file for :command:`osc` and also set
    ``XDG_STATE_HOME`` to a temporary directory so that your local osc
    :file:`cookiejar` is not modified. Both files are cleaned up via
    :py:meth:`teardown`

    """

    #: The operating system for which this instance has been created
    os_version: OsVersion

    #: Name of the branch to which the changes are pushed. If none is provided,
    #: then :py:attr:`deployment_branch_name` is used with a few random
    #: ASCII characters appended.
    branch_name: str = ""

    #: username of the user that will be used to perform the actions by the bot.
    #:
    #: This value must be provided, otherwise the post initialization function
    #: raises an exception.
    osc_username: str = ""

    repositories: list[str] = field(default_factory=lambda: _DEFAULT_REPOS)

    _packages: list[str] | None = None

    _osc_conf_file: str = ""

    _xdg_state_home_dir: tempfile.TemporaryDirectory | None = None

    #: Maximum time to wait for a build to finish.
    #: github actions will run for 6h at most, no point in waiting longer
    MAX_WAIT_TIME_SEC: ClassVar[int] = 6 * 3600

    #: filename of the environment file used to store the bot's settings
    DOTENV_FILE_NAME: ClassVar[str] = "test-build.env"

    _run_cmd: RunCommand = field(default_factory=lambda: RunCommand(logger=LOGGER))

    def __post_init__(self) -> None:
        if not self.branch_name:
            self.branch_name = (
                self.deployment_branch_name
                + "-"
                + "".join(random.choice(string.ascii_letters) for _ in range(5))
            )

        if not self.osc_username:
            raise RuntimeError("osc_username is not set, cannot continue")

    @property
    def _bcis(self) -> Generator[BaseContainerImage, None, None]:
        """Generator yielding all
        :py:class:`~bci_build.package.BaseContainerImage` that have the same
        :py:attr:`~bci_build.package.BaseContainerImage.os_version` as this bot
        instance.

        """
        return (
            bci
            for bci in list(ALL_CONTAINER_IMAGE_NAMES.values()) + DOTNET_IMAGES
            if bci.os_version == self.os_version
        )

    def _generate_project_name(self, prefix: str) -> str:
        assert self.osc_username
        res = f"home:{self.osc_username}:{prefix}:"
        if self.os_version == OsVersion.TUMBLEWEED:
            res += str(self.os_version)
        else:
            res += f"SLE-15-SP{str(self.os_version)}"
        return res

    @property
    def continuous_rebuild_project_name(self) -> str:
        """The name of the continuous rebuild project on OBS."""
        return self._generate_project_name("BCI:CR")

    @property
    def staging_project_name(self) -> str:
        """The name of the staging project on OBS.

        It is constructed as follows:
        ``home:$OSC_USER:BCI:Staging:$OS_VER:$BRANCH`` where:

        - ``OSC_USER``: :py:attr:`osc_username`
        - ``OS_VER``: :py:attr:`os_version`
        - ``BRANCH``: :py:attr:`branch_name`

        """
        return self._generate_project_name("BCI:Staging") + ":" + self.branch_name

    @property
    def staging_project_url(self) -> str:
        """URL to the staging project."""
        return get_obs_project_url(self.staging_project_name)

    @property
    def deployment_branch_name(self) -> str:
        """The name of the branch for this :py:attr:`~StagingBot.os_version`
        where the build recipes are checked out by default.

        """
        return (
            str(self.os_version)
            if self.os_version == OsVersion.TUMBLEWEED
            else f"sle15-sp{str(self.os_version)}"
        )

    @property
    def package_names(self) -> list[str] | None:
        """Name of the packages in the staging project or ``None`` if the
        staging project has not been setup yet.

        """
        return self._packages

    @package_names.setter
    def package_names(self, pkgs: list[str] | None) -> None:
        bci_pkg_names = [bci.package_name for bci in self._bcis]
        if pkgs is not None:
            for pkg in pkgs:
                if pkg not in bci_pkg_names:
                    raise ValueError(
                        f"Invalid package name {pkg}, does not belong to the current os_version ({self.os_version})"
                    )

        self._packages = pkgs

    @property
    def bcis(self) -> Generator[BaseContainerImage, None, None]:
        """Generator for creating an iterable yielding all
        :py:class:`~bci_build.package.BaseContainerImage` that are in the bot's
        staging project.

        """
        return (
            bci
            for bci in self._bcis
            if (
                bci.package_name in self._packages
                if self._packages is not None
                else True
            )
        )

    @staticmethod
    def from_github_comment(comment_text: str, osc_username: str) -> "StagingBot":
        if comment_text == "":
            raise ValueError("Received empty github comment, cannot create the bot")
        # comment_text looks like this:
        # Created a staging project on OBS for 4: [home:defolos:BCI:Staging:SLE-15-SP4:sle15-sp4-HsmtR](url/to/proj)
        # Changes pushed to branch [`sle15-sp4-HsmtR`](url/to/branch)
        lines = comment_text.strip().splitlines()
        proj_line = lines[0]
        CREATED_TEXT = "Created a staging project on OBS for "
        if CREATED_TEXT not in proj_line:
            raise ValueError(f"Invalid first line in the comment: {comment_text}")
        os_ver, prj_markdown_link = proj_line.replace(CREATED_TEXT, "").split(": ")

        CHANGES_TEXT = "Changes pushed to branch "
        branch_line = lines[1]
        if CHANGES_TEXT not in branch_line:
            raise ValueError(f"Invalid second line in the comment: {comment_text}")
        branch_link_markdown = branch_line.replace(CHANGES_TEXT, "")
        branch = branch_link_markdown.split("`]")[0].replace("[`", "")

        bot = StagingBot(
            os_version=OsVersion.parse(os_ver),
            branch_name=branch,
            osc_username=osc_username,
        )

        assert bot.staging_project_name == (
            prj := prj_markdown_link.split("]")[0].replace("[", "")
        ), f"Mismatch between the constructed project name ({bot.staging_project_name}) and the project name from the comment ({prj})"
        return bot

    @staticmethod
    async def from_env_file() -> "StagingBot":
        """Read the last saved settings from the environment file
        (:py:attr:`~StagingBot.DOTENV_FILE_NAME`) in the current working
        directory and create a :py:class:`StagingBot` from them.

        """
        async with aiofiles.open(StagingBot.DOTENV_FILE_NAME, "r") as dot_env:
            env_file = await dot_env.read()

        branch, os_version, _, osc_username, _, _, _, repos, pkgs = [
            line.split("=")[1] for line in env_file.strip().splitlines()
        ]
        packages: list[str] | None = None if pkgs == "None" else pkgs.split(",")
        stg_bot = StagingBot(
            os_version=OsVersion.parse(os_version),
            osc_username=osc_username,
            branch_name=branch,
            repositories=repos.split(","),
        )

        stg_bot.package_names = packages
        return stg_bot

    @property
    def obs_workflows_yml(self) -> str:
        """The contents of :file:`.obs/workflows.yml` for branching each package
        from the continuous rebuild project
        (:py:attr:`~StagingBot.continuous_rebuild_project_name`) to the staging
        sub-project.

        """
        workflows = """---
staging_build:
  steps:
"""
        source_project = self.continuous_rebuild_project_name
        for bci in self._bcis:
            workflows += f"""    - branch_package:
        source_project: {source_project}
        source_package: {bci.package_name}
        target_project: {source_project}:Staging
"""
        workflows += """  filters:
    event: pull_request

refresh_devel_BCI:
  steps:
"""
        devel_prj = get_bci_project_name(self.os_version)
        for bci in self._bcis:
            workflows += f"""    - trigger_services:
        project: {devel_prj}
        package: {bci.package_name}
"""

        workflows += f"""  filters:
    event: push
    branches:
      only:
        - {self.deployment_branch_name}
"""
        return workflows

    @property
    def changelog_check_github_action(self) -> str:
        return (
            r"""---
name: Check the changelogs

on:
  pull_request:

jobs:
  changelog-check:
    name: changelog check
    runs-on: ubuntu-22.04
    container: ghcr.io/dcermak/bci-ci:latest

    steps:
      - uses: actions/checkout@v3
        with:
          ref: main
          fetch-depth: 0

      - uses: actions/cache@v3
        with:
          path: ~/.cache/pypoetry/virtualenvs
          key: poetry-${{ hashFiles('poetry.lock') }}

      - name: install python dependencies
        run: poetry install

      - name: fix the file permissions of the repository
        run: chown -R $(id -un):$(id -gn) .

      - name: fetch all branches
        run: git fetch

      - name: check the changelog
        run: |
          poetry run ./scratch-build-bot.py \
              --os-version """
            + str(self.os_version)
            + r""" -vvvv \
              changelog_check \
                  --base-ref origin/${{ github.base_ref }} \
                  --head-ref ${{ github.event.pull_request.head.sha }}
        env:
          OSC_USER: "irrelevant"
"""
        )

    @property
    def find_missing_packages_action(self) -> str:
        return (
            r"""---
name: Check whether packages are missing on OBS

on:
  push:
    branches:
      - '"""
            + self.deployment_branch_name
            + """'

jobs:
  create-issues-for-dan:
    name: create an issue for Dan to create the packages in devel:BCI
    runs-on: ubuntu-latest
    container: ghcr.io/dcermak/bci-ci:latest

    strategy:
      fail-fast: false

    steps:
      # we need all branches for the build checks
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
          ref: main
          token: ${{ secrets.CHECKOUT_TOKEN }}

      - uses: actions/cache@v3
        with:
          path: ~/.cache/pypoetry/virtualenvs
          key: poetry-${{ hashFiles('poetry.lock') }}

      - name: fix the file permissions of the repository
        run: chown -R $(id -un):$(id -gn) .

      - name: install python dependencies
        run: poetry install

      - name: find the packages that are missing
        run: |
          pkgs=$(poetry run ./scratch-build-bot.py --os-version """
            + str(self.os_version)
            + """ find_missing_packages)
          if [[ ${pkgs} = "" ]]; then
              echo "missing_pkgs=false" >> $GITHUB_ENV
          else
              echo "missing_pkgs=true" >> $GITHUB_ENV
              echo "pkgs=${pkgs}" >> $GITHUB_ENV
          fi
          cat test-build.env >> $GITHUB_ENV
        env:
          OSC_PASSWORD: ${{ secrets.OSC_PASSWORD }}
          OSC_USER: "defolos"

      - uses: JasonEtco/create-an-issue@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          update_existing: true
          filename: ".github/create-package.md"
        if: env.missing_pkgs == 'true'
"""
        )

    async def setup(self) -> None:
        if pw := os.getenv(OSC_PASSWORD_ENVVAR_NAME):
            osc_conf = tempfile.NamedTemporaryFile("w", delete=False)
            osc_conf.write(
                f"""[general]
apiurl = https://api.opensuse.org
[https://api.opensuse.org]
user = {self.osc_username}
pass = {pw}
aliases = obs
"""
            )
            osc_conf.flush()
            self._osc_conf_file = osc_conf.name

            self._xdg_state_home_dir = tempfile.TemporaryDirectory()
            self._run_cmd = RunCommand(
                logger=LOGGER, env={"XDG_STATE_HOME": self._xdg_state_home_dir.name}
            )

        await self.write_env_file()

    async def write_env_file(self):
        async with aiofiles.open(self.DOTENV_FILE_NAME, "w") as dot_env:
            await dot_env.write(
                f"""{BRANCH_NAME_ENVVAR_NAME}={self.branch_name}
{OS_VERSION_ENVVAR_NAME}={self.os_version}
OS_VERSION_PRETTY={self.os_version.pretty_print}
{OSC_USER_ENVVAR_NAME}={self.osc_username}
DEPLOYMENT_BRANCH_NAME={self.deployment_branch_name}
PROJECT_NAME={self.staging_project_name}
PROJECT_URL={self.staging_project_url}
REPOSITORIES={','.join(self.repositories)}
PACKAGES={','.join(self.package_names) if self.package_names else None}
"""
            )

    async def teardown(self) -> None:
        """Local cleanup after the bot (nothing on OBS is removed and the git
        repository itself is left untouched).

        """
        if self._osc_conf_file:
            await aiofiles.os.remove(self._osc_conf_file)

            assert self._xdg_state_home_dir is not None

            tasks = []
            for suffix in ("", ".lock"):
                tasks.append(
                    ensure_absent(
                        os.path.join(
                            self._xdg_state_home_dir.name, "osc", f"cookiejar{suffix}"
                        )
                    )
                )
            await asyncio.gather(*tasks)
            await ensure_absent(os.path.join(self._xdg_state_home_dir.name, "osc"))
            self._xdg_state_home_dir.cleanup()

    @property
    def _osc(self) -> str:
        """command to invoke osc (may include a CLI flag for the custom config file)"""
        return (
            "osc" if not self._osc_conf_file else f"osc --config={self._osc_conf_file}"
        )

    async def _generate_test_project_meta(self, target_project_name: str) -> ET.Element:
        bci_devel_meta = ET.fromstring(
            await _fetch_bci_devel_project_config(self.os_version, "meta")
        )

        # write the same project meta as devel:BCI, but replace the 'devel:BCI:*'
        # with the target project name in the main element and in all repository
        # path entries
        bci_devel_meta.attrib["name"] = target_project_name

        # we will remove the helmchartsrepo as we do not need it
        repo_names = []
        repos_to_remove = []

        # ppc64le & s390x are mostly busted on TW and just cause pointless
        # build failures, so we don't build them
        # Also, we don't use the local architecture, so drop that one always
        arches_to_drop = [str(Arch.LOCAL)]
        arches_to_drop.extend(
            [str(Arch.PPC64LE), str(Arch.S390X)]
            if self.os_version == OsVersion.TUMBLEWEED
            else []
        )

        for elem in bci_devel_meta:
            if elem.tag == "repository":
                if "name" in elem.attrib:
                    if (name := elem.attrib["name"]) in ("helmcharts", "standard"):
                        if name == "helmcharts":
                            repos_to_remove.append(elem)
                        continue

                    repo_names.append(name)
                else:
                    raise ValueError(
                        f"Invalid <repository> element, missing 'name' attribute: {ET.tostring(elem).decode()}"
                    )

                for repo_elem in elem.iter(tag="path"):
                    if (
                        "project" in repo_elem.attrib
                        and "devel:BCI:" in repo_elem.attrib["project"]
                    ):
                        repo_elem.attrib["project"] = target_project_name

                arch_entries = list(elem.iter(tag="arch"))
                for arch_entry in arch_entries:
                    if arch_entry.text in arches_to_drop:
                        elem.remove(arch_entry)

        self.repositories = repo_names
        for repo_to_remove in repos_to_remove:
            bci_devel_meta.remove(repo_to_remove)

        person = ET.Element(
            "person", {"userid": self.osc_username, "role": "maintainer"}
        )
        bci_devel_meta.append(person)

        return bci_devel_meta

    async def _send_prj_meta(
        self, target_project_name: str, prj_meta: ET.Element
    ) -> None:
        """Set the meta of the project on OBS with the name
        ``target_project_name`` to the config ``prj_meta``.

        """
        async with aiofiles.tempfile.NamedTemporaryFile(mode="wb") as tmp_meta:
            await tmp_meta.write(ET.tostring(prj_meta))
            await tmp_meta.flush()

            async def _send_prj_meta():
                await self._run_cmd(
                    f"{self._osc} meta prj --file={tmp_meta.name} {target_project_name}"
                )

            # obs sometimes dies setting the project meta with SQL errors 🤯
            # so we just try again…
            await retry_async_run_cmd(_send_prj_meta)

    async def write_cr_project_config(self) -> None:
        """Send the configuration of the continuous rebuild project to OBS.

        This will create the project if it did not exist already. If it exists,
        then its configuration (= ``meta`` in OBS jargon) will be updated.

        """
        meta = await self._generate_test_project_meta(
            self.continuous_rebuild_project_name
        )
        (
            scmsync := ET.Element("scmsync")
        ).text = f"https://github.com/SUSE/bci-dockerfile-generator#{self.deployment_branch_name}"
        meta.append(scmsync)
        await self._send_prj_meta(self.continuous_rebuild_project_name, meta)

    async def write_staging_project_configs(self) -> None:
        """Submit the ``prjconf`` and ``meta`` to the test project on OBS.

        The ``prjconf`` is taken directly from the development project on OBS
        (``devel:BCI:*``).

        The ``meta`` has to be modified slightly:

        - we remove the ``helmcharts`` repository (we don't create anything for
          that repo, so not worth creating it)
        - change the path from ``devel:BCI:*`` to the staging project name
        - add the bot user as the maintainer (otherwise you can't do anything in
          the project anymore…)

        Then we send the ``meta`` and then the ``prjconf``.
        """
        confs: _ProjectConfigs = {}

        async def _fetch_prjconf():
            confs["prjconf"] = await _fetch_bci_devel_project_config(
                self.os_version, "prjconf"
            )

        async def _fetch_prj():
            confs["meta"] = await self._generate_test_project_meta(
                self.staging_project_name
            )

        await asyncio.gather(_fetch_prj(), _fetch_prjconf())

        # First set the project meta! This will create the project if it does not
        # exist already, if we do it asynchronously, then the prjconf might be
        # written before the project exists, which fails
        await self._send_prj_meta(self.staging_project_name, confs["meta"])

        async with aiofiles.tempfile.NamedTemporaryFile(mode="w") as tmp_prjconf:
            await tmp_prjconf.write(confs["prjconf"])
            await tmp_prjconf.flush()
            await self._run_cmd(
                f"{self._osc} meta prjconf --file={tmp_prjconf.name} {self.staging_project_name}"
            )

    def _osc_fetch_results_cmd(self, extra_osc_flags: str = "") -> str:
        return (
            f"{self._osc} results --xml {extra_osc_flags} "
            + " ".join("--repo=" + repo_name for repo_name in self.repositories)
            + f" {self.staging_project_name}"
        )

    async def remote_cleanup(
        self, branches: bool = True, obs_project: bool = True
    ) -> None:
        """Deletes the branch with the test commit locally and on the remote and
        removes the staging project.

        All performed actions are permitted to fail without raising an exception
        to ensure that a partially setup test run is cleaned up as much as
        possible.

        Args:
            branches: if ``True``, removes the branch locally and on the remote
                (defaults to ``True``)
            obs_project: if ``True``, removes the staging project on OBS
                (defaults to ``True``)

        """

        async def remove_branch():
            await self._run_cmd(
                f"git branch -D {self.branch_name}", raise_on_error=False
            )
            await self._run_cmd(
                f"git push origin -d {self.branch_name}", raise_on_error=False
            )

        tasks = []
        if branches:
            tasks.append(remove_branch())
        if obs_project:
            tasks.append(
                self._run_cmd(
                    f"{self._osc} rdelete -m 'cleanup' --recursive --force {self.staging_project_name}",
                    raise_on_error=False,
                )
            )

        await asyncio.gather(*tasks)

    async def _write_pkg_meta(
        self, bci_pkg: BaseContainerImage, target_obs_project: str, git_branch_name
    ) -> None:
        """Write the package ``_meta`` of the package with the name of the
        ``bci_pkg`` in the ``target_obs_project`` to be synced from the git
        branch ``git_branch_name``.

        """
        (pkg_conf := ET.Element("package")).attrib["name"] = bci_pkg.package_name

        (title := ET.Element("title")).text = bci_pkg.title
        (descr := ET.Element("description")).text = bci_pkg.description
        (
            scmsync := ET.Element("scmsync")
        ).text = f"https://github.com/SUSE/bci-dockerfile-generator?subdir={bci_pkg.package_name}#{git_branch_name}"

        for elem in (title, descr, scmsync):
            pkg_conf.append(elem)

        async with aiofiles.tempfile.NamedTemporaryFile(mode="w") as tmp_pkg_conf:
            await tmp_pkg_conf.write(ET.tostring(pkg_conf).decode())
            await tmp_pkg_conf.flush()
            await self._run_cmd(
                f"{self._osc} meta pkg --file={tmp_pkg_conf.name} {target_obs_project} {bci_pkg.package_name}"
            )

    async def write_pkg_configs(
        self,
        packages: Iterable[BaseContainerImage],
        git_branch_name: str,
        target_obs_project: str,
    ) -> None:
        """Write all package configurations (= :file:`_meta`) for every package
        in ``packages`` to the project `target_obs_project` so that the package
        is fetched via the scm bridge from the branch `git_branch_name`.

        Args:
            packages: the BCI packages that should be added
            git_branch_name: the name of the git branch from which the sources
                will be retrieved
            target_obs_project: name of the project on OBS to which the packages
                will be added

        """
        tasks = []

        for bci in packages:
            tasks.append(
                self._write_pkg_meta(
                    bci,
                    git_branch_name=git_branch_name,
                    target_obs_project=target_obs_project,
                )
            )

        await asyncio.gather(*tasks)

    def _get_changed_packages_by_commit(self, commit: str | git.Commit) -> list[str]:
        git_commit = (
            commit if isinstance(commit, git.Commit) else git.Repo(".").commit(commit)
        )

        bci_pkg_names = [bci.package_name for bci in self.bcis]
        packages = []

        # get the diff between the commit and the deployment branch on the remote
        # => list of changed files
        #    each file's first path element is the package name -> save that in
        #    `packages`
        for diff in git_commit.diff(f"origin/{self.deployment_branch_name}"):
            # no idea how this could happen, but in theory the diff mode can be
            # `C` for conflict => abort if that's the case
            assert (
                diff.a_mode != "C" and diff.b_mode != "C"
            ), f"diff must not be a conflict, but got {diff=}"

            if (
                (a_path := os.path.split(diff.a_path))
                and a_path[0] in bci_pkg_names
                and (b_path := os.path.split(diff.b_path))
                and b_path[0] in bci_pkg_names
            ):
                packages.append(a_path[0])

                # account for files getting moved
                if b_path[0] != a_path[0]:
                    packages.append(b_path[0])

        res = list(set(packages))

        # it can happen that we only update a non-BCI package file,
        # e.g. .obs/workflows.yml, then we will have a commit, but the diff will
        # not touch any BCI and thus `res` will be an empty list
        # => give reduce an initial value (last parameter) as it will otherwise
        #    fail
        assert reduce(lambda l, r: l and r, (p in bci_pkg_names for p in res), True)
        return res

    async def _run_git_action_in_worktree(
        self,
        new_branch_name: str,
        origin_branch_name: str,
        action: Callable[[str], Coroutine[None, None, bool]],
    ) -> str | None:
        assert not origin_branch_name.startswith("origin/")
        await self._run_cmd(
            f"git worktree add -B {new_branch_name} {new_branch_name} origin/{origin_branch_name}"
        )
        worktree_dir = os.path.join(os.getcwd(), new_branch_name)
        commit = None
        try:
            if await action(worktree_dir):
                commit = (
                    await self._run_cmd(
                        "git show -s --pretty=format:%H HEAD", cwd=worktree_dir
                    )
                ).stdout.strip()
                LOGGER.info("Created commit %s given the current state", commit)

                await self._run_cmd(
                    f"git pull --rebase origin {origin_branch_name}",
                    cwd=worktree_dir,
                    env={**_GIT_COMMIT_ENV, **os.environ},
                )
                await self._run_cmd(
                    "git push --force-with-lease origin HEAD", cwd=worktree_dir
                )

        finally:
            await self._run_cmd(f"git worktree remove --force {new_branch_name}")

        return commit

    async def write_all_build_recipes_to_branch(
        self, commit_msg: str = ""
    ) -> str | None:
        """Creates a worktree for the branch based on the deployment branch of
        this :py:attr:`~StagingBot.os_version`, writes all image build recipes
        into it, commits and then pushes the changes. Afterwards the worktree is
        removed.

        Returns:
            The hash of the commit including all changes by the writing the
            build recipes into the worktree. If no changes were made, then
            ``None`` is returned.

        """

        async def _write_build_recipes_in_worktree(worktree_dir: str) -> bool:
            files = await self.write_all_image_build_recipes(worktree_dir)

            run_in_worktree = RunCommand(cwd=worktree_dir, logger=LOGGER)

            worktree = git.Repo(worktree_dir)
            # no changes => nothing to do & bail
            # note: diff only checks for changes to *existing* packages, but not
            # if anything new got added => need to check if the repo is dirty
            # for that (= is there any output with `git status`) or there any
            # untracked files
            if (
                not worktree.head.commit.diff()
                and not worktree.is_dirty()
                and not worktree.untracked_files
            ):
                LOGGER.info("Writing all build recipes resulted in no changes")
                return False

            await run_in_worktree("git add " + " ".join(files))
            await run_in_worktree(
                f"git commit -m '{commit_msg or 'Test build'}'",
                env={**_GIT_COMMIT_ENV, **os.environ},
            )
            return True

        # we do not want to overwrite any existing changes from the origin which
        # could have been pushed there already

        # is there a origin/self.branch_name?
        branch_commit_hash_on_remote: str | None = None
        try:
            branch_commit_hash_on_remote = (
                git.Repo(".").commit(f"origin/{self.branch_name}").hexsha
            )
        except git.BadName:
            pass

        # yes => check if it is newer than the deployment branch
        commit_range = None
        if branch_commit_hash_on_remote:
            try:
                commit_range = self._get_commit_range_between_refs(
                    branch_commit_hash_on_remote,
                    f"origin/{self.deployment_branch_name}",
                )
            except RecursionError:
                pass

        # it is newer? => base our work on origin/branch_name and not the
        # deployment_branch
        origin_branch = (
            self.deployment_branch_name if not commit_range else self.branch_name
        )
        return await self._run_git_action_in_worktree(
            self.branch_name,
            origin_branch,
            _write_build_recipes_in_worktree,
        )

    async def write_all_image_build_recipes(
        self, destination_prj_folder: str
    ) -> list[str]:
        """Writes all build recipes into the folder
        :file:`destination_prj_folder` and returns a list of files that were
        written.

        Returns:
            A list of all files that were written to
            :file:`destination_prj_folder`. The files are listed relative to
            :file:`destination_prj_folder` and don't contain any leading path
            components.

        """
        tasks: list[Coroutine[None, None, list[str]]] = []

        await aiofiles.os.makedirs(destination_prj_folder, exist_ok=True)

        for bci in self.bcis:

            async def write_files(bci_pkg: BaseContainerImage, dest: str) -> list[str]:
                await aiofiles.os.makedirs(dest, exist_ok=True)

                # remove everything *but* the changes file (.changes is not
                # autogenerated) so that we properly remove files that were dropped
                to_remove = []
                for fname in await aiofiles.os.listdir(dest):
                    if fname == f"{bci_pkg.package_name}.changes":
                        continue
                    to_remove.append(aiofiles.os.remove(os.path.join(dest, fname)))

                await asyncio.gather(*to_remove)

                if isinstance(bci_pkg, DotNetBCI):
                    bci_pkg.generate_custom_end()

                return [
                    f"{bci_pkg.package_name}/{fname}"
                    for fname in await bci_pkg.write_files_to_folder(dest)
                ]

            img_dest_dir = os.path.join(destination_prj_folder, bci.package_name)
            tasks.append(write_files(bci, img_dest_dir))

        async def write_obs_workflows_yml() -> list[str]:
            await aiofiles.os.makedirs(
                (dot_obs := os.path.join(destination_prj_folder, ".obs")), exist_ok=True
            )
            async with aiofiles.open(
                os.path.join(dot_obs, "workflows.yml"), "w"
            ) as workflows_file:
                await workflows_file.write(self.obs_workflows_yml)
            return [".obs/workflows.yml"]

        async def write_github_actions() -> list[str]:
            await aiofiles.os.makedirs(
                (
                    github_workflows := os.path.join(
                        destination_prj_folder, ".github", "workflows"
                    )
                ),
                exist_ok=True,
            )

            actions = []
            for fname, contents in (
                ("changelog_checker.yml", self.changelog_check_github_action),
                ("find-missing-packages.yml", self.find_missing_packages_action),
            ):
                async with aiofiles.open(
                    os.path.join(github_workflows, fname), "w"
                ) as workflows_file:
                    await workflows_file.write(contents)
                actions.append(fname)

            async with aiofiles.open(
                os.path.join(destination_prj_folder, ".github", "dependabot.yml"), "w"
            ) as dependabot_yml:
                await dependabot_yml.write(
                    """---
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
"""
                )

            return [f".github/workflows/{fname}" for fname in actions] + [
                ".github/dependabot.yml"
            ]

        async def write_underscore_config() -> list[str]:
            prjconf = await _fetch_bci_devel_project_config(self.os_version, "prjconf")
            async with aiofiles.open(
                os.path.join(destination_prj_folder, "_config"), "w"
            ) as conf:
                await conf.write(prjconf)

            return ["_config"]

        tasks.append(write_obs_workflows_yml())
        tasks.append(write_underscore_config())
        tasks.append(write_github_actions())

        files = await asyncio.gather(*tasks)
        flattened_file_list = []
        for file_list in files:
            flattened_file_list.extend(file_list)
        return flattened_file_list

    async def fetch_build_results(self) -> list[RepositoryBuildResult]:
        """Retrieves the current build results of the staging project."""
        return RepositoryBuildResult.from_resultlist(
            (await self._run_cmd(self._osc_fetch_results_cmd())).stdout
        )

    async def force_rebuild(self) -> str:
        """Deletes all binaries of the project on OBS and force rebuilds everything."""
        await self._run_cmd(
            f"{self._osc} wipebinaries --all {self.staging_project_name}"
        )
        await self._run_cmd(f"{self._osc} rebuild --all {self.staging_project_name}")
        return self._osc_fetch_results_cmd("--watch")

    async def scratch_build(self, commit_message: str = "") -> None | str:
        # no commit -> no changes -> no reason to build
        if not (commit := await self.write_all_build_recipes_to_branch(commit_message)):
            return None

        self.package_names = self._get_changed_packages_by_commit(commit)
        if not self.package_names:
            return None

        LOGGER.debug(
            "packages that were changed by %s: %s",
            commit,
            ", ".join(self.package_names),
        )
        await self.write_staging_project_configs()
        await self.write_pkg_configs(
            self.bcis,
            git_branch_name=self.branch_name,
            target_obs_project=self.staging_project_name,
        )
        await self._wait_for_all_pkg_service_runs()

        # "encourage" OBS to rebuild, in case this project existed before
        await asyncio.gather(self.force_rebuild(), self.write_env_file())

        return commit

    async def _wait_for_all_pkg_service_runs(self) -> None:
        """Run :command:`osc service wait` for all packages in the staging
        project.

        """
        if self.package_names is None:
            raise RuntimeError("No packages have been set yet, cannot continue")
        # we wait for the service sequentially here. if we wait for all of them
        # in parallel, we can easily grab all wait slots that obs has
        for pkg_name in self.package_names:
            await self._run_cmd(
                f"{self._osc} service wait {self.staging_project_name} {pkg_name}"
            )

    async def wait_for_build_to_finish(
        self, timeout_sec: int | None = None
    ) -> list[RepositoryBuildResult]:
        """Blocks until all builds in the staging project have finished and the
        repositories are no longer dirty.

        Args:
            timeout_sec: Total time in seconds to block. Defaults to
                :py:attr:`~StagingBot.MAX_WAIT_TIME_SEC`


        Raises:
            :py:class:`asyncio.TimeoutError`: when build takes longer than the
                specified timeout

            :py:class:`RuntimeError`: when the staging project has no build
                results (this is most likely an issue with OBS)


        Returns:
            The last state of all packages in the staging project after the
            builds finished

        """

        start = datetime.now()

        # OBS can be sometimes a bit slow with figuring out that there are
        # packages to be build or with starting some builds that need to fetch
        # remote assets
        # It will then just give us an empty list of packages for all repos if
        # we call the `/results/` route fast enough after project setup or even
        # worse, it will figure out that our problematic packages are excluded
        # in some repos, but have not been added to others. I.e. we have to
        # remove excluded packages from our list as well
        #
        # If that happens (=> Σ packages == 0), when we wait for 60s and try
        # again (and repeat this up to 10 times). If OBS hasn't managed to do
        # *anything* by then, just bail…
        def _get_number_of_packages_with_results(
            build_result_list: list[RepositoryBuildResult],
        ) -> int:
            all_pkg_results: list[PackageBuildResult] = [
                pkg_res
                for pkg_res in itertools.chain.from_iterable(
                    result.packages for result in build_result_list
                )
                if pkg_res.code
                not in (PackageStatusCode.EXCLUDED, PackageStatusCode.SCHEDULED)
            ]
            return len(all_pkg_results)

        def _dirty_repos_present(
            build_result_list: Iterable[RepositoryBuildResult],
        ) -> bool:
            for build_res in build_result_list:
                if build_res.dirty:
                    return True
            return False

        build_res: list[RepositoryBuildResult] = []
        retries = 0
        while True:

            def is_execution_time_exceeded() -> bool:
                return (datetime.now() - start).total_seconds() > (
                    timeout_sec or self.MAX_WAIT_TIME_SEC
                )

            # We face the problem that `osc results --watch` stops reading after
            # a while and just does nothing until all eternity.
            # So we instead set the timeout of the watch command to 5 minutes
            # and thereby periodically kill it. If the time is not yet up, we
            # jest restart the whole thing again.
            while not is_execution_time_exceeded():
                try:
                    timeout = timedelta(
                        seconds=min(
                            5 * 60,
                            # total timeout - elapsed seconds
                            (timeout_sec or self.MAX_WAIT_TIME_SEC)
                            - (datetime.now() - start).total_seconds(),
                        )
                    )
                    LOGGER.debug(
                        "will watch the repository for results for %s",
                        timeout.total_seconds(),
                    )
                    await self._run_cmd(
                        self._osc_fetch_results_cmd("--watch"), timeout=timeout
                    )
                    # if we got here, then osc result --watch successfully
                    # finished
                    break
                except asyncio.TimeoutError:
                    if is_execution_time_exceeded():
                        raise
                except CommandError as cmd_err:
                    if (
                        "SSL Error: (104, 'Connection reset by peer')"
                        in cmd_err.command_result.stderr
                    ) or (
                        "[Errno 101] Network is unreachable"
                        in cmd_err.command_result.stderr
                    ):
                        LOGGER.debug("SSL Connection to OBS broke, retrying...")
                    else:
                        raise

            build_res = await self.fetch_build_results()
            if (
                _get_number_of_packages_with_results(build_res) == 0
                or _dirty_repos_present(build_res)
            ) and retries < 10:
                LOGGER.debug(
                    "got 0 packages with build results or a dirty repository, sleeping and retrying"
                )
                retries += 1
                await asyncio.sleep(60)
            else:
                break

        if _get_number_of_packages_with_results(build_res) == 0:
            raise RuntimeError(
                f"{self.staging_project_name} has no packages with build results, something is broken ⚡"
            )

        if _dirty_repos_present(build_res):
            raise RuntimeError(f"{self.staging_project_name} is still dirty!")

        return build_res

    async def _fetch_user(self, username: str) -> User:
        return User.from_xml(
            (await self._run_cmd(f"{self._osc} api /person/{username}")).stdout
        )

    def _get_commit_range_between_refs(
        self, child_ref: str, ancestor_ref: str
    ) -> list[git.Commit] | None:
        repo = git.Repo(".")
        ancestor_commit = repo.commit(ancestor_ref)
        child_commit = repo.commit(child_ref)

        def _recurse_search_for_ancestor(
            commit: git.Commit, ancestor: git.Commit
        ) -> list[git.Commit] | None:
            for parent in commit.parents:
                if parent == ancestor:
                    return [parent]

                if hist := _recurse_search_for_ancestor(parent, ancestor):
                    return [parent] + hist

            return None

        commits = _recurse_search_for_ancestor(child_commit, ancestor_commit)
        if not commits:
            return None
        return [child_commit] + commits

    async def add_changelog_entry(
        self, entry: str, username: str, package_names: list[str] | None
    ) -> str:
        target_branch_name = f"for-deploy-{self.os_version}"
        entry = entry.replace('"', r"\"")

        user = await self._fetch_user(username)

        if not package_names:
            commits = self._get_commit_range_between_refs(
                f"origin/{target_branch_name}", f"origin/{self.deployment_branch_name}"
            )
            if not commits:
                raise RuntimeError(
                    "Could not determine commit range from "
                    f"origin/{target_branch_name} to "
                    f"origin/{self.deployment_branch_name} and no package names "
                    "provided, don't know where to add a changelog."
                )
            package_names = []
            for commit in commits:
                package_names.extend(self._get_changed_packages_by_commit(commit))

            package_names = list(set(package_names))

        if not package_names:
            raise ValueError(
                "No package names were supplied or no packages were changed between "
                f"origin/{target_branch_name} and origin/{self.deployment_branch_name}"
            )

        async def _add_changelog_in_worktree(worktree_dir: str) -> bool:
            assert package_names
            run_in_worktree = RunCommand(
                cwd=worktree_dir,
                logger=LOGGER,
            )
            tasks: list[Coroutine[None, None, CommandResult]] = []
            files = []
            for package_name in package_names:
                fname = f"{package_name}/{package_name}.changes"
                tasks.append(
                    run_in_worktree(
                        f'/usr/lib/build/vc -m "{entry}" {package_name}.changes',
                        env={"VC_REALNAME": user.realname, "VC_MAILADDR": user.email},
                        cwd=os.path.join(worktree_dir, package_name),
                    )
                )
                files.append(fname)

            await asyncio.gather(*tasks)
            await run_in_worktree("git add " + " ".join(files))

            commit_msg = (
                f"Update changelog for {package_names[0]}"
                if len(package_names) == 1
                else f"Update changelogs for {', '.join(package_names)}"
            )
            await run_in_worktree(
                f"git commit -m '{commit_msg}'",
                env={
                    **_GIT_COMMIT_ENV,
                    "GIT_AUTHOR_NAME": user.realname,
                    "GIT_AUTHOR_EMAIL": user.email,
                    **os.environ,
                },
            )
            return True

        # Just retry appending the changelog multiple times in case there is a
        # push in the mean time
        # Not super elegant, but prevents us from pull & rebase + push a bunch
        # of times manually
        commit = await retry_async_run_cmd(
            lambda: self._run_git_action_in_worktree(
                new_branch_name=target_branch_name,
                origin_branch_name=target_branch_name,
                action=_add_changelog_in_worktree,
            )
        )
        assert commit
        return commit

    def get_packages_without_changelog_addition(
        self, base_ref: str, change_ref: str
    ) -> list[str]:
        """Runs a simple heuristic whether a packages' changelog has had an
        addition between ``base_ref`` and ``change_ref``.

        Returns:
            The list of packages without a commit in the range ``base_ref`` and
            ``change_ref`` that added at least four lines (= minimum length of a
            one line :command:`osc vc` entry).

        """
        commit_range = self._get_commit_range_between_refs(change_ref, base_ref)
        if not commit_range:
            raise RuntimeError(f"{base_ref} is not an ancestor of {change_ref}!")

        packages: set[str] = set()
        for commit in commit_range:
            packages.update(self._get_changed_packages_by_commit(commit))

        package_changelog_appended: dict[str, bool] = {
            package: False for package in packages
        }

        for commit in commit_range:
            for package_name, changelog_appended in package_changelog_appended.items():
                if changelog_appended:
                    continue
                if changes_entry := commit.stats.files.get(
                    f"{package_name}/{package_name}.changes"
                ):
                    if changes_entry["insertions"] >= changes_entry["deletions"] + 4:
                        package_changelog_appended[package_name] = True

        return [
            pkg_name
            for pkg_name, changelog_updated in package_changelog_appended.items()
            if not changelog_updated
        ]

    async def configure_devel_bci_package(self, package_name: str) -> None:
        bci = [b for b in self._bcis if b.package_name == package_name]

        if not bci:
            raise ValueError(
                f"{package_name} is not a valid package name for "
                f"{self.os_version.pretty_print}, expected one of "
                + (", ".join(b.package_name for b in self._bcis))
            )

        assert (
            len(bci) == 1
        ), f"Got {len(bci)} packages with the name {package_name}: {bci}"

        await self._write_pkg_meta(
            bci[0],
            target_obs_project=get_bci_project_name(self.os_version),
            git_branch_name=self.deployment_branch_name,
        )

    async def find_missing_packages_on_obs(self) -> list[str]:
        """Returns the name of all packages that are currently in a git
        deployment branch, but have not been setup on OBS.

        """
        repo = git.Repo(".")
        deployment_branch_head = repo.commit(f"origin/{self.deployment_branch_name}")
        pkgs_in_deployment_branch = set(
            tree.name for tree in deployment_branch_head.tree
        ) - set((".obs", ".github", "_config"))
        pkgs_on_obs = set(
            (
                await self._run_cmd(
                    f"{self._osc} ls {get_bci_project_name(self.os_version, 'obs')}"
                )
            ).stdout.splitlines()
        )

        return list(pkgs_in_deployment_branch - pkgs_on_obs)
