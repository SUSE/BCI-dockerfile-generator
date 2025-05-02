import git
import pytest
from pytest import Config

from staging.git_repo import get_commit_range_between_refs


@pytest.mark.parametrize(
    "child_ref, ancestor_ref, expected_commit_range",
    [
        (
            "1bcd993b0a8782e1756725127c0cbb6d8c88845e",
            "1bcd993b0a8782e1756725127c0cbb6d8c88845e",
            {},
        ),
        # 04d1acf7246e8ba11a2c454dc200ce58b53cb807 is the child of 1bcd993b0a8782e1756725127c0cbb6d8c88845e
        (
            "1bcd993b0a8782e1756725127c0cbb6d8c88845e",
            "04d1acf7246e8ba11a2c454dc200ce58b53cb807",
            {"1bcd993b0a8782e1756725127c0cbb6d8c88845e"},
        ),
        # above case, wrong way around: child is the ancestor
        (
            "04d1acf7246e8ba11a2c454dc200ce58b53cb807",
            "1bcd993b0a8782e1756725127c0cbb6d8c88845e",
            None,
        ),
        # A more involved test case:
        #
        # * |   19c42351 Merge pull request #2442 from HVSharma12/pulseaudio-entrypoint
        # |\ \
        # | * | 43074689 Add entrypoint script for PulseAudio container
        # * | |   e57be2ad Merge pull request #2444 from SUSE/poetry_lock_update
        # |\ \ \
        # | * | | 9ed4c2d9 Update poetry.lock
        # * | | |   9ede9a87 Merge pull request #2439 from SUSE/drop_gcc12
        # |\ \ \ \
        # | |/ / /
        # |/| | |
        # | * | | fe656acb Remove gcc 12 container
        # | |/ /
        # * | |   86990f63 Merge pull request #2441 from SUSE/cosign
        # |\ \ \
        # | |/ /
        # |/| |
        # | * | 1aa8fc9f update cosign versions
        # |/ /
        # * |   37ebaf51 Merge pull request #2435 from HVSharma12/firefox-audio-fix
        #
        (
            "e57be2ad",
            "86990f63",
            {
                "e57be2ad",
                "9ede9a87",
                "9ed4c2d9",
                "fe656acb",
            },
        ),
    ],
)
def test_get_git_commit_range(
    pytestconfig: Config,
    child_ref: str,
    ancestor_ref: str,
    expected_commit_range: set[str] | None,
) -> None:
    repo_path = str(pytestconfig.rootpath.absolute())
    repo = git.Repo(repo_path)

    if expected_commit_range is None:
        expected_res = None
    else:
        expected_res = {repo.commit(sha) for sha in expected_commit_range}
        # verify that ancestor_ref is not in the returned set!
        assert repo.commit(ancestor_ref) not in expected_res

    assert (
        get_commit_range_between_refs(child_ref, ancestor_ref, repo_path=repo_path)
        == expected_res
    )
