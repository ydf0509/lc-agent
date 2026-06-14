# Query bfzs Database

Query session messages, agent presets, and tool usage from the bfzs application databases.

## Usage

```bash
# Set interpreter
$Python = "D:\ProgramData\miniconda3\envs\py312\python.exe"
$Script = "D:\codes\lc-agent\.agents\skills\query-bfzs-db\scripts\query_session.py"

# List recent sessions
& $Python $Script --sessions

# List agent presets (with tool/mcp filters)
& $Python $Script --presets

# Query messages for a specific session
& $Python $Script "session-uuid-here"

# Show tool calls in a session
& $Python $Script --tools "session-uuid-here"
```

## Database Locations

- **Data DB**: `D:\codes\lc-agent-bfzs\bfzs_data.db` (sessions, agent_presets)
- **Checkpoint DB**: `D:\codes\lc-agent-bfzs\bfzs_checkpoints.db` (LangGraph state with messages)

## When to Use

- Debugging what tools/presets are actually being used
- Verifying message content without manual browser testing
- Checking if the correct `preset_id` was applied to a session
