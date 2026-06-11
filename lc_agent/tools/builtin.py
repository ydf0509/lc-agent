# lc_agent/tools/builtin.py
from datetime import datetime

from lc_agent.tools.registry import tool


@tool(group="builtin")
def get_current_time() -> str:
    """获取当前日期和时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
