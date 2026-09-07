import pytest
from unittest.mock import MagicMock

from lc_agent.core.models import AgentPreset, SubAgentLink
from lc_agent.core.engine import AgentEngine
from lc_agent.core.engine_helpers.subagent_helpers import SubAgentDescriptor


MINIMAL_CONFIG = {
    "provider": {
        "test": {
            "base_url": "http://localhost:4000/v1",
            "api_key": "test",
            "models": [{"id": "test-model", "context_limit": 8000}],
        }
    },
    "agent": {"default_model": "test-model", "max_subagent_depth": 2},
}


def test_engine_no_longer_exposes_legacy_make_subagent_tool():
    engine = AgentEngine(MINIMAL_CONFIG)
    assert not hasattr(engine, "_make_subagent_tool")


def test_get_subagent_tool_names_returns_empty_before_build():
    engine = AgentEngine(MINIMAL_CONFIG)
    names = engine.get_subagent_tool_names("chat")
    assert names == set()


def test_build_subagent_registry_uses_link_description_then_default_fallback():
    engine = AgentEngine(MINIMAL_CONFIG)
    child_with_link = AgentPreset(
        id="child-with-link",
        name="资料查询",
        system_prompt="查资料",
        default_model="test-model",
        default_delegation_description="默认描述不会被使用",
        can_be_subagent=True,
    )
    child_with_default = AgentPreset(
        id="child-with-default",
        name="代码审查",
        system_prompt="做代码审查",
        default_model="test-model",
        default_delegation_description="当你需要代码审查时调用它",
        can_be_subagent=True,
    )
    parent = AgentPreset(
        id="parent",
        name="主智能体",
        system_prompt="负责协调",
        default_model="test-model",
        subagents=[
            SubAgentLink(
                agent_id="child-with-link",
                delegation_description="当你需要查资料时调用它",
            ),
            SubAgentLink(
                agent_id="child-with-default",
                delegation_description="",
            ),
        ],
    )

    engine._presets = {
        child_with_link.id: child_with_link,
        child_with_default.id: child_with_default,
        parent.id: parent,
    }

    registry = engine._build_subagent_registry(parent, depth=0, building_set=frozenset())

    assert registry == {
        "资料查询": SubAgentDescriptor(
            subagent_type="资料查询",
            preset_id="child-with-link",
            display_name="资料查询",
            description="当你需要查资料时调用它",
        ),
        "代码审查": SubAgentDescriptor(
            subagent_type="代码审查",
            preset_id="child-with-default",
            display_name="代码审查",
            description="当你需要代码审查时调用它",
        ),
    }


def test_build_agent_injects_single_task_tool_and_records_display_map(monkeypatch):
    engine = AgentEngine(MINIMAL_CONFIG)
    child = AgentPreset(
        id="research-agent",
        name="研究专家",
        system_prompt="做研究",
        default_model="test-model",
        default_delegation_description="当你需要深入研究时调用它",
        can_be_subagent=True,
    )
    parent = AgentPreset(
        id="parent-agent",
        name="主智能体",
        system_prompt="协调任务",
        default_model="test-model",
        subagents=[
            SubAgentLink(
                agent_id="research-agent",
                delegation_description="",
            )
        ],
    )
    engine._presets = {child.id: child, parent.id: parent}

    captured = {}

    monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
    monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)

    engine.build_agent(parent, cache_key="parent-agent")

    task_tools = [tool for tool in captured["tools"] if tool.name == "task"]

    assert [tool.name for tool in task_tools] == ["task"]
    assert all(not tool.name.startswith("subagent_") for tool in captured["tools"])
    assert task_tools[0].description.startswith("Delegate a task to one configured sub-agent.")
    assert "stateless" in task_tools[0].description
    assert "final and only reply" in task_tools[0].description
    assert "<subagent_type>研究专家</subagent_type>" in task_tools[0].description
    assert "<when_to_use>" in task_tools[0].description
    assert "当你需要深入研究时调用它" in task_tools[0].description
    assert engine.get_subagent_tool_names("parent-agent") == {"task"}
    assert engine.get_subagent_display_name_map("parent-agent") == {"研究专家": "研究专家"}


def test_build_subagent_registry_injects_general_purpose():
    engine = AgentEngine(MINIMAL_CONFIG)
    parent = AgentPreset(
        id="parent-agent",
        name="主智能体",
        system_prompt="协调任务",
        default_model="test-model",
        enable_general_purpose_subagent=True,
    )
    engine._presets = {parent.id: parent}

    registry = engine._build_subagent_registry(parent, depth=0, building_set=frozenset())

    assert "general-purpose" in registry
    gp = registry["general-purpose"]
    assert gp.preset_id == "__gp__:parent-agent"
    assert gp.display_name == "通用助手"
    assert "all tools as the main agent" in gp.description

    # The cloned general-purpose preset must not have subagents or gp flag
    gp_preset = engine._presets["__gp__:parent-agent"]
    assert gp_preset.subagents is None
    assert gp_preset.enable_general_purpose_subagent is False


def test_build_subagent_registry_no_general_purpose_when_disabled():
    engine = AgentEngine(MINIMAL_CONFIG)
    parent = AgentPreset(
        id="parent-agent",
        name="主智能体",
        system_prompt="协调任务",
        default_model="test-model",
        enable_general_purpose_subagent=False,
    )
    engine._presets = {parent.id: parent}

    registry = engine._build_subagent_registry(parent, depth=0, building_set=frozenset())

    assert "通用助手" not in registry
    assert "__gp__:parent-agent" not in engine._presets


