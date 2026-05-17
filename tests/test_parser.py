import pytest

from aurel.parser import RepositoryUrlError, parse_repository_url


@pytest.mark.parametrize(
    ("url", "provider", "owner", "repo"),
    [
        ("https://github.com/openai/codex", "github", "openai", "codex"),
        ("https://github.com/openai/codex/", "github", "openai", "codex"),
        ("https://github.com/openai/codex.git", "github", "openai", "codex"),
        ("http://github.com/example/project_name", "github", "example", "project_name"),
        ("https://gitlab.com/group/project", "gitlab", "group", "project"),
        (
            "https://gitlab.com/group/subgroup/project",
            "gitlab",
            "group/subgroup",
            "project",
        ),
        ("https://bitbucket.org/team/project", "bitbucket", "team", "project"),
    ],
)
def test_parse_valid_repository_url(url, provider, owner, repo):
    parsed = parse_repository_url(url)

    assert parsed.provider == provider
    assert parsed.owner == owner
    assert parsed.name == repo
    assert parsed.full_name == f"{owner}/{repo}"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "https://github.com/owner",
        "https://github.com/owner/repo/issues",
        "git@github.com:owner/repo.git",
        "https://bitbucket.org/team/project/src/main",
        "https://gitlab.com/group/project/-/issues",
    ],
)
def test_reject_invalid_repository_url(url):
    with pytest.raises(RepositoryUrlError):
        parse_repository_url(url)
