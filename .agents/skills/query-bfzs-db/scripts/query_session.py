"""Query bfzs session data (messages, tools, presets) from SQLite databases.

Usage:
  python query_session.py <session_id>              # Show messages for a session
  python query_session.py --presets                 # List all agent presets
  python query_session.py --sessions [--limit N]    # List recent sessions
  python query_session.py --tools <session_id>      # Show tool calls in session
  python query_session.py --state                   # Show runtime MCP/tool state
"""
import argparse
import asyncio
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

BFZS_DIR = Path(r"D:\codes\lc-agent-bfzs")
DATA_DB = BFZS_DIR / "bfzs_data.db"
CHECKPOINT_DB = BFZS_DIR / "bfzs_checkpoints.db"
API_BASE = "http://127.0.0.1:8001/api"


def get_conn(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)
    return sqlite3.connect(str(db_path))


def list_presets():
    conn = get_conn(DATA_DB)
    c = conn.cursor()
    c.execute("SELECT id, name, allowed_tool_groups, allowed_mcp_servers FROM agent_presets")
    print(f"{'ID':<40} {'Name':<25} {'Tools':<20} {'MCP'}")
    print("-" * 110)
    for row in c.fetchall():
        tools = json.loads(row[2]) if row[2] else None
        mcp = json.loads(row[3]) if row[3] else None
        print(f"{row[0]:<40} {row[1]:<25} {str(tools):<20} {mcp}")
    conn.close()


def list_sessions(limit: int = 10):
    conn = get_conn(DATA_DB)
    c = conn.cursor()
    c.execute(
        "SELECT id, title, agent_id, message_count, created_at FROM sessions ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    print(f"{'ID':<38} {'Title':<30} {'Agent':<15} {'Msgs':<5} {'Created'}")
    print("-" * 120)
    for row in c.fetchall():
        print(f"{row[0]:<38} {row[1]:<30} {row[2]:<15} {row[3]:<5} {row[4]}")
    conn.close()


def query_messages(session_id: str):
    """Load messages using LangGraph's native checkpoint API."""
    async def _load():
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        conn = await aiosqlite.connect(str(CHECKPOINT_DB))
        saver = AsyncSqliteSaver(conn)

        config = {"configurable": {"thread_id": session_id}}
        checkpoint_tuple = await saver.aget_tuple(config)

        if not checkpoint_tuple:
            print(f"No checkpoint for session: {session_id}")
            await conn.close()
            return

        checkpoint = checkpoint_tuple.checkpoint
        messages = checkpoint.get("channel_values", {}).get("messages", [])
        print(f"\n=== Messages ({len(messages)}) for {session_id} ===\n")

        for msg in messages:
            msg_type = getattr(msg, "type", "?")
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", [])
            kwargs = getattr(msg, "additional_kwargs", {})

            icon = {"human": "USER", "ai": "AI", "system": "SYS", "tool": "TOOL"}.get(msg_type, msg_type)
            print(f"[{icon}]")
            if content:
                print(f"  {str(content)[:800]}")
            if tool_calls:
                for tc in tool_calls:
                    name = tc.get("name", "?") if isinstance(tc, dict) else getattr(tc, "name", "?")
                    args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                    print(f"  TOOL_CALL: {name}")
                    print(f"    args: {json.dumps(args, ensure_ascii=False, default=str)[:200]}")
            if kwargs:
                print(f"  kwargs: {json.dumps(kwargs, ensure_ascii=False, default=str)[:300]}")
            print()

        await conn.close()

    asyncio.run(_load())


def query_tools_used(session_id: str):
    """Show tool calls made in a session."""
    async def _load():
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        conn = await aiosqlite.connect(str(CHECKPOINT_DB))
        saver = AsyncSqliteSaver(conn)

        config = {"configurable": {"thread_id": session_id}}
        checkpoint_tuple = await saver.aget_tuple(config)

        if not checkpoint_tuple:
            print(f"No checkpoint for session: {session_id}")
            await conn.close()
            return

        messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
        tool_calls = []
        tool_results = []

        for msg in messages:
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    name = tc.get("name", "?") if isinstance(tc, dict) else getattr(tc, "name", "?")
                    args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                    tool_calls.append({"name": name, "args": args})
            if getattr(msg, "type", "") == "tool":
                tool_results.append({"name": getattr(msg, "name", "?"), "content": str(getattr(msg, "content", ""))[:200]})

        if tool_calls:
            print(f"\n=== Tool Calls ({len(tool_calls)}) ===\n")
            for tc in tool_calls:
                print(f"  -> {tc['name']}")
                print(f"     args: {json.dumps(tc['args'], ensure_ascii=False, default=str)[:200]}")
        if tool_results:
            print(f"\n=== Tool Results ({len(tool_results)}) ===\n")
            for tr in tool_results:
                print(f"  <- {tr['name']}: {tr['content'][:150]}")
        if not tool_calls and not tool_results:
            print("No tool calls in this session")

        await conn.close()

    asyncio.run(_load())


def show_runtime_state():
    """Show current runtime state of MCP servers and tool groups via API."""
    try:
        resp = urllib.request.urlopen(f"{API_BASE}/mcp")
        mcp = json.loads(resp.read())
        print("=== MCP Servers ===")
        for s in mcp:
            status_icon = {"connected": "v", "error": "x", "disabled": "-", "disconnected": "?"}.get(s["status"], "?")
            print(f"  [{status_icon}] {s['name']}: enabled={s['enabled']}, status={s['status']}, tools={len(s['tools'])}")

        resp = urllib.request.urlopen(f"{API_BASE}/tools/groups")
        groups = json.loads(resp.read())
        print("\n=== Tool Groups ===")
        for g in groups:
            icon = "v" if g["enabled"] else "-"
            print(f"  [{icon}] {g['id']} ({g['description']}): {len(g['tools'])} tools")
    except Exception as e:
        print(f"ERROR connecting to API: {e}")
        print("Is the server running on http://127.0.0.1:8001?")


def main():
    parser = argparse.ArgumentParser(description="Query bfzs session data")
    parser.add_argument("session_id", nargs="?", help="Session/thread ID to query")
    parser.add_argument("--presets", action="store_true", help="List agent presets")
    parser.add_argument("--sessions", action="store_true", help="List recent sessions")
    parser.add_argument("--tools", action="store_true", help="Show tool calls for session")
    parser.add_argument("--state", action="store_true", help="Show runtime MCP/tool state")
    parser.add_argument("--limit", type=int, default=10, help="Limit for --sessions")
    args = parser.parse_args()

    if args.presets:
        list_presets()
    elif args.sessions:
        list_sessions(args.limit)
    elif args.state:
        show_runtime_state()
    elif args.session_id:
        if args.tools:
            query_tools_used(args.session_id)
        else:
            query_messages(args.session_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