def test_build_agent_injects_delegation_prompt_into_subagent(monkeypatch):
    """_depth > 0 时，SubagentDelegationMiddleware 应作为 middleware[0] (prepend=True)，system_prompt 保持不变。"""
    from lc_agent.prompts.subagent_prompts import SUBAGENT_DELEGATION_PROMPT

    engine = AgentEngine(MINIMAL_CONFIG)
    child = AgentPreset(
        id="worker",
        name="worker",
        system_prompt="你是专门做研究的助手。",
        default_model="test-model",
        can_be_subagent=True,
    )
    engine._presets = {child.id: child}

    captured = {}

    monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
    monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)

    engine.build_agent(child, cache_key="worker", _depth=1)

    system_prompt = captured.get("system_prompt", "")
    middleware = captured.get("middleware", [])

    # system_prompt is wrapped in <instructions> block
    assert system_prompt == "<instructions>\n你是专门做研究的助手。\n</instructions>"

    # PatchToolCallsMiddleware is registered first, so index 0 is not the
    # delegation middleware. Look it up by its registered middleware_name.
    assert middleware, "middleware list should not be empty"
    delegation = next(
        (mw for mw in middleware if getattr(mw, "name", "") == "SubagentDelegationMiddleware"),
        None,
    )
    assert delegation is not None, "SubagentDelegationMiddleware was not registered"
    assert delegation._text == SUBAGENT_DELEGATION_PROMPT
    assert delegation._prepend is True


def test_build_agent_injects_task_system_prompt_middleware_when_subagents_configured(monkeypatch):
    """主 agent (_depth=0) 且有子 agent 时，middleware 应包含 TaskSystemPromptMiddleware。"""
    from lc_agent.core.engine import TASK_SYSTEM_PROMPT

    engine = AgentEngine(MINIMAL_CONFIG)
    child = AgentPreset(
        id="worker",
        name="worker",
        system_prompt="研究助手",
        default_model="test-model",
        can_be_subagent=True,
    )
    parent = AgentPreset(
        id="orchestrator",
        name="orchestrator",
        system_prompt="协调工作",
        default_model="test-model",
        subagents=[SubAgentLink(agent_id="worker", delegation_description="深入研究时使用")],
    )
    engine._presets = {child.id: child, parent.id: parent}

    captured = {}

    monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
    monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)

    engine.build_agent(parent, cache_key="orchestrator", _depth=0)

    middleware = captured.get("middleware", [])
    mw_names = [getattr(m, "name", type(m).__name__) for m in middleware]

    assert "TaskSystemPromptMiddleware" in mw_names

    task_mw = next(m for m in middleware if getattr(m, "name", None) == "TaskSystemPromptMiddleware")
    assert TASK_SYSTEM_PROMPT in getattr(task_mw, "_text", "")

    # TaskSystemPromptMiddleware 应在 TodoListMiddleware 之前
    if "TodoListMiddleware" in mw_names:
        assert mw_names.index("TaskSystemPromptMiddleware") < mw_names.index("TodoListMiddleware")


def test_build_agent_no_task_middleware_when_no_subagents(monkeypatch):
    """没有子 agent 时不注入 TaskSystemPromptMiddleware。"""
    engine = AgentEngine(MINIMAL_CONFIG)
    standalone = AgentPreset(
        id="standalone",
        name="standalone",
        system_prompt="单独运行",
        default_model="test-model",
    )
    engine._presets = {standalone.id: standalone}

    captured = {}
    monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
    monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)
    engine.build_agent(standalone, cache_key="standalone", _depth=0)

    middleware = captured.get("middleware", [])
    mw_names = [getattr(m, "name", type(m).__name__) for m in middleware]
    assert "TaskSystemPromptMiddleware" not in mw_names


def test_build_agent_includes_ask_user_middleware_at_depth_0(monkeypatch):
    """顶层 agent (_depth=0) 应注入 AskUserMiddleware。"""
    engine = AgentEngine(MINIMAL_CONFIG)
    preset = AgentPreset(
        id="top-agent",
        name="top-agent",
        system_prompt="顶层助手",
        default_model="test-model",
    )
    engine._presets = {preset.id: preset}

    captured = {}
    monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
    monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)
    engine.build_agent(preset, cache_key="top-agent", _depth=0)

    middleware = captured.get("middleware", [])
    mw_names = [getattr(m, "name", type(m).__name__) for m in middleware]
    assert "AskUserMiddleware" in mw_names


def test_build_agent_excludes_ask_user_middleware_at_depth_gt_0(monkeypatch):
    """子 agent (_depth>0) 不应注入 AskUserMiddleware，防止前端无法响应的死锁。"""
    engine = AgentEngine(MINIMAL_CONFIG)
    child = AgentPreset(
        id="worker",
        name="worker",
        system_prompt="子任务执行者",
        default_model="test-model",
    )
    engine._presets = {child.id: child}

    captured = {}
    monkeypatch.setattr(engine, "_create_llm", lambda model_info, model_id, llm_params=None: object())
    monkeypatch.setattr(engine, "_build_summarization_middleware", lambda preset: [])

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr("lc_agent.core.engine.create_agent", fake_create_agent)
    engine.build_agent(child, cache_key="worker", _depth=1)

    middleware = captured.get("middleware", [])
    mw_names = [getattr(m, "name", type(m).__name__) for m in middleware]
    assert "AskUserMiddleware" not in mw_names
