"""Module containing helper functions interact with git repositories."""

import git


def get_commit_range_between_refs(
    child_ref: str, ancestor_ref: str, repo_path: str = "."
) -> set[git.Commit] | None:
    """Returns all commits leading from ``child_ref`` to ``ancestor_ref``,
    **excluding** ``ancestor_ref`` in the repository specified via `repo_path`.

    If ``ancestor_ref`` is not an ancestor of ``child_ref``, then ``None`` is
    returned. If ``ancestor_ref`` and ``child_ref`` are the same commit (can be
    denoted via different names), then an empty set is returned.

    """
    repo = git.Repo(repo_path)

    def is_ancestor(child_sha: str, ancestor_sha: str) -> bool:
        """Checks whether the commit identified via ``ancestor_sha`` is an
        ancestor of the commit identified via ``child_sha``.

        """
        try:
            repo.git.merge_base(ancestor_sha, child_sha, is_ancestor=True)
            return True
        except git.GitCommandError as exc:
            # git failing with status 1 indicates that ancestor is not an
            # ancestor of child
            # The only other exit code is 128, which indicates that the commit
            # hexsha is unknown, which must not happen
            assert exc.status == 1
            return False

    ancestor_commit = repo.commit(ancestor_ref)
    child_commit = repo.commit(child_ref)

    if not is_ancestor(child_commit.hexsha, ancestor_commit.hexsha):
        return None

    commit_hexshas = repo.git.rev_list(
        child_commit.hexsha, f"^{ancestor_commit.hexsha}"
    ).splitlines()

    return {repo.commit(sha) for sha in commit_hexshas}
