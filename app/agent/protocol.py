from dataclasses import dataclass, field
from uuid import uuid4

MAIN_AGENT = "main"
APPOINTMENT_AGENT = "appointment"
COURSE_AGENT = "course"
OPERATIONS_AGENT = "operations"

SUPPORTED_AGENTS = {
    MAIN_AGENT,
    APPOINTMENT_AGENT,
    COURSE_AGENT,
    OPERATIONS_AGENT,
}


@dataclass(frozen=True)
class AgentHandoff:
    from_agent: str
    to_agent: str
    reason: str
    trace_id: str = field(default_factory=lambda: uuid4().hex)


def normalized_agent(agent: str | None) -> str:
    value = (agent or MAIN_AGENT).strip().lower()
    return value if value in SUPPORTED_AGENTS else MAIN_AGENT

