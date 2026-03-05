
---
name: Summary
description: 总结当前收集的日志线索，评估信息完备度，并指导后续调查方向。
---

# Summary skill 功能

总结当前收集的日志线索，评估信息完备度，并指导后续调查方向。

## 工作流程

1. 线索检索与对齐：从 /memories/clue/ 长期记忆中提取已记录的信息，与当前处理的日志流进行关联。
2. 单条日志剖析：针对每条日志，收集其行为特征判定所需线索（got_clues）。
3. 完备性校验：基于“最少线索确认原则”，评估当前信息是否足以形成闭环。
  - 若信息足以支撑结论，则 also_need_clues 置为空。
  - 若存在逻辑断层，则精准列出缺失的关键证据。


## 输出格式要求
输出必须严格遵循 JSON 数组格式，确保字段类型的准确性：
```json
[
  {
    "log_entry": {...  },
    "event_content": {...  },
    "got_clues": [... ],
    "also_need_clues": [... ]
  },
  ...
],

```

字段解释：
- log_entry: 该单条日志的一些基本信息，json格式
- event_content: 该单条原始日志中的event_content字段内容，json格式
- got_clues: 针对该单条日志收集到的各种线索，字符串列表格式
- also_need_clues: 还需要收集的线索。如果不需要收集线索了，值为空列表。

示例：
```json
[
  {
    "log_entry": {
      "entry_number": 1,
      "pt_d": "2025-12-29",
      "eventid": "818800801",
      "event_name": "HAP_UPDATE",
      "description": "hap应用升级",
      "bsn": "026CEM254F009587",
      "device_type": "CLS",
      "os_version": "OpenHarmony-5.0.5.165",
      "product_model": "CLS-AL30"
    },
    "event_content": {
      "APP_DISTRIBUTION_TYPE": "os_integration",
      "BUNDLE_NAME": "com.huawei.hmsapp.litegames",
      "CALLING_APPID": "",
      "CALLING_BUNDLE_NAME": "",
      "CALLING_UID": 0,
      "FINGERPRINT": "EE90E55652B9E4E8A221663C46A240F1A52B5379AB8E1FA6096BBEF52F4F2F5E",
      "HIDE_DESKTOP_ICON": 0,
      "INSTALL_TIME": 1766942225276,
      "INSTALL_TYPE": "PreBundleInstall",
      "USERID": 100,
      "VERSION": 150001300
    },
    "got_clues": [
      "xxx",
      "xxx",
      ...
    ],
    "also_need_clues": [
      "xxx",
      "xxx",
      ...
    ]
  },
  ...
]
```

## 关键约束
- 记忆同步：所有 got_clues 的读写必须与 /memories/clue/ 路径下的状态保持实时同步，确保分析的连贯性。
- 最少线索确认原则：禁止过度溯源。一旦现有线索足以判定事件性质或定位故障点，严禁在 also_need_clues 中添加非必要的探索性请求。
- 精准度要求：有关线索的内容描述需具体化（例如：使用“需核实调用方 UID 的权限”而非“需更多信息”）。