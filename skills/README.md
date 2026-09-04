# Skills

`skills/<name>/SKILL.md` 是自定义 Skill 的唯一正典位置，frontmatter 是元数据唯一 source of truth；`capabilities/skills.md` 只是自动/轻量发现索引。

## 规则

- Skill 内部文件一律从**当前 Skill 目录**解析，不假定 cwd，也不假定 `$CODEX_HOME` / `$HOME/.claude` 等运行时私有路径。
- 跨机器成立的流程、命令形态、服务固有行为留在 Skill。
- Python/Node/Bash 路径、输出目录、数据库、MCP endpoint、已验证 strategy 等机器事实写 `.local/runtime.json` / `.local/state.json`。
- Secret 正文不进 `.local`；只允许缓存 credential locator。
- 第一次 discovery 跑通后应缓存，后续直接复用；缓存失效才重新探测。
- 运行时私有 skills 目录只是部署入口，不是第二份 source of truth。
