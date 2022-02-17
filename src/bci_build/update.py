#!/usr/bin/env python3
import asyncio
import logging
from typing import Optional

from asyncio import create_subprocess_shell
import aiofiles.tempfile

from bci_build.package import ALL_CONTAINER_IMAGE_NAMES, BaseContainerImage


LOGGER = logging.getLogger(__name__)


async def update_package(
    bci: BaseContainerImage,
    commit_msg: str,
    target_pkg: Optional[str] = None,
    target_prj: Optional[str] = None,
    cleanup_on_error: bool = False,
    submit_package: bool = True,
    cleanup_on_no_change: bool = True,
) -> None:
    """Update the package of this BCI image on IBS:

    1. if ``target_pkg`` is ``None``, branch the image package, optionally
       into the supplied ``target_prj``
    2. checkout the branched package or ``target_pkg``
    3. render the build recipe files from the ``bci`` Container Image
    4. update the changelog, commit the changes and create a submitrequest
       (the SR is only created when ``submit_package`` is ``True``) if any
       changes were made.

    If ``cleanup_on_error`` is ``True``, then perform a :command:`osc
    rdelete` of the branched package or ``target_pkg`` if an error occurred
    during the update.

    """
    assert not (
        (target_pkg is not None) and (target_prj is not None)
    ), f"Both {target_pkg=} and {target_prj=} cannot be defined at the same time"

    async with aiofiles.tempfile.TemporaryDirectory() as tmp:
        LOGGER.info("Updating %s for SP%d", bci.ibs_package, bci.sp_version)
        LOGGER.debug("Running update in %s", tmp)

        async def run_cmd(c: str) -> str:
            LOGGER.debug("Running command %s", c)
            p = await create_subprocess_shell(
                c,
                stderr=asyncio.subprocess.STDOUT,
                stdout=asyncio.subprocess.PIPE,
                cwd=tmp,
            )
            retcode = await p.wait()
            stdout, _ = await p.communicate()
            if retcode != 0:
                raise RuntimeError(
                    f"Commend {c} failed (exit code {retcode}) with: {stdout.decode()}"
                )
            return stdout.decode()

        try:
            if not target_pkg:
                cmd = f"osc -A ibs branch SUSE:SLE-15-SP{bci.sp_version}:Update:BCI {bci.ibs_package}"
                if target_prj:
                    cmd += f" {target_prj}"
                stdout = (await run_cmd(cmd)).split("\n")

                co_cmd = stdout[2]
                target_pkg = co_cmd.split(" ")[-1]

            await run_cmd(f"osc -A ibs co {target_pkg} -o {tmp}")

            written_files = await bci.write_files_to_folder(tmp)
            for fname in written_files:
                await run_cmd(f"osc add {fname}")

            st_out = await run_cmd("osc st")
            # nothing changed => leave
            if st_out == "":
                LOGGER.info("Nothing changed => no update available")
                if cleanup_on_no_change:
                    await run_cmd(
                        f"osc -A ibs rdelete {target_pkg} -m 'cleanup as nothing changed'"
                    )
                return

            for cmd in ["vc", "ci"] + (["sr --cleanup"] if submit_package else []):
                await run_cmd(f'osc {cmd} -m "{commit_msg}"')

        except Exception as exc:
            LOGGER.error("failed to update %s, got %s", bci.name, exc)
            if cleanup_on_error:
                await run_cmd(f"osc -A ibs rdelete {target_pkg} -m 'cleanup on error'")
            raise exc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("Update the SLE BCI image description on IBS")

    parser.add_argument(
        "images",
        type=str,
        nargs="+",
        choices=list(ALL_CONTAINER_IMAGE_NAMES.keys()),
        help="The BCI container image that should be updated",
    )
    parser.add_argument(
        "--commit-msg",
        type=str,
        nargs=1,
        default=[None],
        help="Required commit message that will be added to the changelog, as the commit message and for the submit request.",
    )

    parser.add_argument(
        "--cleanup-on-error",
        action="store_true",
        help="Delete the branched or target package if an error occurred during the update process",
    )
    parser.add_argument(
        "--no-cleanup-on-no-change",
        action="store_true",
        help="Don't remove the branched package when nothing changed",
    )
    parser.add_argument(
        "--no-sr",
        action="store_true",
        help="Don't send a submitrequest after the package has been updated",
    )
    parser.add_argument(
        "--target-pkg",
        type=str,
        nargs="?",
        default=None,
        help="Don't branch the package on IBS, instead use the specified package to perform the update. When using this option, only one container image can be updated",
    )
    parser.add_argument(
        "--target-prj",
        type=str,
        nargs="?",
        default=None,
        help="Don't branch into the default project, use the supplied one instead. This option is incompatible with the --target-pkg flag.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity of the logger to stderr",
    )

    args = parser.parse_args()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt="%(levelname)s: %(message)s"))
    LOGGER.addHandler(handler)

    commit_msg = args.commit_msg[0]
    if commit_msg is None:
        raise ValueError("A commit message must be provided")

    if args.verbose > 0:
        LOGGER.setLevel((3 - min(args.verbose, 2)) * 10)
    else:
        LOGGER.setLevel("ERROR")

    loop = asyncio.get_event_loop()
    for img in args.images:
        loop.run_until_complete(
            update_package(
                ALL_CONTAINER_IMAGE_NAMES[img],
                commit_msg=commit_msg,
                target_pkg=args.target_pkg,
                target_prj=args.target_prj,
                cleanup_on_error=args.cleanup_on_error,
                submit_package=not args.no_sr,
                cleanup_on_no_change=not args.no_cleanup_on_no_change,
            )
        )
