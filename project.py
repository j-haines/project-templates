#! /usr/bin/env python3

import logging
import pathlib
import shlex
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from typing import List, Optional, Set


_CURRENT_DIR = pathlib.Path(".").resolve()
_PROJECT_NAME_SENTINEL = "{%PROJECT_NAME%}"
_SUPPORTED_PROJECT_LANGUAGES: Set[str] = {
    "cpp",
    "py3",
}

logging.basicConfig()
log = logging.getLogger(__name__)


class UnknownProjectTemplate(Exception):
    pass


def _clone_project_template(src: pathlib.Path, dst: pathlib.Path) -> None:
    cmd = f"git clone {src} {dst}"
    try:
        subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        output = e.output.decode("utf-8")
        raise Exception(f"command '{cmd}' exited with non-zero error code, output: \n\t{output}")

def _init_project(destination: pathlib.Path, project_name: str) -> None:
    all_files = _list_recursive(destination)

    for file in all_files:
        log.debug(f"patching file '{file.name}'")
        _patch_project_name(file, project_name.replace("-", "_"))


def _list_recursive(
    parent: pathlib.Path, accumulator: Optional[List[pathlib.Path]] = None,
) -> List[pathlib.Path]:
    accumulator = accumulator or []
    children = [child for child in parent.iterdir() if not child.name.startswith(".")]

    for child in children:
        if child.is_dir():
            accumulator.extend(_list_recursive(child, accumulator=accumulator))
        else:
            accumulator.append(child)

    return accumulator


def _patch_project_name(filepath: pathlib.Path, name: str) -> None:
    with open(filepath, "r+") as file:
        whole_text = file.read()
        replaced_text = whole_text.replace(_PROJECT_NAME_SENTINEL, name)

        file.seek(0)
        file.truncate()
        file.write(replaced_text)


def _validate_project_template(language: str, template: str) -> pathlib.Path:
    template_folder = _CURRENT_DIR / language / template

    if template_folder.exists() and template_folder.is_dir():
        return template_folder
    else:
        raise UnknownProjectTemplate


def clone(args: Namespace) -> int:
    try:
        src_template_folder = _validate_project_template(args.language, args.template)
    except UnknownProjectTemplate:
        log.exception("no project template '{args.template}'.")
        sys.exit(1)

    dst_project_folder = _CURRENT_DIR / args.destination

    try:
        _clone_project_template(src=src_template_folder, dst=dst_project_folder)
    except Exception as e:
        log.error(f"project cloning failed due to {e}")
        return 1

    try:
        _init_project(dst_project_folder, args.project_name or dst_project_folder.name)
    except Exception:
        log.error("project initialization failed")
        return 2

    return 0


def parse_args() -> Namespace:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(help="sub-command")

    clone_subcommand = subparsers.add_parser("clone")

    clone_subcommand.add_argument(
        "language",
        help="The programming language the new project will be written in.",
        choices=_SUPPORTED_PROJECT_LANGUAGES,
    )
    clone_subcommand.add_argument("template", help="The name of the template to clone.")
    clone_subcommand.add_argument("destination", help="The folder for the new project.")
    clone_subcommand.add_argument(
        "project_name",
        help="The name of the project. Defaults to using the destination folder name.",
        default=None,
        nargs="?",
    )

    clone_subcommand.set_defaults(func=clone)
    parser.set_defaults(func=lambda _: parser.print_help())

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(args.func(args))
