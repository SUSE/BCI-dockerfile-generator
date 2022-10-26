import asyncio
import itertools
import logging
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
from typing import ClassVar
from typing import Generator
from typing import Literal

import aiofiles.os
import aiofiles.tempfile
import aiohttp
import git
from bci_build.package import ALL_CONTAINER_IMAGE_NAMES
from bci_build.package import BaseContainerImage
from bci_build.package import OsVersion
from bci_build.update import get_bci_project_name
from obs_package_update.util import CommandError
from obs_package_update.util import retry_async_run_cmd
from obs_package_update.util import RunCommand
from staging.build_result import Arch
from staging.build_result import PackageBuildResult
from staging.build_result import RepositoryBuildResult
from staging.util import ensure_absent
from staging.util import get_obs_project_url

_CONFIG_T = Literal["meta", "prjconf"]
_CONF_TO_ROUTE: dict[_CONFIG_T, str] = {"meta": "_meta", "prjconf": "_config"}

LOGGER = logging.getLogger(__name__)

_DEFAULT_REPOS = ["images", "containerfile"]

#: environment variable name from which the osc username for the bot is read
OSC_USER_ENVVAR_NAME = "OSC_USER"

BRANCH_NAME_ENVVAR_NAME = "BRANCH_NAME"

OS_VERSION_ENVVAR_NAME = "OS_VERSION"

#: environment variable from which the password of the bot's user is taken
OSC_PASSWORD_ENVVAR_NAME = "OSC_PASSWORD"


async def _fetch_bci_devel_project_config(
    os_version: OsVersion, config_type: _CONFIG_T = "prjconf"
) -> str:
    """Fetches the prjconf for the specified ``os_version``"""
    prj_name = get_bci_project_name(os_version, build_service_target="obs")

    route = f"https://api.opensuse.org/public/source/{prj_name}/{_CONF_TO_ROUTE[config_type]}"

    async with aiohttp.ClientSession() as session:
        async with session.get(route) as response:
            return await response.text()


