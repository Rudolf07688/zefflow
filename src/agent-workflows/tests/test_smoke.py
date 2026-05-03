"""Smoke tests — import paths, registry, base classes. No LLM calls."""
from agent_workflows import list_workflows
from agent_workflows.workflows.base import BaseWorkflow, WorkflowResult
from agent_workflows.workflows.registry import WORKFLOWS


def test_registry_populated() -> None:
    assert "daily_db_report" in WORKFLOWS
    assert list_workflows() == sorted(WORKFLOWS.keys())


def test_all_registered_workflows_subclass_base() -> None:
    for name, cls in WORKFLOWS.items():
        assert issubclass(cls, BaseWorkflow)
        assert cls.name == name


def test_workflow_result_schema() -> None:
    result = WorkflowResult(
        workflow_name="x", status="success", duration_seconds=0.1, output={"a": 1}
    )
    assert result.status == "success"
    assert result.output == {"a": 1}


def test_unknown_workflow_raises() -> None:
    from agent_workflows import run

    try:
        run("does_not_exist")
    except KeyError as e:
        assert "does_not_exist" in str(e)
    else:
        raise AssertionError("expected KeyError")
