"""This module reads in environment variables."""

import os
from pathlib import Path
from kvakk_git_tools import ssb_gitconfig  # type: ignore
from rich import print

from ssb_project_cli.ssb_project.build.temp_template_repo import TempTemplateRepo

JUPYTER_IMAGE_SPEC = os.environ.get("JUPYTER_IMAGE_SPEC", "")
PIP_INDEX_URL = os.environ.get("PIP_INDEX_URL", "")
NEXUS_SOURCE_NAME = "nexus"


def running_onprem(image_spec: str) -> bool:
    """Are we running in Jupyter on-prem?

    Args:
        image_spec: Value of the JUPYTER_IMAGE_SPEC environment variable

    Returns:
        True if running on-prem, else False.
    """
    return "onprem" in image_spec


def _local_file_contains_remote_lines(
    local_file_path: str, remote_file_path: str
) -> bool:
    """Compares the contents of two files, one local and one remote.

    Returns True if the contents
    of the local file include all lines in the remote file, False otherwise.

    Args:
        local_file_path (str): The path to the local file to compare.
        remote_file_path (str): The path to the remote file to compare.

    Returns:
        bool: True if the contents of the local file include all lines in the remote file,
              False otherwise.
    """
    # Read the contents of the local file into a set of lines
    with open(local_file_path) as local_file:
        local_content = set(local_file.read().strip().split("\n"))

    # Read the contents of the remote file into a set of lines
    with open(remote_file_path) as remote_file:
        remote_content = set(remote_file.read().strip().split("\n"))
    # Check if the local file has all lines in the remote file
    return remote_content.issubset(local_content)


def print_missing_remote_lines(local_file_path: str, remote_file_path: str) -> None:
    """Prints lines in remote_file that are not in local_file."""
    with open(local_file_path) as local_file:
        local_lines = set(local_file.readlines())

    with open(remote_file_path) as remote_file:
        for line in remote_file:
            if line not in local_lines:
                print(line, end="")  # Beholder original linjeformat


def verify_local_config(
    template_repo_url: str, checkout: str | None, cwd: str = ""
) -> bool:
    """Verifies that the local configuration files contains all lines from the files in the remote repository.

    Returns True if local config is following SSB recommendations otherwise False.

    Args:
        template_repo_url: Template repository url
        checkout: The git reference to check against. Supports branches, tags and commit hashes.
        cwd: Current working directory
    """
    file_paths = [".gitattributes", ".gitignore"]

    if cwd != "":
        # If a path is used we should add a slash
        cwd = cwd + "/"

    result = True
    # create a temporary directory
    with TempTemplateRepo(template_repo_url, checkout) as temp_repo:
        # compare the contents of the local files with the files in the repository
        for file_path in file_paths:
            # get the paths of the local and remote files
            remote_file_path = (
                f"{temp_repo.temp_dir.name}/{temp_repo.subdir}/{file_path}"
            )
            local_file_path = cwd + file_path
            if not Path(local_file_path).exists():
                return False
            # compare the contents of the local and remote files
            if not _local_file_contains_remote_lines(local_file_path, remote_file_path):
                print(
                    f"\n:x:\t{file_path} does not contain the required lines. Missing lines:"
                )
                print_missing_remote_lines(local_file_path, remote_file_path)
                result = False
    return result


def reset_global_gitconfig() -> None:
    """Reset the global gitconfig using 'kvakk-git-tools' module.

    This function attempts to configure the global gitconfig using the 'kvakk-git-tools' module.
    If the configuration fails, an error message is printed indicating the platform's support status.
    """
    print("\nConfiguring git with 'kvakk-git-tools':")

    try:
        ssb_gitconfig.main(test=False)
    except SystemExit:
        platform = ssb_gitconfig.Platform()
        is_supported_bools = ("is", "is not")
        print(
            f"\n:x:\tYour global gitconfig was not fixed, your platform {is_supported_bools[platform.is_unsupported()]} supported."
        )
