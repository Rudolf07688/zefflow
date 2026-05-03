"""Registry mapping workflow names to their classes.

Add a new workflow:
    1. Subclass BaseWorkflow with a unique class-level `name`.
    2. Import + register it here.
"""
from agent_workflows.workflows.base import BaseWorkflow
from agent_workflows.workflows.daily_db_report import DailyDbReportWorkflow
from agent_workflows.workflows.repo_map_init import RepoMapInitWorkflow
from agent_workflows.workflows.repo_map_refresh import RepoMapRefreshWorkflow

WORKFLOWS: dict[str, type[BaseWorkflow]] = {
    DailyDbReportWorkflow.name: DailyDbReportWorkflow,
    RepoMapInitWorkflow.name: RepoMapInitWorkflow,
    RepoMapRefreshWorkflow.name: RepoMapRefreshWorkflow,
}
