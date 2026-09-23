"""Sub-agent stream run tracking for SSE events."""


import asyncio
import time
from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable
from typing import Any

from lc_agent.core.http_trace import pop_subagent_traces
from lc_agent.server import persistence


@dataclass
class _SubAgentRun:
    tool_call_id: str
    sub_session_id: str
    name: str
    query: str
    tokens: list[str] = field(default_factory=list)
    thinking: list[str] = field(default_factory=list)
    content_parts: list[str] = field(default_factory=list)
    inner_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    status: str = "running"
    in_thinking: bool = False
    http_traces: list[dict[str, Any]] | None = None


class SubAgentRunTracker:
    def __init__(
        self,
        *,
        parent_thread_id: str,
        user_id: str,
        subagent_display_map: dict[str, str],
        tool_calls: list[dict[str, Any]],
        existing_subsession_ids: set[str] | None = None,
        usage_rounds: list[dict[str, Any]] | None = None,
    ) -> None:
        self.parent_thread_id = parent_thread_id
        self.user_id = user_id
        self.subagent_display_map = subagent_display_map
        self.tool_calls = tool_calls
        self.existing_subsession_ids = existing_subsession_ids or set()
        # 流式过程的内存 usage 列表引用（主+子混排，role="sub" 打标）。
        # done 时按 sub_session_id 摘出该子会话的 rounds，随子会话消息落库，
        # 仅供子会话页展示 token；总量统计走 record_usage 全量落库，不受影响。
        self._usage_rounds = usage_rounds if usage_rounds is not None else []
        self._runs: dict[str, _SubAgentRun] = {}
        self._tasks: list[asyncio.Task[Any]] = []
        self._run_persistence_tasks: dict[str, asyncio.Task[Any]] = {}

    def handle_event(self, event_type: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if event_type == "tool_call" and payload.get("is_subagent"):
            return event_type, self._enrich_subagent_tool_call(payload)
        if event_type == "subagent_start":
            return event_type, self._handle_start(payload)
        if event_type == "subagent_token":
            self._handle_token(payload)
            return event_type, payload
        if event_type == "subagent_thinking":
            self._handle_thinking(payload)
            return event_type, payload
        if event_type == "subagent_tool_call":
            self._handle_tool_call(payload)
            return event_type, payload
        if event_type == "subagent_tool_result":
            self._handle_tool_result(payload)
            return event_type, payload
        if event_type == "subagent_done":
            return event_type, self._handle_done(payload)
        if event_type in ("summarization_start", "summarization_done", "summarization_failed"):
            return event_type, self._handle_summarization(event_type, payload)
        return event_type, payload

    def finalize_open_runs(self, status: str = "error") -> list[tuple[str, dict[str, Any]]]:
        terminal_events: list[tuple[str, dict[str, Any]]] = []
        for tool_call_id in list(self._runs.keys()):
            terminal_events.append((
                "subagent_done",
                self._handle_done({"tool_call_id": tool_call_id, "status": status}),
            ))
        return terminal_events

    async def drain(self) -> None:
        while self._tasks:
            tasks = self._tasks
            self._tasks = []
            await asyncio.gather(*tasks)

    def _enqueue_persistence(self, tool_call_id: str, operation_factory: Callable[[], Awaitable[Any]]) -> None:
        previous_task = self._run_persistence_tasks.get(tool_call_id)

        async def run_ordered() -> None:
            if previous_task is not None:
                await previous_task
            try:
                await operation_factory()
            finally:
                if self._run_persistence_tasks.get(tool_call_id) is current_task:
                    self._run_persistence_tasks.pop(tool_call_id, None)

        current_task = asyncio.create_task(run_ordered())
        self._run_persistence_tasks[tool_call_id] = current_task
        self._tasks.append(current_task)

    def _handle_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool_call_id = payload["tool_call_id"]
        subagent_type = payload.get("subagent_type")
        raw_name = payload.get("name") or subagent_type or "sub-agent"
        if subagent_type:
            display_name = self.subagent_display_map.get(subagent_type, raw_name)
        else:
            display_name = self.subagent_display_map.get(raw_name, raw_name)
        query = payload.get("query", "")
        sub_session_id = f"{self.parent_thread_id}--sa--{tool_call_id}"
        run = _SubAgentRun(
            tool_call_id=tool_call_id,
            sub_session_id=sub_session_id,
            name=display_name,
            query=query,
        )
        self._runs[tool_call_id] = run
        existed = sub_session_id in self.existing_subsession_ids
        self._mark_parent_tool_call(tool_call_id, display_name, sub_session_id)
        if not existed:
            self._enqueue_persistence(
                tool_call_id,
                lambda: persistence.create_subsession(
                    sub_session_id,
                    self.parent_thread_id,
                    tool_call_id,
                    display_name,
                    f"{display_name}: {query}",
                    self.user_id,
                ),
            )
            self._enqueue_persistence(
                tool_call_id,
                lambda: persistence.save_subsession_delegation_message(
                    sub_session_id,
                    query,
                ),
            )
        return {**payload, "name": display_name, "sub_session_id": sub_session_id}

    def _handle_token(self, payload: dict[str, Any]) -> None:
        run = self._runs.get(payload.get("tool_call_id"))
        if run is not None:
            content = payload.get("content", "")
            if run.in_thinking:
                run.content_parts.append("<!--THINK_END-->")
                run.in_thinking = False
            run.tokens.append(content)
            run.content_parts.append(content)

    def _handle_thinking(self, payload: dict[str, Any]) -> None:
        run = self._runs.get(payload.get("tool_call_id"))
        if run is not None:
            content = payload.get("content", "")
            if not run.in_thinking:
                run.content_parts.append("<!--THINK_START-->")
                run.in_thinking = True
            run.thinking.append(content)
            run.content_parts.append(content)

    def _handle_tool_call(self, payload: dict[str, Any]) -> None:
        run = self._runs.get(payload.get("tool_call_id"))
        if run is None:
            return
        tool_index = len(run.inner_tool_calls)
        run.inner_tool_calls.append({
            "name": payload.get("name", ""),
            "args": payload.get("args", {}),
            "status": "running",
            "startTime": int(time.time() * 1000),
        })
        if run.in_thinking:
            run.content_parts.append("<!--THINK_END-->")
            run.in_thinking = False
        run.content_parts.append(f"\n<!--TOOL:{tool_index}-->\n")

    def _handle_tool_result(self, payload: dict[str, Any]) -> None:
        run = self._runs.get(payload.get("tool_call_id"))
        if run is None:
            return
        tool_name = payload.get("name", "")
        for tool_call in reversed(run.inner_tool_calls):
            if tool_call.get("name") == tool_name and tool_call.get("status") == "running":
                result = payload.get("result", "")
                status = payload.get("status") or ("error" if payload.get("is_error") else "done")
                start_time = tool_call.get("startTime")
                tool_call["status"] = status
                tool_call["result"] = result
                tool_call["duration"] = int(time.time() * 1000) - start_time if start_time else None
                tool_call["resultLength"] = len(result)
                return

    def _sub_usage_rounds(self, sub_session_id: str) -> list[dict[str, Any]]:
        """摘出该子会话的 usage rounds（过滤摘要行），仅供子会话页展示 token。"""
        from lc_agent.server.stream_utils import is_summarize_usage_row

        return [
            r
            for r in self._usage_rounds
            if r.get("role") == "sub"
            and r.get("sub_session_id") == sub_session_id
            and not is_summarize_usage_row(r)
        ]

    def _handle_done(self, payload: dict[str, Any]) -> dict[str, Any]:
        tool_call_id = payload["tool_call_id"]
        run = self._runs.pop(tool_call_id, None)
        if run is None:
            return payload
        run.status = payload.get("status", "done")
        content = self._build_content(run)
        traces = pop_subagent_traces(run.sub_session_id) or None
        run.http_traces = traces
        sub_rounds = self._sub_usage_rounds(run.sub_session_id)
        sub_usage = (
            {
                "rounds": sub_rounds,
                "tool_call_count": len(run.inner_tool_calls),
            }
            if sub_rounds
            else None
        )
        self._enqueue_persistence(
            tool_call_id,
            lambda: persistence.finalize_subsession_message(
                run.sub_session_id,
                content,
                tool_calls=run.inner_tool_calls or None,
                usage=sub_usage,
                http_traces=traces,
            ),
        )
        result_preview = content or payload.get("result_preview", "")
        done_payload = {
            **payload,
            "result_preview": result_preview[:150],
            "status": run.status,
            "duration": int((time.time() - run.start_time) * 1000),
            "tool_count": len(run.inner_tool_calls),
            "token_count": len(run.tokens),
        }
        if traces:
            done_payload["http_traces"] = traces
        if sub_usage:
            done_payload["usage"] = sub_usage
        return done_payload

    def _handle_summarization(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """子会话内部压缩：留痕进子会话 content_parts，前端按 tool_call_id 归属。

        主会话的压缩不走这里（tool_call_id 为空，直接透传，前端挂到当前消息）。
        """
        from lc_agent.server.stream_utils import (
            _sanitize_summarize_count,
            _sanitize_summarize_reason,
        )

        tool_call_id = payload.get("tool_call_id") or ""
        if not tool_call_id:
            return payload
        run = self._runs.get(tool_call_id)
        if run is None:
            return payload
        if event_type == "summarization_done":
            summarized = _sanitize_summarize_count(payload.get("summarized_count", 0))
            kept = _sanitize_summarize_count(payload.get("kept_count", 0))
            run.content_parts.append(f"\n<!--SUMMARIZE:{summarized}:{kept}-->\n")
            return {**payload, "summarized_count": summarized, "kept_count": kept}
        if event_type == "summarization_failed":
            reason = _sanitize_summarize_reason(payload.get("reason", ""))
            run.content_parts.append(f"\n<!--SUMMARIZE_FAIL:{reason}-->\n")
            return {**payload, "reason": reason}
        return payload

    def _mark_parent_tool_call(self, tool_call_id: str, display_name: str, sub_session_id: str) -> None:
        for tool_call in self.tool_calls:
            if tool_call.get("runId") == tool_call_id or tool_call.get("run_id") == tool_call_id:
                tool_call["is_subagent"] = True
                tool_call["sub_session_id"] = sub_session_id
                tool_call["name"] = display_name
                return

    def _enrich_subagent_tool_call(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_name = payload.get("name", "sub-agent")
        display_name = self.subagent_display_map.get(raw_name, raw_name)
        tool_call_id = payload.get("run_id") or payload.get("runId") or payload.get("tool_call_id")
        if not tool_call_id:
            return {**payload, "name": display_name}
        sub_session_id = f"{self.parent_thread_id}--sa--{tool_call_id}"
        self._mark_parent_tool_call(tool_call_id, display_name, sub_session_id)
        return {**payload, "name": display_name, "sub_session_id": sub_session_id}

    @staticmethod
    def _build_content(run: _SubAgentRun) -> str:
        parts = list(run.content_parts)
        if run.in_thinking:
            parts.append("<!--THINK_END-->")
        return "".join(parts)
