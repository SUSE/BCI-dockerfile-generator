#!/usr/bin/env python3
import asyncio
import logging
from typing import List, Literal, Optional

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
    build_service_target: Literal["obs", "ibs"] = "obs",
) -> None:
    """Update the package of this BCI image on OBS or IBS (which one is chosen
    depends on the parameter ``build_service_target``, with the default being
    OBS):

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

    assert build_service_target in (
        "obs",
        "ibs",
    ), f"got an invalid {build_service_target=}, expected 'obs' or 'ibs'"

    if build_service_target == "obs":
        osc = "osc"
        src_prj = f"devel:BCI:SLE-15-SP{bci.os_version}"
    else:
        osc = "osc -A ibs"
        src_prj = f"SUSE:SLE-15-SP{bci.os_version}:Update:BCI"

    async with aiofiles.tempfile.TemporaryDirectory() as tmp:
        LOGGER.info("Updating %s for SP%d", bci.package_name, bci.os_version)
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
                    f"Command {c} failed (exit code {retcode}) with: {stdout.decode()}"
                )
            return stdout.decode()

        try:
            if not target_pkg:
                cmd = f"{osc} branch {src_prj} {bci.package_name}"
                if target_prj:
                    cmd += f" {target_prj}"
                stdout = (await run_cmd(cmd)).split("\n")

                co_cmd = stdout[2]
                target_pkg = co_cmd.split(" ")[-1]

            await run_cmd(f"{osc} co {target_pkg} -o {tmp}")

            written_files = await bci.write_files_to_folder(tmp)
            for fname in written_files:
                await run_cmd(f"osc add {fname}")

            st_out = await run_cmd("osc st")
            # nothing changed => leave
            if st_out == "":
                LOGGER.info("Nothing changed => no update available")
                if cleanup_on_no_change:
                    await run_cmd(
                        f"{osc} rdelete {target_pkg} -m 'cleanup as nothing changed'"
                    )
                return

            for cmd in ["vc", "ci"] + (["sr --cleanup"] if submit_package else []):
                await run_cmd(f'osc {cmd} -m "{commit_msg}"')

        except Exception as exc:
            LOGGER.error("failed to update %s, got %s", bci.name, exc)
            if cleanup_on_error:
                await run_cmd(f"{osc} rdelete {target_pkg} -m 'cleanup on error'")
            raise exc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        "Update the SLE BCI image description on OBS or IBS"
    )

    parser.add_argument(
        "--images",
        type=str,
        nargs="*",
        choices=list(ALL_CONTAINER_IMAGE_NAMES.keys()),
        help="The BCI container image that should be updated. This option is mutually exclusive with --service-pack.",
    )
    parser.add_argument(
        "--service-pack",
        type=int,
        choices=[3, 4],
        nargs=1,
        help="Do not update a single image, instead update all images of a single service pack. This option is mutually exclusive with supplying image names.",
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
        help="Don't branch the package on OBS/IBS, instead use the specified package to perform the update. When using this option, only one container image can be updated",
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
    parser.add_argument(
        "--build-service-target",
        type=str,
        nargs=1,
        default=["obs"],
        choices=["obs", "ibs"],
        help="Specify whether the updater should target obs (build.opensuse.org) or ibs (build.suse.de)",
    )

    args = parser.parse_args()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt="%(levelname)s: %(message)s"))
    LOGGER.addHandler(handler)

    if args.images and args.service_pack:
        raise ValueError(
            "Cannot set the service pack and specific images at the same time"
        )

    commit_msg = args.commit_msg[0]
    if commit_msg is None:
        raise ValueError("A commit message must be provided")

    if args.verbose > 0:
        LOGGER.setLevel((3 - min(args.verbose, 2)) * 10)
    else:
        LOGGER.setLevel("ERROR")

    loop = asyncio.get_event_loop()
    images: List[str] = (
        args.images
        if args.images
        else [
            k
            for k, v in ALL_CONTAINER_IMAGE_NAMES.items()
            if v.os_version == args.service_pack[0]
        ]
    )

    for img in images:
        loop.run_until_complete(
            update_package(
                ALL_CONTAINER_IMAGE_NAMES[img],
                commit_msg=commit_msg,
                target_pkg=args.target_pkg,
                target_prj=args.target_prj,
                cleanup_on_error=args.cleanup_on_error,
                submit_package=not args.no_sr,
                cleanup_on_no_change=not args.no_cleanup_on_no_change,
                build_service_target=args.build_service_target[0],
            )
        )
