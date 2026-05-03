"""Agent that turns raw findings into a polished executive report."""
from typing import ClassVar

from agent_workflows.agents.base import BaseAgent


class ReporterAgent(BaseAgent):
    role: ClassVar[str] = "reporter"

    instructions: ClassVar[list[str]] = [
        "You are an executive analyst.",
        "Turn the inputs into a tight, scannable daily report in markdown.",
        "Use sections: TL;DR, Key numbers, Anomalies, Recommended next steps.",
        "Use tables where helpful. No fluff, no apology, no preamble.",
    ]
