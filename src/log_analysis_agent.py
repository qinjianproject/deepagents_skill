import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from deepagents.backends import FilesystemBackend
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from skill_middle import SkillsMiddleware
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from prompts import *
from tools import *
from utils import format_message
import time

timestamp_str = str(int(time.time()))
checkpointer = MemorySaver()
# === Logging ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === Load environment ===
load_dotenv()

# === Config ===
MAX_CLUE_GET = os.getenv("MAX_CLUE_GET", 20)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL =  os.getenv("OPENAI_MODEL")
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", 25))
LOG_ANALYSIS_AGENT_SYSTEM_PROMPT = Log_Analysis_Agent_System_Prompt.format({"max_clue_get": MAX_CLUE_GET, "thread_id": timestamp_str})
LOG_INTERPRETER_SUBAGENT_SYSTEM_PROMPT = Log_Interpreter_Subagent_System_Prompt
VULNERABILITY_ANALYSIS_SUBAGENT_SYSTEM_PROMPT = Vulnerability_Analysis_Subagent_System_Prompt

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),  
        routes={
            # 显式指定 virtual_mode 消除警告
            f"/results/{timestamp_str}": FilesystemBackend(root_dir=f"./results/{timestamp_str}", virtual_mode=True),
            "/memories/clue/": StoreBackend(runtime)
        }
    )

model = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

logging.info("✅ 系统指令，后端，模型已加载")

# === Skills 配置 ===
USER_SKILLS_DIR = Path.home() / ".deepagents" / "agent" / "skills"
WORKSPACE_ROOT = str(Path(__file__).parent.resolve())
LOG_ANALYSIS_AGENT_SKILLS_DIR = f"{WORKSPACE_ROOT}/.deepagents/log_analysis_agent/skills"
LOG_INTERPRETER_SUBAGENT_SKILLS_DIR = f"{WORKSPACE_ROOT}/.deepagents/log_interpreter_subagent/skills"
VULNERABILITY_ANALYSIS_SUBAGENT_SKILLS_DIR = f"{WORKSPACE_ROOT}/.deepagents/vulnerability_analysis_subagent/skills"



log_analysis_agent_skills_middleware = SkillsMiddleware(
    skills_dir=USER_SKILLS_DIR,
    assistant_id="log_analysis_agent",
    project_skills_dir=LOG_ANALYSIS_AGENT_SKILLS_DIR,
)

log_interpreter_subagent_skill_middleware = SkillsMiddleware(
    skills_dir=USER_SKILLS_DIR,
    assistant_id="log_interpreter_subagent",
    project_skills_dir=LOG_INTERPRETER_SUBAGENT_SKILLS_DIR,
)

vulnerability_analysis_subagent_skill_middleware = SkillsMiddleware(
    skills_dir=USER_SKILLS_DIR,
    assistant_id="vulnerability_analysis_subagent",
    project_skills_dir=VULNERABILITY_ANALYSIS_SUBAGENT_SKILLS_DIR,
)


logging.info(f"✅ Skills 中间件已配置")
logging.info(f"  - 用户 Skills 目录: {USER_SKILLS_DIR}")
logging.info(f"  - 项目 Skills 目录: log_analysis_agent: {LOG_ANALYSIS_AGENT_SKILLS_DIR}; log_interpreter_subagent: {LOG_INTERPRETER_SUBAGENT_SKILLS_DIR}")



# === 创建 DeepAgent（无后端，无子智能体）===

log_interpreter_subagent = {
    "name": "log_interpreter_subagent",
    "description": "将原始结构化日志字段映射为自然语言描述，输出语义更加清晰的日志内容的智能体",
    "system_prompt": LOG_INTERPRETER_SUBAGENT_SYSTEM_PROMPT,
    "tools": [search,fetch_url],
    "middleware": [log_interpreter_subagent_skill_middleware],
    "model":model 
}


vulnerability_analysis_subagent = {
    "name": "vulnerability_analysis_subagent",
    "description": "分析这些筛选出的可疑日志，还原研究员的整体行为模式，判断其研究路径，并推理出可能存在的漏洞",
    "system_prompt": VULNERABILITY_ANALYSIS_SUBAGENT_SYSTEM_PROMPT,
    "tools": [search,fetch_url],
    "middleware": [vulnerability_analysis_subagent_skill_middleware],
    "model":model 
}

