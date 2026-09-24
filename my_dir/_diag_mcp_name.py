"""临时诊断：拉取 docs-langchain 远程 MCP 当前真实工具名。用后删除。"""
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

TARGET = "mcp__docs-langchain__query_docs_filesystem_docs_by_lang_chain"


async def main():
    async with streamablehttp_client("https://docs.langchain.com/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            names = [t.name for t in result.tools]
            print("current tool count:", len(names))
            for n in names:
                mark = "  <== MATCH" if f"mcp__docs-langchain__{n}" == TARGET else ""
                print(" ", n, mark)
            print()
            print("whitelist entry still exists on server:",
                  "query_docs_filesystem_docs_by_lang_chain" in names)


asyncio.run(asyncio.wait_for(main(), timeout=60))
