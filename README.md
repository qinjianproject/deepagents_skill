整体架构：
- agent：
  - 主agent：log_analysis_agent: 日志分析agent，控制整个工作流程
  - 子agent1: log_interpreter_subagent：日志解释subagent，负责日志的初步解释工作
  - 子agent2: vulnerability_analysis_subagent：漏洞分析subagent，负责从异常日志中挖掘出整体的研究员行为和潜在的漏洞


源码：
- skill_middle: skill中间件，用于实现skill功能
- src: 具体实现
    - log_analysis_agent.py: 整体流程
    - prompts.py: 保存三个agent的系统提示词
    - tools.py: 大模型工具
    - utils.py: 定义辅助函数，目前实现了格式化agent输出的功能
- .deepagents: 保存各个agent可以使用的skill



后续工作：
1. 各种skill.md的补全，summary和report需要规定输出的格式，summary不用保存文件
2. 补充各个tools的具体实现