@dataclass
class StagingBot:
    """Bot that creates a staging project for the BCI images in the Open Build
    Service via the git scm bridge.

    This bot creates a new worktree based on the "deployment branch" (see
    :py:attr:`deployment_branch_name`) and writes all build recipes into it. If
    this results in a change, then the changes are committed and pushed to
    github.

    A new staging project with the name :py:attr:`project_name` is then created
    where all packages that were **changed** are inserted via the scm bridge.

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
    ``XDG_STATE_HOME`` to a temporary directory so that your local osc cookiejar
    is not modified. Both files are cleaned up via :py:meth:`teardown`

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
        return (
            bci
            for bci in ALL_CONTAINER_IMAGE_NAMES.values()
            if bci.os_version == self.os_version
        )

    @property
    def project_name(self) -> str:
        """The name of the staging project on OBS.

        It is constructed as follows:
        ``home:$OSC_USER:BCI:Staging:$OS_VER:$BRANCH`` where:

        - ``OSC_USER``: :py:attr:`osc_username`
        - ``OS_VER``: :py:attr:`os_version`
        - ``BRANCH``: :py:attr:`branch_name`

        """
        assert self.osc_username
        res = f"home:{self.osc_username}:BCI:Staging:"
        if self.os_version == OsVersion.TUMBLEWEED:
            res += str(self.os_version)
        else:
            res += f"SLE-15-SP{str(self.os_version)}"
        return res + ":" + self.branch_name

    @property
    def project_url(self) -> str:
        """URL to the staging project."""
        return get_obs_project_url(self.project_name)

    @property
    def deployment_branch_name(self) -> str:
        """The name of the branch for this :py:attr:`~StagingBot.os_version`
        where the build recipes are checked out by default.

        """
        return (
            str(self.os_version).lower()
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
            for bci in ALL_CONTAINER_IMAGE_NAMES.values()
            if bci.os_version == self.os_version
            and (
                bci.package_name in self._packages
                if self._packages is not None
                else True
            )
        )

    @staticmethod
    def from_github_comment(comment_text: str, osc_username: str) -> "StagingBot":
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

        assert bot.project_name == (
            prj := prj_markdown_link.split("]")[0].replace("[", "")
        ), f"Mismatch between the constructed project name ({bot.project_name}) and the project name from the comment ({prj})"
        return bot

    @staticmethod
    async def from_env_file() -> "StagingBot":
        async with aiofiles.open(StagingBot.DOTENV_FILE_NAME, "r") as dot_env:
            env_file = await dot_env.read()

        branch, os_version, osc_username, _, _, repos, pkgs = [
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
{OSC_USER_ENVVAR_NAME}={self.osc_username}
PROJECT_NAME={self.project_name}
PROJECT_URL={self.project_url}
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
            await ensure_absent(
                os.path.join(self._xdg_state_home_dir.name, "osc", "cookiejar")
            )
            await ensure_absent(os.path.join(self._xdg_state_home_dir.name, "osc"))
            self._xdg_state_home_dir.cleanup()

    @property
    def _osc(self) -> str:
        """command to invoke osc (may include a CLI flag for the custom config file)"""
        return (
            "osc" if not self._osc_conf_file else f"osc --config={self._osc_conf_file}"
        )

    async def write_test_project_configs(self) -> None:
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
        confs: dict[_CONFIG_T, str] = {}

        async def _fetch_prjconf():
            confs["prjconf"] = await _fetch_bci_devel_project_config(
                self.os_version, "prjconf"
            )

        async def _fetch_prj():
            confs["meta"] = await _fetch_bci_devel_project_config(
                self.os_version, "meta"
            )

        await asyncio.gather(_fetch_prj(), _fetch_prjconf())

        bci_devel_meta = ET.fromstring(confs["meta"])

        # First set the project meta! This will create the project if it does not
        # exist already, if we do it asynchronously, then the prjconf might be
        # written before the project exists, which fails

        # write the same project meta as devel:BCI, but replace the 'devel:BCI:*'
        # with the actual project name in the main element and in all repository
        # path entries
        async with aiofiles.tempfile.NamedTemporaryFile(mode="wb") as tmp_meta:
            bci_devel_meta.attrib["name"] = self.project_name

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
                            repo_elem.attrib["project"] = self.project_name

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

            await tmp_meta.write(ET.tostring(bci_devel_meta))
            await tmp_meta.flush()

            async def _send_prj_meta():
                await self._run_cmd(
                    f"{self._osc} meta prj --file={tmp_meta.name} {self.project_name}"
                )

            # obs sometimes dies setting the project meta with SQL errors 🤯
            # so we just try again…
            await retry_async_run_cmd(_send_prj_meta)

        async with aiofiles.tempfile.NamedTemporaryFile(mode="w") as tmp_prjconf:
            await tmp_prjconf.write(confs["prjconf"])
            await tmp_prjconf.flush()
            await self._run_cmd(
                f"{self._osc} meta prjconf --file={tmp_prjconf.name} {self.project_name}"
            )

    def _osc_fetch_results_cmd(self, extra_osc_flags: str = "") -> str:
        return (
            f"{self._osc} results --xml {extra_osc_flags} "
            + " ".join("--repo=" + repo_name for repo_name in self.repositories)
            + f" {self.project_name}"
        )

    async def cleanup_branch_and_project(self) -> None:
        """Deletes the branch with the test commit locally and on the remote and
        removes the staging project.

        All performed actions are permitted to fail without raising an exception
        to ensure that a partially setup test run is cleaned up as much as
        possible.

        """

        async def remove_branch():
            await self._run_cmd(
                f"git branch -D {self.branch_name}", raise_on_error=False
            )
            await self._run_cmd(
                f"git push origin -d {self.branch_name}", raise_on_error=False
            )

        await asyncio.gather(
            remove_branch(),
            self._run_cmd(
                f"{self._osc} rdelete -m 'cleanup' --recursive --force {self.project_name}",
                raise_on_error=False,
            ),
        )

    async def write_pkg_configs(self) -> None:
        """Write all package configurations in the staging project for every
        package in :py:attr:`package_names`.

        Each package is setup using the `scmsync` element to track the
        respective subdirectory in the branch :py:attr:`branch_name`.

        Note: if no packages have been set yet, then this function does **nothing**.

        """
        tasks = []

        for bci in self.bcis:

            async def write_pkg_conf(bci_pkg: BaseContainerImage):
                (pkg_conf := ET.Element("package")).attrib[
                    "name"
                ] = bci_pkg.package_name

                (title := ET.Element("title")).text = bci_pkg.title
                (descr := ET.Element("description")).text = bci_pkg.description
                (
                    scmsync := ET.Element("scmsync")
                ).text = f"https://github.com/SUSE/bci-dockerfile-generator?subdir={bci_pkg.package_name}#{self.branch_name}"

                for elem in (title, descr, scmsync):
                    pkg_conf.append(elem)

                async with aiofiles.tempfile.NamedTemporaryFile(
                    mode="w"
                ) as tmp_pkg_conf:
                    await tmp_pkg_conf.write(ET.tostring(pkg_conf).decode())
                    await tmp_pkg_conf.flush()
                    await self._run_cmd(
                        f"{self._osc} meta pkg --file={tmp_pkg_conf.name} {self.project_name} {bci_pkg.package_name}"
                    )

            tasks.append(write_pkg_conf(bci))

        await asyncio.gather(*tasks)

    def _get_changed_packages_by_commit(self, commit: str) -> list[str]:
        repo = git.Repo(".")
        bci_pkg_names = [bci.package_name for bci in self.bcis]
        packages = []

        # get the diff between the commit and the deployment branch on the remote
        # => list of changed files
        #    each file's first path element is the package name -> save that in
        #    `packages`
        for diff in repo.commit(commit).diff(f"origin/{self.deployment_branch_name}"):
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
        assert reduce(lambda l, r: l and r, (p in bci_pkg_names for p in res))
        return res

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
        await self._run_cmd(
            f"git worktree add -B {self.branch_name} {self.branch_name} "
            f"origin/{self.deployment_branch_name}"
        )
        worktree_dir = os.path.join(os.getcwd(), self.branch_name)

        try:
            await self.write_all_image_build_recipes(worktree_dir)

            run_in_worktree = RunCommand(cwd=worktree_dir, logger=LOGGER)

            worktree = git.Repo(worktree_dir)
            # no changes => nothing to do & bail
            # note: diff only checks for changes to *existing* packages, but not
            # if anything new got added => need to check if the repo is dirty
            # for that (= is there any output with `git status`)
            if not worktree.head.commit.diff() and not worktree.is_dirty():
                LOGGER.info("Writing all build recipes resulted in no changes")
                return None

            await run_in_worktree("git add *")
            await run_in_worktree(
                f"git commit -m '{commit_msg or 'Test build'}'",
            )

            commit = (
                await run_in_worktree("git show -s --pretty=format:%H HEAD")
            ).stdout.strip()
            LOGGER.info("Created commit %s given the current state", commit)
            await run_in_worktree("git push origin HEAD")

        finally:
            await self._run_cmd(f"git worktree remove {self.branch_name}")

        return commit

    async def write_all_image_build_recipes(self, destination_prj_folder: str) -> None:
        tasks = []

        await aiofiles.os.makedirs(destination_prj_folder, exist_ok=True)

        for bci in self.bcis:

            async def write_files(bci_pkg: BaseContainerImage, dest: str):
                await aiofiles.os.makedirs(dest, exist_ok=True)

                # remove everything *but* the changes file (.changes is not
                # autogenerated) so that we properly remove files that were dropped
                to_remove = []
                for fname in await aiofiles.os.listdir(dest):
                    if fname == f"{bci_pkg.package_name}.changes":
                        continue
                    to_remove.append(aiofiles.os.remove(os.path.join(dest, fname)))

                await asyncio.gather(*to_remove)

                await bci_pkg.write_files_to_folder(dest)

            img_dest_dir = os.path.join(destination_prj_folder, bci.package_name)
            tasks.append(write_files(bci, img_dest_dir))

        await asyncio.gather(*tasks)

    async def fetch_build_results(self) -> list[RepositoryBuildResult]:
        """Retrieves the current build results of the staging project."""
        return RepositoryBuildResult.from_resultlist(
            (await self._run_cmd(self._osc_fetch_results_cmd())).stdout
        )

    async def force_rebuild(self) -> str:
        """Deletes all binaries of the project on OBS and force rebuilds everything."""
        await self._run_cmd(f"{self._osc} wipebinaries --all {self.project_name}")
        await self._run_cmd(f"{self._osc} rebuild --all {self.project_name}")
        return self._osc_fetch_results_cmd("--watch")

    async def scratch_build(self) -> None | str:
        # no commit -> no changes -> no reason to build
        if not (commit := await self.write_all_build_recipes_to_branch()):
            return None

        self.package_names = self._get_changed_packages_by_commit(commit)
        LOGGER.debug(
            "packages that were changed by %s: %s",
            commit,
            ", ".join(self.package_names),
        )
        await self.write_test_project_configs()
        await self.write_pkg_configs()
        await self._wait_for_all_pkg_service_runs()

        # "encourage" OBS to rebuild, in case this project existed before
        await asyncio.gather(self.force_rebuild(), self.write_env_file())

        return commit

    async def _wait_for_all_pkg_service_runs(self) -> None:
        """Run :command:`osc service wait` for all packages in the staging
        project.

        """
        service_wait_tasks = []
        if self.package_names is None:
            raise RuntimeError("No packages have been set yet, cannot continue")
        for pkg_name in self.package_names:

            async def wait_for_service(bci_pkg_name: str) -> None:
                await self._run_cmd(
                    f"{self._osc} service wait {self.project_name} {bci_pkg_name}"
                )

            service_wait_tasks.append(wait_for_service(pkg_name))

        await asyncio.gather(*service_wait_tasks)

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
        # packages to be build
        # It will then just give us an empty list of packages for all repos if
        # we call the `/results/` route fast enough after project setup
        # If that happens (=> Σ packages == 0), when we wait for 10s and try
        # again (and repeat this up to 10 times). If OBS hasn't managed to do
        # *anything* by then, just bail…
        def get_number_of_packages_with_results(
            build_result_list: list[RepositoryBuildResult],
        ) -> int:
            all_pkg_results: list[PackageBuildResult] = list(
                itertools.chain.from_iterable(
                    result.packages for result in build_result_list
                )
            )
            return len(all_pkg_results)

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
            if get_number_of_packages_with_results(build_res) == 0 and retries < 10:
                LOGGER.debug("got 0 packages with build results, sleeping and retrying")
                retries += 1
                await asyncio.sleep(10)
            else:
                break

        if get_number_of_packages_with_results(build_res) == 0:
            raise RuntimeError(
                f"{self.project_name} has no packages with build results, something is broken ⚡"
            )

        return build_res
