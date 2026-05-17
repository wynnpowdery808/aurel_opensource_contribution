from aurel import analyzer
from aurel.analyzer import analyze_repository
from aurel.config import AurelConfig
from aurel.models import IssueReadiness, Repository


def test_analyze_repository_finds_existing_readme_problems():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {"README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md"}

    def fake_file_exists(repo, path):
        return path in found

    def fake_file_content(repo, path):
        return "# TODO\n\nComing soon."

    analysis = analyze_repository(
        repository,
        AurelConfig(),
        file_exists=fake_file_exists,
        file_content=fake_file_content,
        issue_loader=lambda repo: _issue_readiness(1),
    )

    finding_titles = {finding.title for finding in analysis.findings}

    assert "README appears to contain placeholder text" in finding_titles
    assert "Setup path is not obvious from the README" in finding_titles
    assert analysis.score.value < analysis.score.max_value
    assert analysis.recommendations


def test_analyze_repository_does_not_penalize_optional_readme():
    repository = Repository(provider="github", owner="owner", name="repo")
    config = AurelConfig(
        required_signals={
            "readme": False,
            "license": True,
            "contributing": True,
            "security": True,
            "code_of_conduct": True,
        }
    )
    found = {
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/pull_request_template.md",
    }

    def fake_file_exists(repo, path):
        return path in found

    analysis = analyze_repository(
        repository,
        config,
        file_exists=fake_file_exists,
        file_content=lambda repo, path: None,
        issue_loader=lambda repo: _issue_readiness(3),
    )

    assert analysis.file_results["readme"] is False
    assert not any("overview" in finding.title.lower() for finding in analysis.findings)
    assert analysis.score.max_value == 100
    assert analysis.score.value == 100
    assert analysis.score.label == "Excellent contributor readiness"
    assert analysis.recommendations[0].title == "Keep contributor guidance current"


def test_analyze_repository_caps_score_without_beginner_issues():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/pull_request_template.md",
    }

    def fake_file_exists(repo, path):
        return path in found

    def fake_file_content(repo, path):
        return (
            "# Useful README\n\n"
            "Install and setup with `install`. Run the usage example with `run`. "
            "Execute tests with `test`, lint with `lint`, and build with `build`. "
            "This project overview gives contributors enough context to understand "
            "what the repository does and how to verify their first change safely."
        )

    analysis = analyze_repository(
        repository,
        AurelConfig(),
        file_exists=fake_file_exists,
        file_content=fake_file_content,
        issue_loader=lambda repo: _issue_readiness(0),
    )

    assert analysis.score.uncapped_value == 84
    assert analysis.score.value == 84
    assert analysis.score.applied_cap.limit == 89
    assert any(
        finding.title == "Beginner-friendly issue path not detected"
        for finding in analysis.findings
    )


def test_analyze_repository_detects_missing_exact_commands():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {"pyproject.toml", "README.md", "LICENSE", "CONTRIBUTING.md"}

    def fake_file_exists(repo, path):
        return path in found

    def fake_file_content(repo, path):
        return (
            "# Useful README\n\n"
            "This project has setup notes, usage examples, and testing guidance, "
            "but the commands are described in prose instead of exact copyable commands. "
            "The project is intended for new contributors and maintainers."
        )

    analysis = analyze_repository(
        repository,
        AurelConfig(),
        file_exists=fake_file_exists,
        file_content=fake_file_content,
        issue_loader=lambda repo: _issue_readiness(1),
    )

    titles = {finding.title for finding in analysis.findings}

    assert "Install command is not obvious from the README" in titles
    assert "Local run command is not obvious from the README" in titles
    assert "Test command is not obvious from the README" in titles
    assert "Lint command is not obvious from the README" in titles
    assert "Build command is not obvious from the README" in titles
    assert analysis.onboarding_plan.read_first
    assert analysis.onboarding_plan.run_first
    assert analysis.onboarding_plan.change_first


def test_analyze_repository_uses_cached_github_tree_paths(monkeypatch):
    repository = Repository(provider="github", owner="owner", name="repo")
    tree_calls = []
    direct_file_calls = []

    def fake_repository_paths(repo, token=None):
        tree_calls.append((repo.full_name, token))
        return frozenset(
            {
                "pyproject.toml",
                "README.md",
                "LICENSE",
                "CONTRIBUTING.md",
                "SECURITY.md",
                "CODE_OF_CONDUCT.md",
                ".github/ISSUE_TEMPLATE/bug_report.md",
                ".github/pull_request_template.md",
            }
        )

    def fake_remote_file_exists(repo, path, token=None):
        direct_file_calls.append((path, token))
        return False

    monkeypatch.setattr(analyzer, "remote_repository_paths", fake_repository_paths)
    monkeypatch.setattr(analyzer, "remote_file_exists", fake_remote_file_exists)

    analysis = analyze_repository(
        repository,
        AurelConfig(),
        token="fake-github-token",
        file_content=lambda repo, path: (
            "# Useful README\n\n"
            "Install with `python -m pip install -r requirements.txt`. "
            "Run with `aurel https://github.com/owner/repo`. "
            "Test with `python -m pytest`, lint with `ruff check .`, "
            "and build with `python -m build`."
        ),
        issue_loader=lambda repo: _issue_readiness(3),
    )

    assert analysis.profile.name == "Python project"
    assert tree_calls == [("owner/repo", "fake-github-token")]
    assert direct_file_calls == []


def _issue_readiness(count):
    return IssueReadiness(
        checked=True,
        beginner_issue_count=count,
        labels_found=("good first issue",) if count else (),
        confidence="High",
        note="test issue readiness",
    )
