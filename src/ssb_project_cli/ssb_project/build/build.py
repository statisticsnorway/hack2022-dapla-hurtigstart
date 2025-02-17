"""Build command module."""

import os
import json
import re

from pathlib import Path
import sys
from typing import List

import kvakk_git_tools.validate_ssb_gitconfig  # type: ignore

from .environment import verify_local_config
from .poetry import install_ipykernel
from .poetry import poetry_install
from .poetry import check_and_fix_onprem_source
from rich import print

from .prompt import confirm_fix_ssb_git_config

from ssb_project_cli.ssb_project.util import (
    get_kernels_dict,
    get_project_name_and_root_path,
)


def build_project(
    path: Path | None,
    working_directory: Path,
    template_repo_url: str,
    checkout: str | None,
    verify_config: bool = True,
    no_kernel: bool = False,
) -> None:
    """Installs dependencies and kernel for a given project.

    Args:
        path: Path to project
        working_directory: working directory
        template_repo_url: Template repository url
        checkout: The git reference to check against. Supports branches, tags and commit hashes.
        verify_config: Determines if gitconfig is verified.
        no_kernel: Determines if a kernel shall be generated or not.
    """
    if path is None:
        project_directory = working_directory
    else:
        project_directory = working_directory / path

    project_name, project_root = get_project_name_and_root_path(project_directory)

    if project_name is None or project_root is None:
        print(
            ":x:\tCould not find project root. Please run ssb-project within a project directory."
        )
        sys.exit()

    if verify_config:
        validate_and_fix_git_config(
            template_repo_url, checkout, project_name, project_root
        )

    check_and_fix_onprem_source(project_root)

    poetry_install(project_root)
    if not no_kernel:
        install_ipykernel(project_root, project_name)
        ipykernel_attach_bashrc(project_name)


def validate_and_fix_git_config(
    template_repo_url: str, checkout: str | None, project_name: str, project_root: Path
) -> None:
    """Validate and fix the git config.

    Args:
        template_repo_url: Template repository url
        checkout: The git reference to check against. Supports branches, tags and commit hashes.
        project_name: The name of the project
        project_root: The root directory of the project/repo.
    """
    try:
        valid_global_git_config = kvakk_git_tools.validate_git_config()
        print(f"{valid_global_git_config=}")
    except FileExistsError:
        # If gitconfig does not exist the configuration is invalid
        print("Got FileExistError when checking .gitconfig")
        valid_global_git_config = False
    valid_project_git_config = verify_local_config(
        template_repo_url,
        checkout,
        cwd=str(project_root),
    )
    if not valid_global_git_config or not valid_project_git_config:
        print(
            ":x:\tYour project's Git configuration does not follow SSB recommendations,\n:x:\twhich may result in sensitive data being pushed to GitHub."
        )
        confirm_fix_ssb_git_config(
            project_name,
            template_repo_url,
            checkout,
            project_root,
            valid_global_git_config,
            valid_project_git_config,
        )


def ipykernel_attach_bashrc(project_name: str) -> None:
    """Attaches bashrc to the project kernel by modifying ipykernel files.

    Args:
        project_name: path to the kernel directory
    """
    kernels = get_kernels_dict()
    if project_name not in kernels:
        print(
            f":x:\tCould not mount .bashrc, '{project_name}' kernel was not found'."  # noqa: B907
        )
        sys.exit(1)

    project_kernel_path = kernels[project_name]["resource_dir"]
    if not Path(project_kernel_path).exists():
        print(
            f":x:\tCould not mount .bashrc, path: '{project_kernel_path}' does not exist."  # noqa: B907
        )
        sys.exit(1)

    kernel_json_file = f"{project_kernel_path}/kernel.json"
    if not Path(kernel_json_file).exists():
        print(
            f":x:\tCould not mount .bashrc, file: '{kernel_json_file}' does not exist."  # noqa: B907
        )
        sys.exit(1)

    with open(kernel_json_file, encoding="utf-8") as f:
        content_as_json = json.loads(f.read())

    python_executable_path = _get_python_executable_path(content_as_json["argv"])
    if python_executable_path is None:
        print(
            f":x:\tCould not mount .bashrc, cannot find python executable path in {kernel_json_file}"
        )  # noqa: B907
        sys.exit(1)

    if python_executable_path.endswith("/python.sh"):
        print(
            ":warning:\t.bashrc should already been mounted in your kernel, if you are in doubt do a 'clean' followed by a 'build'"
        )  # noqa: B907
        sys.exit(0)

    start_script_path = f"{project_kernel_path}/python.sh"
    content_as_json["argv"] = [
        start_script_path,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]

    with open(kernel_json_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(content_as_json))

    _write_start_script(start_script_path, python_executable_path)

    # set rx to everyone, required for jupyterlab to get permission to call start script
    os.chmod(start_script_path, 0o555)  # noqa: S103


def _get_python_executable_path(argv: List[str]) -> str | None:
    """Searches for any entry which ends with python.

    Args:
        argv: A list of strings

    Returns: Path to python executable if it exists, otherwise None
    """
    pattern = r"^.*(?:/python3|/python|/python\.sh)$"
    matches = [entry for entry in argv if re.match(pattern, entry)]
    return matches[0] if len(matches) >= 1 else None


def _write_start_script(start_script_path: str, python_executable_path: str) -> None:
    """Write the start script content to the specified path.

    Args:
        start_script_path: Path to create the start script
        python_executable_path: Path to the python executable
    """
    with open(start_script_path, "w", encoding="utf-8") as f:
        f.writelines(
            [
                "#!/usr/bin/env bash\n",
                "source $HOME/.bashrc\n",
                f"exec {python_executable_path} $@",
            ]
        )
