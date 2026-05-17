from aurel.checks import (
    COMMUNITY_FILES,
    analyze_community_signals,
    check_community_files,
)
from aurel.config import AurelConfig
from aurel.models import Repository


def test_check_community_files_uses_expected_file_list():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {"README.md", "LICENSE"}
    requested_files = []

    def fake_file_exists(repo, path):
        requested_files.append((repo.provider, repo.owner, repo.name, path))
        return path in found

    results = check_community_files(repository, file_exists=fake_file_exists)

    assert set(results) == set(COMMUNITY_FILES)
    assert results["README.md"] is True
    assert results["LICENSE"] is True
    assert results["CONTRIBUTING.md"] is False
    assert requested_files == [
        ("github", "owner", "repo", filename) for filename in COMMUNITY_FILES
    ]


def test_check_community_files_accepts_configured_file_list():
    repository = Repository(provider="github", owner="owner", name="repo")

    def fake_file_exists(repo, path):
        return path == "docs/CONTRIBUTING.md"

    results = check_community_files(
        repository,
        file_exists=fake_file_exists,
        filenames=("docs/CONTRIBUTING.md",),
    )

    assert results == {"docs/CONTRIBUTING.md": True}


def test_analyze_community_signals_accepts_alternate_readme_location():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {"docs/index.md", "LICENSE", "CONTRIBUTING.md"}

    def fake_file_exists(repo, path):
        return path in found

    signals = analyze_community_signals(
        repository,
        AurelConfig(),
        file_exists=fake_file_exists,
    )
    by_key = {signal.key: signal for signal in signals}

    assert by_key["readme"].present is True
    assert by_key["readme"].matched_path == "docs/index.md"
    assert by_key["license"].present is True
    assert by_key["security"].present is False


def test_analyze_community_signals_respects_optional_requirement():
    repository = Repository(provider="github", owner="owner", name="repo")
    config = AurelConfig(required_signals={"readme": False})

    def fake_file_exists(repo, path):
        return False

    signals = analyze_community_signals(
        repository,
        config,
        file_exists=fake_file_exists,
    )
    readme = next(signal for signal in signals if signal.key == "readme")

    assert readme.present is False
    assert readme.required is False
    assert "optional" in readme.note
