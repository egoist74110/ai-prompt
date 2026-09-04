# Scanner / Scheduler / Agent 架构

适用于“定时扫描外部源 → 发现增量 → 处理 → 通知”的通用模式，不绑定 OpenClaw 或某个运行时。

## 架构

```text
Scheduler（cron / systemd timer / Windows Task Scheduler / runtime automation）
    ↓
Scanner（快速、只读）
    → 调外部 API
    → 读取本地 processed state
    → 计算增量
    → stdout 输出结构化 JSON
    ↓
Processor / Agent
    → 对新条目执行转录/摘要
    → 成功后写 processed state
    → 通知/交付
```

## Scanner

- 只负责发现，不做耗时转录。
- processed state 位置来自 `scripts/runtime_config.py`，最终落在 `.local/runtime.json` 指定的 `state_dir`。
- 使用数据源原生唯一 ID（B站用 bvid），避免标题改名造成重复。
- stdout 使用 JSON，调度器/Agent 不依赖某个运行时专属文本协议。

## Scheduler

调度方式属于部署环境事实：

- Linux/macOS 可用 cron/systemd/launchd；
- Windows 可用 Task Scheduler；
- 支持 automation 的 AI runtime 也可以直接定时调用脚本。

中央仓库不保存某台机器的定时任务绝对路径。创建任务时解析当前 `<skill_dir>` 和 Python locator；若该运行时支持自己的持久任务配置，由运行时管理。

## Processor / Agent

- 输入：Scanner JSON 或直接调用 `batch_transcribe.py`。
- 成功后才把 bvid 记入 processed state；失败项下次仍可重试。
- 输出：TXT/数据库/摘要/报告等。
- 机器路径全部来自 local runtime，不在 scheduler message 里硬编码某个 home。

## 关键原则

1. Scanner 必须快，只做网络读取 + 集合比较。
2. 增量状态用稳定唯一 ID。
3. 处理成功后才标 processed，避免失败被永久吞掉。
4. 无增量时调度器可静默，不启动高成本处理流程。
5. 暂时失败不把 state 永久标死；下轮或满足 retry condition 后重试。
6. scheduler/executable/path 第一次验证后缓存，后续直接复用，不每次重新找 Python/Skill 目录。
