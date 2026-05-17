"""Parse and validate remote repository URLs."""

from __future__ import annotations

from urllib.parse import urlparse

from aurel.models import Repository


class RepositoryUrlError(ValueError):
    """Raised when a repository URL cannot be parsed."""


PROVIDERS = {
    "github.com": "github",
    "www.github.com": "github",
    "gitlab.com": "gitlab",
    "www.gitlab.com": "gitlab",
    "bitbucket.org": "bitbucket",
    "www.bitbucket.org": "bitbucket",
}

GITHUB_ACTION_PATHS = {"tree", "blob", "issues", "pulls", "actions", "wiki"}
BITBUCKET_ACTION_PATHS = {"src", "branch", "issues", "pull-requests", "commits"}
GITLAB_ACTION_PATHS = {"-", "issues", "merge_requests", "tree", "blob"}


def parse_repository_url(url: str) -> Repository:
    """Parse a supported remote repository URL.

    GitHub and Bitbucket URLs must look like owner/repo. GitLab also supports
    nested group paths, such as group/subgroup/repo.
    """

    if not url or not url.strip():
        raise RepositoryUrlError("Please provide a repository URL.")

    parsed = urlparse(url.strip())

    if parsed.scheme not in {"http", "https"}:
        raise RepositoryUrlError("Repository URL must start with http:// or https://.")

    provider = PROVIDERS.get(parsed.netloc.lower())
    if provider is None:
        raise RepositoryUrlError(
            "Repository URL must point to GitHub, GitLab, or Bitbucket."
        )

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise RepositoryUrlError("Repository URL must include an owner and repo name.")

    if provider == "github":
        return _parse_two_part_provider(parts, provider, GITHUB_ACTION_PATHS)

    if provider == "bitbucket":
        return _parse_two_part_provider(parts, provider, BITBUCKET_ACTION_PATHS)

    return _parse_gitlab(parts)


def parse_github_url(url: str) -> Repository:
    """Backward-compatible parser for GitHub-only callers."""

    repository = parse_repository_url(url)
    if repository.provider != "github":
        raise RepositoryUrlError("Repository URL must point to github.com.")
    return repository


def _parse_two_part_provider(
    parts: list[str],
    provider: str,
    action_paths: set[str],
) -> Repository:
    if len(parts) != 2 or parts[0] in action_paths or parts[1] in action_paths:
        raise RepositoryUrlError(
            f"{provider.title()} URL must look like https://host/owner/repo."
        )

    owner, repo_name = parts
    repo_name = _strip_git_suffix(repo_name)

    if not _is_valid_path_part(owner) or not _is_valid_path_part(repo_name):
        raise RepositoryUrlError("Repository owner and name must be valid path parts.")

    return Repository(provider=provider, owner=owner, name=repo_name)


def _parse_gitlab(parts: list[str]) -> Repository:
    if any(part in GITLAB_ACTION_PATHS for part in parts):
        raise RepositoryUrlError(
            "GitLab URL must point to a repository, not a repository subpage."
        )

    repo_name = _strip_git_suffix(parts[-1])
    owner = "/".join(parts[:-1])

    if not all(_is_valid_path_part(part) for part in [*parts[:-1], repo_name]):
        raise RepositoryUrlError("Repository path must contain valid path parts.")

    return Repository(provider="gitlab", owner=owner, name=repo_name)


def _strip_git_suffix(value: str) -> str:
    if value.endswith(".git"):
        return value[:-4]
    return value


def _is_valid_path_part(value: str) -> bool:
    """Return True when a URL path part is safe for a repository path."""

    if value in {"", ".", ".."}:
        return False

    return all(character not in value for character in (" ", "\t", "\n", "\r"))
