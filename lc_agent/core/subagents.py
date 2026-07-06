from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ContextT, ModelRequest, ModelResponse, ResponseT
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from lc_agent.db.engine import get_async_engine
from lc_agent.db.subagent_repository import SubAgentRunRepository


class TaskInput(BaseModel):
    description: str = Field(description="交给子Agent独立完成的完整任务描述。")
    subagent_type: str = Field(description="要调用的子Agent ID。")


TASK_SYSTEM_PROMPT = """## `task` 子Agent工具

你可以调用 `task` 工具把复杂、独立、需要多步骤完成的任务交给子Agent。
调用时必须提供：
- `subagent_type`: 可用子Agent之一
- `description`: 完整任务描述，包括背景、目标、输出格式

只在任务确实适合委托时调用子Agent；简单问题直接自己完成。
"""


def _last_ai_text(result: dict[str, Any]) -> str:
    for message in reversed(result.get("messages", [])):
        if isinstance(message, AIMessage):
            text = message.text if hasattr(message, "text") else message.content
            if isinstance(text, str) and text.strip():
                return text.strip()
            if message.content:
                return str(message.content).strip()
    return "子Agent未返回有效结果。"


def _get_runtime_configurable(runtime: Any) -> dict[str, Any]:
    config = getattr(runtime, "config", None) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    return dict(configurable)


def _json_safe_event(event: dict) -> dict[str, Any]:
    data = event.get("data", {})
    safe_data: dict[str, Any] = {}
    for key in ("event", "name", "run_id", "parent_ids"):
        if key in event:
            safe_data[key] = event[key]
    if isinstance(data, dict):
        safe_data["data"] = {
            k: str(v)[:500] if not isinstance(v, (str, int, float, bool, type(None))) else v
            for k, v in data.items()
        }
    return safe_data


def build_subagent_task_tool(
    *,
    parent_agent_id: str,
    subagents: Mapping[str, Runnable],
    subagent_names: Mapping[str, str],
    db_url: str,
    max_depth: int = 3,
) -> StructuredTool:
    async def task(description: str, subagent_type: str, runtime: Any) -> str | Command:
        if subagent_type not in subagents:
            allowed = ", ".join(sorted(subagents))
            return f"拒绝调用子Agent：`{subagent_type}` 不在允许列表中。可用子Agent：{allowed}"

        configurable = _get_runtime_configurable(runtime)
        call_stack = list(configurable.get("lc_agent_call_stack") or [parent_agent_id])
        if subagent_type in call_stack:
            return f"拒绝调用子Agent：检测到循环调用 {' -> '.join([*call_stack, subagent_type])}"
        if len(call_stack) >= max_depth:
            return f"拒绝调用子Agent：调用深度超过限制 {max_depth}。当前调用链：{' -> '.join(call_stack)}"

        parent_thread_id = configurable.get("thread_id", "")
        tool_call_id = getattr(runtime, "tool_call_id", None) or "unknown-tool-call"
        sub_thread_id = f"{parent_thread_id}:sub:{tool_call_id}:{subagent_type}"
        sub_config: RunnableConfig = {
            "configurable": {
                **configurable,
                "thread_id": sub_thread_id,
                "lc_agent_call_stack": [*call_stack, subagent_type],
                "ls_agent_type": "subagent",
            }
        }

        parent_session_id = parent_thread_id.split(":sub:")[0] or parent_thread_id

        content_parts: list[str] = []
        async with AsyncSession(get_async_engine(db_url), expire_on_commit=False) as session:
            repo = SubAgentRunRepository(session)
            run = await repo.create_run(
                parent_session_id=parent_session_id,
                parent_message_id=None,
                parent_tool_run_id=tool_call_id,
                parent_agent_id=parent_agent_id,
                sub_agent_id=subagent_type,
                sub_agent_name=subagent_names.get(subagent_type, subagent_type),
                sub_thread_id=sub_thread_id,
                task_description=description,
                depth=len(call_stack),
            )

            try:
                async for event in subagents[subagent_type].astream_events(
                    {"messages": [HumanMessage(content=description)]},
                    config=sub_config,
                    version="v2",
                ):
                    await repo.append_event(
                        run_id=run.id,
                        event_type=event.get("event", ""),
                        payload=_json_safe_event(event),
                    )
                    if event.get("event") == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            text = chunk.content
                            if isinstance(text, list):
                                text = "".join(
                                    p.get("text", "") if isinstance(p, dict) else str(p) for p in text
                                )
                            if isinstance(text, str):
                                content_parts.append(text)

                content = "".join(content_parts)
                await repo.finish_run(
                    run_id=run.id,
                    status="done",
                    summary=content[:200],
                    final_result=content,
                )
            except Exception as e:
                await repo.finish_run(
                    run_id=run.id,
                    status="error",
                    summary=str(e)[:200],
                    final_result=str(e),
                )
                raise

        return Command(update={"messages": [ToolMessage(content, tool_call_id=tool_call_id)]})

    return StructuredTool.from_function(
        name="task",
        description=TASK_SYSTEM_PROMPT,
        coroutine=task,
        args_schema=TaskInput,
        infer_schema=False,
    )


class SubAgentMiddleware(AgentMiddleware[Any, ContextT, ResponseT]):
    def __init__(
        self,
        *,
        parent_agent_id: str,
        subagents: Mapping[str, Runnable],
        subagent_names: Mapping[str, str],
        db_url: str,
        max_depth: int = 3,
    ) -> None:
        super().__init__()
        self.parent_agent_id = parent_agent_id
        self.subagents = dict(subagents)
        self.subagent_names = dict(subagent_names)
        available = "\n".join(f"- {agent_id}: {subagent_names.get(agent_id, agent_id)}" for agent_id in self.subagents)
        self.system_prompt = f"{TASK_SYSTEM_PROMPT}\n\n可用子Agent：\n{available}"
        self.tools = [
            build_subagent_task_tool(
                parent_agent_id=parent_agent_id,
                subagents=self.subagents,
                subagent_names=self.subagent_names,
                db_url=db_url,
                max_depth=max_depth,
            )
        ]

    def wrap_model_call(self, request: ModelRequest[ContextT], handler):
        if request.system_message is not None:
            content = [*request.system_message.content_blocks, {"type": "text", "text": f"\n\n{self.system_prompt}"}]
        else:
            content = [{"type": "text", "text": self.system_prompt}]
        return handler(request.override(system_message=SystemMessage(content=content)))

    async def awrap_model_call(self, request: ModelRequest[ContextT], handler):
        if request.system_message is not None:
            content = [*request.system_message.content_blocks, {"type": "text", "text": f"\n\n{self.system_prompt}"}]
        else:
            content = [{"type": "text", "text": self.system_prompt}]
        return await handler(request.override(system_message=SystemMessage(content=content)))