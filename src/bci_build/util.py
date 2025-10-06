import enum

import aiofiles


@enum.unique
class ParseVersion(enum.StrEnum):
    MAJOR = enum.auto()
    MINOR = enum.auto()
    PATCH = enum.auto()
    PATCH_UPDATE = enum.auto()
    OFFSET = enum.auto()


async def write_to_file(fname: str, contents: str | bytes) -> None:
    if isinstance(contents, str):
        async with aiofiles.open(fname, "w") as f:
            await f.write(contents)
    elif isinstance(contents, bytes):
        async with aiofiles.open(fname, "bw") as f:
            await f.write(contents)
    else:
        raise TypeError(
            f"Invalid type of contents: {type(contents)}, expected string or bytes"
        )