# 限定迭代次数
# log_analysis_agent = create_deep_agent(
#     model=model,
#     tools=[search,fetch_url],
#     subagents=[log_interpreter_subagent, vulnerability_analysis_subagent],
#     backend=make_backend,
#     middleware=[log_analysis_agent_skills_middleware],
#     system_prompt=LOG_ANALYSIS_AGENT_SYSTEM_PROMPT,
#     # debug=True,
#     store=InMemoryStore(),
#     checkpointer=checkpointer
# ).with_config({"recursion_limit": RECURSION_LIMIT})

# 不限定迭代次数
log_analysis_agent = create_deep_agent(
    model=model,
    tools=[search,fetch_url],
    subagents=[log_interpreter_subagent, vulnerability_analysis_subagent],
    backend=make_backend,
    middleware=[log_analysis_agent_skills_middleware],
    system_prompt=LOG_ANALYSIS_AGENT_SYSTEM_PROMPT,
    # debug=True,
    store=InMemoryStore(),
    checkpointer=checkpointer
)

logging.info(f"✅ log_analysis_agent 已创建")
logging.info(f"  - 模型: {OPENAI_MODEL}")
# logging.info(f"  - 递归限制: {RECURSION_LIMIT}")


# === 优化后的交互式运行部分 ===
if __name__ == "__main__":
    import sys
    from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

    # 初始化 thread_id，确保对话连贯
    config = {
        "configurable": {"thread_id": f"{timestamp_str}"},
        "recursion_limit": RECURSION_LIMIT
    }
    
    print("--- Log Analysis Agent 交互模式已启动 (输入 'exit' 退出) ---")
    
    user_input = None

    while True:
        if not user_input:
            user_input = input("\n[用户]: ")
        
        if user_input.lower() in ["exit", "quit", "退出"]:
            break

        # try:
        #     # 这里的输入格式需要根据你的 create_deep_agent 接收参数调整
        #     # 关键：每次循环都调用 stream，由于有 checkpointer，它会记得之前的状态
        #     for chunk in log_analysis_agent.stream(
        #         {"messages": [HumanMessage(content=user_input)]}, 
        #         config=config, 
        #         stream_mode="values"
        #     ):
        #         if "messages" in chunk:
        #             last_msg = chunk["messages"][-1]
                    
        #             # 1. 打印 AI 回复
        #             if isinstance(last_msg, AIMessage):
        #                 if last_msg.content:
        #                     print(f"\n[AI]: {last_msg.content}")
                        
        #                 # 如果 AI 输出了内容但没有调用工具，说明它可能在等你确认
        #                 # 我们跳出当前的 stream 循环，去等待用户 input()
        #                 if not last_msg.tool_calls:
        #                     continue

        #                 # 2. 打印工具调用请求
        #                 for tc in last_msg.tool_calls:
        #                     print(f"\n[工具调用]: {tc['name']}({tc['args']})")
                    
        #             # 3. 打印工具返回（可选，用于调试）
        #             elif isinstance(last_msg, ToolMessage):
        #                 print(f"✅ [工具返回] 内容长度: {len(str(last_msg.content))}")
            
        #     # 本轮对话结束，清空 user_input 以便下次循环进入 input()
        #     user_input = None

        # except Exception as e:
        #     logging.error(f"运行出错: {str(e)}")
        #     user_input = None

        try:
            # 记录当前已显示的最后一条消息的索引，避免重复打印
            last_shown_index = 0
            
            # 使用 stream 获取状态更新
            for chunk in log_analysis_agent.stream(
                {"messages": [HumanMessage(content=user_input)]}, 
                config=config, 
                stream_mode="values"
            ):
                if "messages" in chunk:
                    all_messages = chunk["messages"]
                    # 只获取本次 stream 产生的新消息
                    new_messages = all_messages[last_shown_index:]
                    
                    if new_messages:
                        # 使用 utils 中的格式化函数进行美化打印
                        format_message(new_messages)
                        # 更新索引
                        last_shown_index = len(all_messages)

            # 本轮流式输出结束，重置输入等待下一次循环
            user_input = None

        except Exception as e:
            logging.error(f"运行出错: {str(e)}")
            user_input = None