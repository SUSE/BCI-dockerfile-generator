import os
import pathlib

import pytest
import yaml
from bci_build.package import ALL_OS_VERSIONS
from bci_build.package import OsVersion
from osc_helper.runner import OscRunner
from staging.bot import StagingBot


@pytest.fixture(autouse=True)
def run_in_tmp_path(tmp_path: pathlib.Path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


@pytest.mark.parametrize("os_version", ALL_OS_VERSIONS)
@pytest.mark.parametrize("branch", ["", "something"])
@pytest.mark.parametrize("packages", [None, ["pcp-image"]])
@pytest.mark.parametrize(
    "repositories", [None, ["images"], ["images", "containerfile", "ports"]]
)
@pytest.mark.asyncio
async def test_load_from_env(
    os_version: OsVersion,
    branch: str,
    packages: list[str] | None,
    repositories: list[str] | None,
):
    kwargs = {
        "os_version": os_version,
        "osc_runner": OscRunner("foobar"),
        "branch_name": branch,
    }
    if repositories:
        kwargs["repositories"] = repositories
    bot = StagingBot(**kwargs)
    bot.package_names = packages
    await bot.setup()

    bot_from_env = await StagingBot.from_env_file()
    # we need to use the same osc_runner as their individual setup() causes them
    # to be different
    bot.osc_runner = bot_from_env.osc_runner

    assert await StagingBot.from_env_file() == bot


_osc_runner = OscRunner("defolos")


@pytest.mark.parametrize(
    "comment,bot",
    [
        (
            """Created a staging project on OBS for 4: [home:defolos:BCI:Staging:SLE-15-SP4:sle15-sp4-AVeMj](https://build.opensuse.org/project/show/home:defolos:BCI:Staging:SLE-15-SP4:sle15-sp4-AVeMj)
Changes pushed to branch [`sle15-sp4-AVeMj`](https://github.com/SUSE/BCI-dockerfile-generator/tree/sle15-sp4-AVeMj)""",
            StagingBot(
                os_version=OsVersion.SP4,
                branch_name="sle15-sp4-AVeMj",
                osc_runner=_osc_runner,
            ),
        ),
        (
            """Created a staging project on OBS for Tumbleweed: [home:defolos:BCI:Staging:Tumbleweed:tumbleweed-EqgiS](https://build.opensuse.org/project/show/home:defolos:BCI:Staging:Tumbleweed:tumbleweed-EqgiS)
Changes pushed to branch [`tumbleweed-EqgiS`](https://github.com/SUSE/BCI-dockerfile-generator/tree/tumbleweed-EqgiS)""",
            StagingBot(
                os_version=OsVersion.TUMBLEWEED,
                branch_name="tumbleweed-EqgiS",
                osc_runner=_osc_runner,
            ),
        ),
        (
            """Created a staging project on OBS for 3: [home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-OZGYa](https://build.opensuse.org/project/show/home:defolos:BCI:Staging:SLE-15-SP3:sle15-sp3-OZGYa)
Changes pushed to branch [`sle15-sp3-OZGYa`](https://github.com/SUSE/BCI-dockerfile-generator/tree/sle15-sp3-OZGYa)""",
            StagingBot(
                os_version=OsVersion.SP3,
                branch_name="sle15-sp3-OZGYa",
                osc_runner=_osc_runner,
            ),
        ),
    ],
)
def test_from_github_comment(comment: str, bot: StagingBot):
    assert bot == StagingBot.from_github_comment(
        comment_text=comment, osc_username=_osc_runner.osc_username
    )


def test_from_empty_github_comment():
    with pytest.raises(ValueError) as val_err_ctx:
        StagingBot.from_github_comment("", "irrelevant")

    assert "Received empty github comment, cannot create the bot" in str(
        val_err_ctx.value
    )


_bot = StagingBot(os_version=OsVersion.SP5, osc_runner=_osc_runner)


@pytest.mark.parametrize(
    "action", [_bot.changelog_check_github_action, _bot.find_missing_packages_action]
)
def test_github_actions_valid_yaml(action: str) -> None:
    assert yaml.safe_load(action)
