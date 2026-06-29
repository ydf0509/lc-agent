
# 1 当前项目，请使用python3.12运行

解释器在 `D:\ProgramData\Miniconda3\envs\py312\python.exe`


# 2 项目开发阶段

目前还是已非常早期开发阶段，没人使用，数据和代码中不要写兼容性迁移，没有任何历史包袱。

# 3.AI 写langchain 家族框架代码时候的规则

## 3.1 写 langchain / langgraph / deepagents 代码时，禁止使用ai预训练的过时的语法写法。
  要使用最新的框架语法。 写代码时候要用 `docs-langchain` 和 `reference-langchain` 这个两个langchain官方文档的mcp工具查询框架最新用法。


## 3.2 如果有必要，要用 nb_rag mcp查询 langchain / langgraph / deepagents  用法
  如果官方的文档，不够用，ai要调用 `nbrag` mcp的一些列工具来查询用法，要多次多轮深入调用nbrag的一系列工具，不要浅尝辄止，没检索足够足够的资料就开始回答。

  nbrag已向量化langchain相关源码和教程到知识库 `langchain_ai_codes_and_docs`

  langchain_ai_codes_and_docs 知识库包含如下文件件的内容
  ```python
  r'D:\codes\docs\src',
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_anthropic",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_classic",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_community",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_core",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_deepseek",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_google_genai",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_openai",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_protocol",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain_text_splitters",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langdetect",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langgraph",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langgraph_sdk",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langsmith",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\langchain",
       r"D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\deepagents",
  ```

## 3.3 ai可以从 `D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\` 目录下深入 langchain 相关的源码，包含函数入参和注释和用法。

ai可以从 `D:\ProgramData\miniconda3\envs\py312\Lib\site-packages\` 目录下深入 langchain 相关的源码，包含函数入参和注释和用法。


# 4 理解项目定位

lc-agent 是一个框架，是作为python包被导入使用。
`D:\codes\lc-agent-bfzs` 项目是基于lc-agent框架开发的演示项目。
`D:\codes\lc-agent-bfzs\bfzs\main.py` 是演示项目的入口文件。

lc-agent-bfzs的数据库是 `D:\codes\lc-agent-bfzs\bfzs_data.db` 和 `D:\codes\lc-agent-bfzs\bfzs_checkpoints.db` 。不是在lc-agent框架的默认目录`D:\codes\lc-agent\` 下。