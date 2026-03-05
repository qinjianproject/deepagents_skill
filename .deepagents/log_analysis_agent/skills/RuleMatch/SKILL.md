---
name: RuleMatch
description: 匹配内部安全策略规则，确认该日志是否触发已知违规或者相似的威胁。
---

# RuleMatch Skill

功能

## When to Use This Skill

什么时候用

## Research Process

根据收集到的规则，使用以下策略判断是否可疑：

**高可疑性（High Suspicion）**:
- BUNDLE_NAME包含"example"或"test"（如com.example.shell）
- APP_DISTRIBUTION_TYPE为"none"
- USERID为2000（shell权限）
- INSTALL_TYPE为"normalInstall"但来自系统应用
- CALLING_UID不为0但CALLING_BUNDLE_NAME为空（可能隐藏调用者）
- FINGERPRINT为空或使用默认值
- 多个连续的安装/更新操作在短时间内发生

**中等可疑性（Medium Suspicion）**:
- BUNDLE_NAME使用不常见的域名（非com.huawei, com.ohos）
- APP_DISTRIBUTION_TYPE为空
- HIDE_DESKTOP_ICON为1（隐藏图标）
- INSTALL_TIME与happentime有显著差异

**低可疑性（Low Suspicion）**:
- 系统应用（com.huawei.*或com.ohos.*）的正常安装/更新
- APP_DISTRIBUTION_TYPE为"os_integration"或"app_gallery"
- USERID为100（普通用户）

#### c) 上下文分析
- 检查是否有连续的相似事件（可能表示自动化脚本）
- 分析时间序列模式（如特定时间的集中操作）
- 检查是否有异常的调用链（如普通应用调用系统级安装）

### 2. 研究目标推测
基于可疑行为，推测安全研究员可能的研究目标：

- **权限提升**: 寻找方法获得更高权限（如从普通用户到shell）
- **系统组件漏洞**: 研究系统应用或框架的潜在漏洞
- **安全机制绕过**: 尝试绕过安全检查或权限控制
- **隐蔽持久化**: 测试隐藏应用或创建持久化后门的方法
- **信息泄露**: 尝试提取敏感信息或系统状态

## Available Tools

可用工具

## Subagent Configuration

子agent的配置

## Best Practices

一些限制
