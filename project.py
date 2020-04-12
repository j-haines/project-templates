#! /usr/bin/env python3

import logging
import os
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

logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


class UnknownProjectTemplate(Exception):
    pass


def basename(path: pathlib.Path) -> str:
    return os.path.basename(path)


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
    parent: pathlib.Path, accumulator: Optional[List[pathlib.Path]] = None, maxdepth: int = -1
) -> List[pathlib.Path]:
    """List all files and folders under `parent`, recursively up to `maxdepth`.

    If maxdepth is less than 0, the function will list recursively the full
     file tree with no limit."""
    accumulator = accumulator or []

    # stop recursion
    if maxdepth == 0:
        return [parent]

    children = [child for child in parent.iterdir() if not child.name.startswith(".")]

    for child in children:
        if child.is_dir():
            if maxdepth > 0:
                maxdepth = maxdepth - 1

            accumulator.extend(_list_recursive(child, accumulator=accumulator, maxdepth=maxdepth))
        else:
            accumulator.append(child)

    return accumulator


def _list_subtemplate_folders(parent: pathlib.Path) -> Set[pathlib.Path]:
    accumulator: Set[pathlib.Path] = set()
    for child in _list_recursive(parent, maxdepth=1):
        # assume parent is a master project if it is a folder with no files
        # e.g. "projects" may be "parent/child" or simply "parent"
        if parent.is_dir() and len([child for child in parent.iterdir() if child.is_file()]) == 0:
            accumulator.add(child)

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
        log.exception(f"no project template '{args.template}'.")
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


def list(args: Namespace) -> int:
    language = args.language
    languages_folder = _CURRENT_DIR / language

    if not (languages_folder.exists() and languages_folder.is_dir()):
        log.error(f"unsupported language '{language}'")
        return 1

    template_folders: Set[pathlib.Path] = set()
    for template_folder_child in languages_folder.iterdir():
        if template_folder_child.is_dir():
            template_folders.add(template_folder_child)

    project_folders: Set[pathlib.Path] = set()
    for template_folder in template_folders:
        template_basename = basename(template_folder)

        template_folder_children = set(_list_recursive(template_folder, maxdepth=1))
        template_folder_files = {child for child in template_folder_children if child.is_file()}
        subtemplate_folders = template_folder_children - template_folder_files

        # if a folder has children that aren't folders or README files, it's
        #  probably a template folder rather than a project folder
        noreadme_files = {file for file in template_folder_files if not str(file).lower()[:6] == "readme"}
        if len(noreadme_files):
            continue

        project_folders.add(template_folder)
        for subtemplate_folder in _list_subtemplate_folders(template_folder):
            subtemplate_basename = basename(subtemplate_folder)

            log.info(f"{template_basename}/{subtemplate_basename}")

    for template_folder in template_folders - project_folders:
        template_basename = basename(template_folder)

        log.info(f"{template_basename}")

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

    list_subcommand = subparsers.add_parser("list")

    list_subcommand.add_argument("language", help="The programming language to list project templates for.")

    clone_subcommand.set_defaults(func=clone)
    list_subcommand.set_defaults(func=list)
    parser.set_defaults(func=lambda _: parser.print_help())

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(args.func(args))
