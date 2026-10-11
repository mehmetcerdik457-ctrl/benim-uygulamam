import pytest

from omega_mvi.inspection.pr_review import review_changed_files


def test_generates_categorized_advisory_findings_with_supplied_citations():
    report = review_changed_files(
        [
            {
                "path": "src/auth.py",
                "sanitized_summary": "Updated token handling and authorization checks",
                "start_line": 12,
                "end_line": 18,
            }
        ]
    )

    assert [finding.category for finding in report.findings] == [
        "security",
        "authorization",
    ]
    assert all(
        finding.citation.path == "src/auth.py"
        and finding.citation.start_line == 12
        and finding.citation.end_line == 18
        for finding in report.findings
    )
    assert report.advisory_only is True
    assert report.approval_authority is False


def test_does_not_echo_supplied_summary_in_findings():
    summary = "Added a private key to a test fixture"
    report = review_changed_files(
        [
            {
                "path": "tests/test_auth.py",
                "sanitized_summary": summary,
                "start_line": 3,
                "end_line": 5,
            }
        ]
    )

    assert summary not in repr(report)
    assert report.findings[0].category == "security"


@pytest.mark.parametrize(
    "change",
    [
        {"path": "../outside.py"},
        {"path": "/absolute.py"},
        {"start_line": 0},
        {"end_line": 0},
        {"start_line": True},
        {"extra": "raw diff"},
    ],
)
def test_rejects_invalid_or_unsupported_summary_fields(change):
    item = {
        "path": "src/module.py",
        "sanitized_summary": "Updated error handling",
        "start_line": 1,
        "end_line": 2,
    }
    item.update(change)

    with pytest.raises(ValueError):
        review_changed_files([item])


def test_reports_empty_findings_when_no_rule_matches():
    report = review_changed_files(
        [
            {
                "path": "src/formatting.py",
                "sanitized_summary": "Reformatted helper names",
                "start_line": 1,
                "end_line": 4,
            }
        ]
    )

    assert report.findings == ()
