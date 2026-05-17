from aurel.models import Repository
from aurel.workflow import analyze_workflow_readiness


def test_workflow_readiness_detects_issue_and_pr_templates():
    repository = Repository(provider="github", owner="owner", name="repo")
    found = {".github/ISSUE_TEMPLATE/bug_report.md", ".github/pull_request_template.md"}

    def fake_file_exists(repo, path):
        return path in found

    workflow = analyze_workflow_readiness(repository, file_exists=fake_file_exists)

    assert workflow.issue_template_found is True
    assert workflow.pull_request_template_found is True
    assert workflow.issue_template_path == ".github/ISSUE_TEMPLATE/bug_report.md"
    assert workflow.pull_request_template_path == ".github/pull_request_template.md"
    assert workflow.confidence == "High"


def test_workflow_readiness_reports_missing_templates():
    repository = Repository(provider="gitlab", owner="group", name="project")

    workflow = analyze_workflow_readiness(
        repository,
        file_exists=lambda repo, path: False,
    )

    assert workflow.issue_template_found is False
    assert workflow.pull_request_template_found is False
    assert "not detected" in workflow.note
