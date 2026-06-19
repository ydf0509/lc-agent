# Agent Hot Switch Bugs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix runtime correctness bugs around model, tools, MCP, skills, and agent editor selections so the next chat turn uses the current UI configuration.

**Architecture:** Agent configuration is persisted through the `/api/agents` routes, then `AgentEngine` builds and caches LangGraph agents by preset and model. Runtime tools/MCP/skills toggles must invalidate all affected cached agents. Editing an agent must invalidate all cache entries for that agent, including model override variants.

**Tech Stack:** Python 3.12, FastAPI, SQLModel/SQLAlchemy, LangChain/LangGraph, Vue 3, Pinia, Element Plus, pytest.

---

## Bugs Found

1. Skill runtime toggle does not invalidate cached agents.
   - Evidence: `/api/skills/{name}/toggle` updates `scanner._disabled_skills`, but unlike tool group and MCP toggles, it does not increment `engine._mcp_generation`.
   - Impact: If an agent has already been built, toggling a skill in the right panel may not affect the next message. The cached system prompt still contains the old skill list until another event rebuilds the agent.

2. Editing an agent does not invalidate model-specific cached agents.
   - Evidence: `/api/agents/{agent_id}` deletes only `engine._agents[agent_id]`.
   - Impact: If the user previously chatted with that agent under a selected model, the cache key is `agent_id::model::<model_id>`. Editing allowed tool groups, MCP servers, skills, dangerous tools, prompt, or default model can leave those model-specific cached agents stale.

3. Code-registered agent edits also do not invalidate cached graph variants.
   - Evidence: the code-agent update branch mutates `engine._custom_presets[agent_id]` and returns immediately without clearing `_agents`.
   - Impact: UI checkbox changes allowed for code agents can appear saved while cached runtime state remains stale for any cached generated variants.

## Root Cause

Agent cache invalidation is scattered across route handlers. Tool group and MCP routes update `_mcp_generation`, but skill toggles are missing the same invalidation signal. Agent update/delete routes clear only the exact agent key, not all derived cache keys created for model hot switching.

## Files

- Modify: `lc_agent/core/engine.py`
- Modify: `lc_agent/server/routes/agents.py`
- Modify: `lc_agent/server/routes/skills.py`
- Test: `tests/test_engine.py`
- Test: `tests/test_routes_agents.py`
- Test: `tests/test_skills.py`

## Task 1: Add Engine Cache Invalidation Helper

- [x] **Step 1: Write the failing test**

Add this test to `tests/test_engine.py` under `TestAgentEngine`:

```python
def test_invalidate_agent_cache_removes_model_variants(self, sample_config):
    from lc_agent.core.engine import AgentEngine

    engine = AgentEngine(sample_config)
    engine._agents["agent-a"] = object()
    engine._agents["agent-a::model::m1"] = object()
    engine._agents["agent-a::model::m2"] = object()
    engine._agents["agent-b"] = object()
    engine._agent_mcp_gen["agent-a"] = 0
    engine._agent_mcp_gen["agent-a::model::m1"] = 0
    engine._agent_mcp_gen["agent-b"] = 0

    engine.invalidate_agent_cache("agent-a")

    assert "agent-a" not in engine._agents
    assert "agent-a::model::m1" not in engine._agents
    assert "agent-a::model::m2" not in engine._agents
    assert "agent-b" in engine._agents
    assert "agent-a" not in engine._agent_mcp_gen
    assert "agent-a::model::m1" not in engine._agent_mcp_gen
    assert "agent-b" in engine._agent_mcp_gen
```

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py::TestAgentEngine::test_invalidate_agent_cache_removes_model_variants -q
```

Expected: FAIL with `AttributeError: 'AgentEngine' object has no attribute 'invalidate_agent_cache'`.

- [x] **Step 3: Write minimal implementation**

Add this method to `lc_agent/core/engine.py` near `_get_agent_cache_key`:

```python
    def invalidate_agent_cache(self, preset_id: str) -> None:
        """Remove cached agents for a preset, including model override variants."""
        prefix = f"{preset_id}::model::"
        keys = [
            key
            for key in self._agents
            if key == preset_id or key.startswith(prefix)
        ]
        for key in keys:
            self._agents.pop(key, None)
            self._agent_mcp_gen.pop(key, None)
```

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py::TestAgentEngine::test_invalidate_agent_cache_removes_model_variants -q
```

Expected: PASS.

## Task 2: Invalidate All Agent Cache Variants On Agent Update/Delete

- [x] **Step 1: Write failing route tests**

