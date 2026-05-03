"""Demo workflow: inspect the DB, then write an exec-style daily report."""
from typing import Any, ClassVar

from agent_workflows.agents.db_inspector import DbInspectorAgent
from agent_workflows.agents.reporter import ReporterAgent
from agent_workflows.workflows.base import BaseWorkflow


class DailyDbReportWorkflow(BaseWorkflow):
    name: ClassVar[str] = "daily_db_report"

    DEFAULT_INSPECTION_PROMPT = (
        "Inspect the database. List all tables, count rows in each, and flag any "
        "anomalies (empty tables, suspicious nulls, outlier values). Be concise."
    )

    def _execute(self) -> dict[str, Any]:
        inspection_prompt = self.config.get(
            "inspection_prompt", self.DEFAULT_INSPECTION_PROMPT
        )

        findings = DbInspectorAgent().run(inspection_prompt)

        report = ReporterAgent().run(
            f"Turn the following DB findings into a daily exec report:\n\n{findings}"
        )

        return {"findings": findings, "report": report}
