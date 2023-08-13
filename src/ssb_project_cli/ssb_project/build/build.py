"""Build command module."""
import os
import json
import re

from pathlib import Path
from typing import List

import kvakk_git_tools.validate_ssb_gitconfig  # type: ignore

from .environment import JUPYTER_IMAGE_SPEC, verify_local_config
from .environment import PIP_INDEX_URL
from .environment import running_onprem
from .poetry import install_ipykernel
from .poetry import poetry_install
from .poetry import poetry_source_add
from .poetry import poetry_source_includes_source_name
from .poetry import poetry_source_remove
from rich import print

from .prompt import confirm_fix_ssb_git_config

from ssb_project_cli.ssb_project.util import get_kernels_dict


def build_project(
    path: Path,
    working_directory: Path,
    template_repo_url: str,
    template_reference: str,
    verify_config: bool = True,
) -> None:
    """Installs dependencies and kernel for a given project.

    Args:
        path: Path to project
        working_directory: working directory
        template_repo_url: Template repository url
        template_reference: Template reference
        verify_config: Determines if gitconfig is verified.
    """
    if path == "":
        project_name = working_directory.name
        project_directory = working_directory
    else:
        project_name = path.absolute().name
        project_directory = working_directory / path

    if not (project_directory / "pyproject.toml").is_file():
        print(
            f":x:\tProject directory: {project_directory} is not a valid SSB-project, pyproject.toml is missing."
        )
        exit(1)
    if verify_config:
        try:
            valid_global_git_config = kvakk_git_tools.validate_git_config()
        except FileExistsError:
            # If gitconfig does not exist the configuration is invalid
            valid_global_git_config = False
        valid_project_git_config = verify_local_config(
            template_repo_url,
            template_reference,
            cwd=str(working_directory / project_directory),
        )
        if not valid_global_git_config or not valid_project_git_config:
            print(
                ":x:\tYour project's Git configuration does not follow SSB recommendations,\n:x:\twhich may result in sensitive data being pushed to GitHub."
            )
            confirm_fix_ssb_git_config(
                project_name,
                template_repo_url,
                template_reference,
                project_directory,
                valid_global_git_config,
                valid_project_git_config,
            )

    if running_onprem(JUPYTER_IMAGE_SPEC):
        print(
            ":twisted_rightwards_arrows:\tDetected onprem environment, using proxy for package installation"
        )
        if poetry_source_includes_source_name(project_directory):
            poetry_source_remove(project_directory, lock_update=False)
        poetry_source_add(PIP_INDEX_URL, project_directory)
    elif poetry_source_includes_source_name(project_directory):
        print(
            ":twisted_rightwards_arrows:\tDetected non-onprem environment, removing proxy for package installation"
        )
        poetry_source_remove(project_directory)

    poetry_install(project_directory)
    install_ipykernel(project_directory, project_name)
    ipykernel_attach_bashrc(project_name)


def ipykernel_attach_bashrc(project_name: str) -> None:
    """Attaches bashrc to the project kernel by modifying ipykernel files.

    Args:
        project_name: path to the kernel directory
    """
    kernels = get_kernels_dict()
    if project_name not in kernels:
        print(
            f":x:\tCould not mount .bashrc, '{project_name}' is not found in 'jupyter kernelspec list'."  # noqa: B907
        )
        exit(1)

    project_kernel_path = kernels[project_name]
    if not Path(project_kernel_path).exists():
        print(
            f":x:\tCould not mount .bashrc, path: '{project_kernel_path}' does not exist."  # noqa: B907
        )
        exit(1)

    kernel_json_file = f"{project_kernel_path}/kernel.json"
    if not Path(kernel_json_file).exists():
        print(
            f":x:\tCould not mount .bashrc, file: '{kernel_json_file}' does not exist."  # noqa: B907
        )
        exit(1)

    with open(kernel_json_file, encoding="utf-8") as f:
        content_as_json = json.loads(f.read())

    python_executable_path = _get_python_executable_path(content_as_json["argv"])
    if python_executable_path is None:
        print(
            f":x:\tCould not mount .bashrc, cannot find python executable path in {kernel_json_file}"
        )  # noqa: B907
        exit(1)

    if python_executable_path.endswith("/python.sh"):
        print(
            ":warning:\t.bashrc should already been mounted in your kernel, if you are in doubt do a 'clean' followed by a 'build'"
        )  # noqa: B907
        exit(0)

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