Add to `tests/test_routes_agents.py`:

```python
@pytest.mark.asyncio
async def test_update_agent_invalidates_model_variant_cache(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/agents", json={
            "name": "Cache Agent",
            "system_prompt": "Old prompt",
            "default_model": "gpt-4",
        })
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["id"]

        app.engine._agents[agent_id] = object()
        app.engine._agents[f"{agent_id}::model::gpt-4"] = object()
        app.engine._agent_mcp_gen[agent_id] = app.engine._mcp_generation
        app.engine._agent_mcp_gen[f"{agent_id}::model::gpt-4"] = app.engine._mcp_generation

        update_resp = await client.put(f"/api/agents/{agent_id}", json={
            "system_prompt": "New prompt",
        })

    assert update_resp.status_code == 200
    assert agent_id not in app.engine._agents
    assert f"{agent_id}::model::gpt-4" not in app.engine._agents
    assert agent_id not in app.engine._agent_mcp_gen
    assert f"{agent_id}::model::gpt-4" not in app.engine._agent_mcp_gen
```

Add this code-agent variant test to the same file:

```python
@pytest.mark.asyncio
async def test_update_code_agent_invalidates_model_variant_cache(app):
    graph = object()
    app.add_agent("code_agent_cache", graph)
    app.engine._agents["code_agent_cache::model::gpt-4"] = object()
    app.engine._agent_mcp_gen["code_agent_cache::model::gpt-4"] = app.engine._mcp_generation

    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/api/agents/code_agent_cache", json={
            "allowed_skills": [],
        })

    assert resp.status_code == 200
    assert "code_agent_cache::model::gpt-4" not in app.engine._agents
    assert "code_agent_cache::model::gpt-4" not in app.engine._agent_mcp_gen
    assert app.engine._agents["code_agent_cache"] is graph
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py::test_update_agent_invalidates_model_variant_cache tests/test_routes_agents.py::test_update_code_agent_invalidates_model_variant_cache -q
```

Expected: FAIL because model variant cache entries remain.

- [x] **Step 3: Write minimal route implementation**

Modify `lc_agent/server/routes/agents.py`:

```python
        engine._custom_presets[agent_id] = updated
        engine.invalidate_agent_cache(agent_id, keep_exact=agent_id in engine._agents)
        return {**updated.model_dump(), "source": "code"}
```

For user agent update:

```python
    engine.invalidate_agent_cache(agent_id)
```

For delete:

```python
    engine.invalidate_agent_cache(agent_id)
```

If the helper needs to preserve a pre-built code graph, extend it with `keep_exact: bool = False`.

- [x] **Step 4: Run tests to verify they pass**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_routes_agents.py::test_update_agent_invalidates_model_variant_cache tests/test_routes_agents.py::test_update_code_agent_invalidates_model_variant_cache -q
```

Expected: PASS.

## Task 3: Invalidate Runtime Cache On Skill Toggle

- [x] **Step 1: Write failing route test**

Add to `tests/test_skills.py`:

```python
@pytest.mark.asyncio
async def test_toggle_skill_increments_mcp_generation(app_with_skills):
    transport = ASGITransport(app=app_with_skills.fastapi_app)
    gen_before = app_with_skills.engine._mcp_generation

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/skills/test-skill/toggle")

    assert resp.status_code == 200
    assert app_with_skills.engine._mcp_generation == gen_before + 1
```

Use the actual fixture skill name from `tests/test_skills.py`; if it is not `test-skill`, replace it with the discovered name.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_skills.py::test_toggle_skill_increments_mcp_generation -q
```

Expected: FAIL because `_mcp_generation` is unchanged.

- [x] **Step 3: Write minimal route implementation**

Modify `lc_agent/server/routes/skills.py`:

```python
    engine = getattr(request.app.state, "engine", None)
    if engine:
        engine._mcp_generation += 1
    return {"name": name, "enabled": enabled}
```

- [x] **Step 4: Run test to verify it passes**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_skills.py::test_toggle_skill_increments_mcp_generation -q
```

Expected: PASS.

## Task 4: Verification

- [x] **Step 1: Run targeted backend tests**

Run:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe -m pytest tests/test_engine.py tests/test_routes_agents.py tests/test_routes_tools.py tests/test_skills.py -q
```

Expected: PASS.

- [x] **Step 2: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: build exits 0. Existing Rolldown annotation/chunk-size warnings may still appear.

- [x] **Step 3: Update this plan checklist**

Mark completed steps with `[x]` after verification.
