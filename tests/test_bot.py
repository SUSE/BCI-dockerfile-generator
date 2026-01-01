import os
import pathlib

import pytest
import yaml

from bci_build.os_version import ALL_NONBASE_OS_VERSIONS
from bci_build.os_version import OsVersion
from staging.bot import StagingBot


@pytest.fixture(autouse=True)
def run_in_tmp_path(tmp_path: pathlib.Path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


@pytest.mark.parametrize("os_version", ALL_NONBASE_OS_VERSIONS)
@pytest.mark.parametrize("branch", ["", "something"])
@pytest.mark.parametrize("packages", [None, ["bind-image"]])
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
    kwargs = {"os_version": os_version, "osc_username": "foobar", "branch_name": branch}
    if repositories:
        kwargs["repositories"] = repositories
    bot = StagingBot(**kwargs)
    bot.package_names = packages
    await bot.setup()

    assert await StagingBot.from_env_file() == bot


_osc_user = "testuser"


@pytest.mark.parametrize(
    "comment,bot",
    [
        (
            """Created a staging project on OBS for 16.0: [home:testuser:BCI:Staging:16.0:16.0-AVeMj](https://build.opensuse.org/project/show/home:testuser:BCI:Staging:16.0:16.0-AVeMj)
Changes pushed to branch [`16.0-AVeMj`](https://github.com/SUSE/BCI-dockerfile-generator/tree/16.0-AVeMj)""",
            StagingBot(
                os_version=OsVersion.SL16_0,
                branch_name="16.0-AVeMj",
                osc_username=_osc_user,
            ),
        ),
        (
            """Created a staging project on OBS for Tumbleweed: [home:testuser:BCI:Staging:Tumbleweed:tumbleweed-EqgiS](https://build.opensuse.org/project/show/home:testuser:BCI:Staging:Tumbleweed:tumbleweed-EqgiS)
Changes pushed to branch [`tumbleweed-EqgiS`](https://github.com/SUSE/BCI-dockerfile-generator/tree/tumbleweed-EqgiS)""",
            StagingBot(
                os_version=OsVersion.TUMBLEWEED,
                branch_name="tumbleweed-EqgiS",
                osc_username=_osc_user,
            ),
        ),
        (
            """Created a staging project on OBS for 7: [home:testuser:BCI:Staging:SLE-15-SP7:sle15-sp7-OZGYa](https://build.opensuse.org/project/show/home:testuser:BCI:Staging:SLE-15-SP7:sle15-sp7-OZGYa)
Changes pushed to branch [`sle15-sp7-OZGYa`](https://github.com/SUSE/BCI-dockerfile-generator/tree/sle15-sp7-OZGYa)""",
            StagingBot(
                os_version=OsVersion.SP7,
                branch_name="sle15-sp7-OZGYa",
                osc_username=_osc_user,
            ),
        ),
    ],
)
def test_from_github_comment(comment: str, bot: StagingBot):
    assert bot == StagingBot.from_github_comment(
        comment_text=comment, osc_username=_osc_user
    )


def test_from_empty_github_comment():
    with pytest.raises(ValueError) as val_err_ctx:
        StagingBot.from_github_comment("", "irrelevant")

    assert "Received empty github comment, cannot create the bot" in str(
        val_err_ctx.value
    )


_bot = StagingBot(os_version=OsVersion.SP7, osc_username=_osc_user)


@pytest.mark.parametrize(
    "action", [_bot.changelog_check_github_action, _bot.find_missing_packages_action]
)
def test_github_actions_valid_yaml(action: str) -> None:
    assert yaml.safe_load(action)
