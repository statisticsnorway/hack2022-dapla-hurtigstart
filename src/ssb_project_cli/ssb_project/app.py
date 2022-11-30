"""Command-line-interface for project-operations in dapla-jupterlab."""

import typer
from rich.console import Console

from .build.build import build_project
from .clean.clean import clean_project
from .create.create import create_project
from .create.repo_privacy import RepoPrivacy
from .settings import CURRENT_WORKING_DIRECTORY
from .settings import GITHUB_ORG_NAME
from .settings import HOME_PATH
from .settings import STAT_TEMPLATE_DEFAULT_REFERENCE
from .settings import STAT_TEMPLATE_REPO_URL


# Don't print with color, it's difficult to read when run in Jupyter
console = Console(color_system=None)
print = console.print

app = typer.Typer(
    help="Usage instructions: https://statisticsnorway.github.io/dapla-manual/ssb-project.html",
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,  # Locals can contain sensitive information
)


@app.command()
def create(  # noqa: C901
    project_name: str = typer.Argument(..., help="Project name"),  # noqa: B008
    description: str = typer.Argument(  # noqa: B008
        "", help="A short description of your project"
    ),
    repo_privacy: RepoPrivacy = typer.Argument(  # noqa: B008
        RepoPrivacy.internal, help="Visibility of the Github repo"
    ),
    add_github: bool = typer.Option(  # noqa: B008
        False,
        "--github",
        help="Create the repo on Github as well",
    ),
    github_token: str = typer.Option(  # noqa: B008
        "",
        help="Your Github Personal Access Token, follow these instructions to create one: https://statisticsnorway.github.io/dapla-manual/ssb-project.html#personal-access-token-pat",
    ),
) -> None:
    """:sparkles:\tCreate a project locally, and optionally on GitHub with the flag --github. The project will follow SSB's best practice for development."""
    create_project(
        project_name,
        description,
        repo_privacy,
        add_github,
        github_token,
        CURRENT_WORKING_DIRECTORY,
        HOME_PATH,
        GITHUB_ORG_NAME,
        STAT_TEMPLATE_REPO_URL,
        STAT_TEMPLATE_DEFAULT_REFERENCE,
    )


@app.command()
def build(
    path: str = typer.Argument(  # noqa: B008
        "",
        help="Project path",
    ),
) -> None:
    """:wrench:\tCreate a virtual environment and corresponding Jupyter kernel. Runs in the current folder if no arguments are supplied."""
    build_project(path, CURRENT_WORKING_DIRECTORY)


@app.command()
def clean(
    project_name: str = typer.Argument(  # noqa: B008
        ..., help="The name of the project/kernel you want to delete."
    )
) -> None:
    """Deletes the kernel corresponding to the provided project name."""
    clean_project(project_name)


def main() -> None:
    """Main function of ssb_project_cli."""
    app(prog_name="ssb-project")  # pragma: no cover


if __name__ == "__main__":
    main()  # pragma: no cover
