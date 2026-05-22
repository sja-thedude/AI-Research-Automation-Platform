"""Multi-agent orchestration scaffold.

A minimal, dependency-light orchestrator that coordinates specialized agents
(researcher, writer, critic…) over a shared scratchpad. It is intentionally
provider-agnostic and synchronous; production agentic loops (tool calling,
LangGraph state machines, parallel fan-out) plug into `Agent.run` and
`Orchestrator.run` without changing callers.

This is the documented extension point for the platform's "multi-agent AI
systems" capability.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import get_chat_model
from .retrieval import retrieve

logger = logging.getLogger("neuraforge")


@dataclass
class AgentContext:
    """Shared state passed between agents in a run."""

    task: str
    owner_id: str | None = None
    team_id: str | None = None
    scratchpad: list[dict] = field(default_factory=list)  # [{agent, output}]

    def note(self, agent: str, output: str) -> None:
        self.scratchpad.append({"agent": agent, "output": output})

    def transcript(self) -> str:
        return "\n\n".join(f"## {n['agent']}\n{n['output']}" for n in self.scratchpad)


@dataclass
class Agent:
    """A single role-played LLM agent with an optional retrieval tool."""

    name: str
    system_prompt: str
    model: str | None = None
    use_retrieval: bool = False
    temperature: float = 0.2

    def run(self, ctx: AgentContext) -> str:
        context_block = ""
        if self.use_retrieval:
            hits = retrieve(ctx.task, owner_id=ctx.owner_id, team_id=ctx.team_id)
            context_block = "\n\n".join(f"- {h.content}" for h in hits)

        llm = get_chat_model(self.model, self.temperature)
        prompt = (
            f"Task: {ctx.task}\n\n"
            f"Knowledge:\n{context_block or '(none)'}\n\n"
            f"Prior work:\n{ctx.transcript() or '(none)'}\n\n"
            f"Now perform your role as {self.name}."
        )
        resp = llm.invoke(
            [SystemMessage(content=self.system_prompt), HumanMessage(content=prompt)]
        )
        ctx.note(self.name, resp.content)
        return resp.content


class Orchestrator:
    """Runs a pipeline of agents sequentially over a shared context."""

    def __init__(self, agents: list[Agent]):
        self.agents = agents

    def run(self, task: str, *, owner_id=None, team_id=None) -> AgentContext:
        ctx = AgentContext(task=task, owner_id=owner_id, team_id=team_id)
        for agent in self.agents:
            logger.info("Agent '%s' running", agent.name)
            agent.run(ctx)
        return ctx


def research_team() -> Orchestrator:
    """A ready-made researcher -> writer -> critic pipeline."""
    return Orchestrator(
        [
            Agent(
                name="Researcher",
                system_prompt="You gather and synthesize facts from the knowledge base. Be thorough and cite specifics.",
                use_retrieval=True,
            ),
            Agent(
                name="Writer",
                system_prompt="You turn research notes into a clear, well-structured report.",
            ),
            Agent(
                name="Critic",
                system_prompt="You review the report for gaps, inaccuracies and clarity, then output a final improved version.",
                temperature=0.0,
            ),
        ]
    )
