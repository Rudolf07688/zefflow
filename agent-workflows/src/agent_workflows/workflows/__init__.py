"""Workflow classes — first-class orchestration units."""
from agent_workflows.workflows.base import BaseWorkflow, WorkflowResult
from agent_workflows.workflows.daily_db_report import DailyDbReportWorkflow
from agent_workflows.workflows.registry import WORKFLOWS
from agent_workflows.workflows.repo_map_refresh import RepoMapRefreshWorkflow

__all__ = [
    "BaseWorkflow", "DailyDbReportWorkflow", "RepoMapRefreshWorkflow",
    "WORKFLOWS", "WorkflowResult",
]
