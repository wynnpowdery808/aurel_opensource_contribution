from aurel.models import Repository
from aurel.profiles import detect_profile


def test_detect_python_profile_from_project_files():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {"pyproject.toml", "requirements.txt"}

    def fake_file_exists(repo, path):
        return path in found

    profile = detect_profile(repository, file_exists=fake_file_exists)

    assert profile.name == "Python project"
    assert profile.confidence == "Medium"
    assert profile.evidence == ("pyproject.toml", "requirements.txt")


def test_detect_general_profile_when_no_signals_match():
    repository = Repository(provider="github", owner="owner", name="repo")

    def fake_file_exists(repo, path):
        return False

    profile = detect_profile(repository, file_exists=fake_file_exists)

    assert profile.name == "General repository"
    assert profile.confidence == "Low"
