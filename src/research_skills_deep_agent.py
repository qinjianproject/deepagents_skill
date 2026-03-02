import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from tools import search,fetch_url
from deepagents.backends import FilesystemBackend

from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from skill_middle import SkillsMiddleware
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
# === Logging ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === Load environment ===
load_dotenv()

# === Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL =  os.getenv("OPENAI_MODEL")
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", 25))


SYSTEM_PROMPT = """你是拥有多种技能的智能体，能够帮助用户完成各种任务。

## 工作流程
1. 理解用户需求。
2. 识别是否有合适的技能（Skill）可以满足需求。
3. **重要：在调用任何工具读取 Skill 的详细指令（SKILL.md）或执行 Skill 脚本之前，你必须先向用户描述你打算使用的技能名称及其作用，并询问用户“是否需要使用此技能继续？”。**
4. 只有在用户明确表示“同意”、“继续”或类似许可后，才允许读取该 Skill 的路径并执行后续操作。
5. 如果用户拒绝，请尝试直接使用通用工具或询问用户其他处理方式。

## 输出要求
- 使用中文输出

## 严格遵循
- 凡是生成与写入的文件，默认必须放在/fs/ 目录下
"""

logging.info("✅ 系统指令已加载")

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),  
        routes={
            # 显式指定 virtual_mode 消除警告
            "/fs/": FilesystemBackend(root_dir="./fs", virtual_mode=True),
            "/memories/": StoreBackend(runtime)
        }
    )

# === 创建模型实例 ===
model = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# === Skills 配置 ===
USER_SKILLS_DIR = Path.home() / ".deepagents" / "agent" / "skills"
USER_SKILLS_DIR = "./agent/skills"
WORKSPACE_ROOT = str(Path(__file__).parent.resolve())

skills_middleware = SkillsMiddleware(
    skills_dir=USER_SKILLS_DIR,
    assistant_id="agent",
    project_skills_dir=None,
)


logging.info(f"✅ Skills 中间件已配置")
logging.info(f"  - 用户 Skills 目录: {USER_SKILLS_DIR}")
logging.info(f"  - 项目 Skills 目录: {USER_SKILLS_DIR}")

# === 创建 DeepAgent（无后端，无子智能体）===
# 注意：在 langgraph dev 模式下，store 由平台自动提供，不需要手动传入

research_subagent = {
    "name": "search-agent",
    "description": "使用search工具进行信息检索与总结的智能体",
    "system_prompt": "你是web检索与研究智能体。",
    "tools": [search,fetch_url],
    "model":model 
}

agent = create_deep_agent(
    model=model,
    tools=[],
    # subagents=[research_subagent],
    backend=make_backend,
    middleware=[skills_middleware],
    system_prompt=SYSTEM_PROMPT,
    # debug=True,
    store=InMemoryStore(),
    checkpointer=checkpointer
).with_config({"recursion_limit": RECURSION_LIMIT})

logging.info(f"✅ 简单 DeepAgent 已创建")
logging.info(f"  - 模型: {OPENAI_MODEL}")
logging.info(f"  - 递归限制: {RECURSION_LIMIT}")





# === 优化后的交互式运行部分 ===
if __name__ == "__main__":
    import sys
    from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

    # 初始化 thread_id，确保对话连贯
    config = {
        "configurable": {"thread_id": "stock_analysis_001"},
        "recursion_limit": RECURSION_LIMIT
    }
    
    print("--- DeepAgent 交互模式已启动 (输入 'exit' 退出) ---")
    
    # 初始问题（如果命令行没传参数，就用默认的）
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "分析贵州茅台 600519"

    while True:
        if not user_input:
            user_input = input("\n[用户]: ")
        
        if user_input.lower() in ["exit", "quit", "退出"]:
            break

        try:
            # 这里的输入格式需要根据你的 create_deep_agent 接收参数调整
            # 关键：每次循环都调用 stream，由于有 checkpointer，它会记得之前的状态
            for chunk in agent.stream(
                {"messages": [HumanMessage(content=user_input)]}, 
                config=config, 
                stream_mode="values"
            ):
                if "messages" in chunk:
                    last_msg = chunk["messages"][-1]
                    
                    # 1. 打印 AI 回复
                    if isinstance(last_msg, AIMessage):
                        if last_msg.content:
                            print(f"\n[AI]: {last_msg.content}")
                        
                        # 如果 AI 输出了内容但没有调用工具，说明它可能在等你确认
                        # 我们跳出当前的 stream 循环，去等待用户 input()
                        if not last_msg.tool_calls:
                            continue

                        # 2. 打印工具调用请求
                        for tc in last_msg.tool_calls:
                            print(f"\n[工具调用]: {tc['name']}({tc['args']})")
                    
                    # 3. 打印工具返回（可选，用于调试）
                    elif isinstance(last_msg, ToolMessage):
                        print(f"✅ [工具返回] 内容长度: {len(str(last_msg.content))}")
            
            # 本轮对话结束，清空 user_input 以便下次循环进入 input()
            user_input = None

        except Exception as e:
            logging.error(f"运行出错: {str(e)}")
            user_input = None