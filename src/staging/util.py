import pathlib

import aiofiles.os


def get_obs_project_url(
    project_name: str, base_url: str = "https://build.opensuse.org/"
) -> str:
    """Returns the url of the project with the given name."""
    base = base_url if base_url[-1] != "/" else base_url[:-1]
    return f"{base}/project/show/{project_name}"


async def ensure_absent(path: str | pathlib.Path) -> None:
    """Removes the file or directory with the given ``path`` if it exists or
    does nothing.

    Directories must be empty to be removed.

    Raises:
        :py:class:`ValueError`: if ``path`` is neither a file nor a directory

    """
    if await aiofiles.os.path.exists(path):
        if await aiofiles.os.path.isfile(path):
            await aiofiles.os.remove(path)
        elif await aiofiles.os.path.isdir(path):
            await aiofiles.os.rmdir(path)
        else:
            raise ValueError(f"{path} is neither a file nor a directory")
