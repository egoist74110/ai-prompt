---
name: figma
description: 读取 Figma 设计稿（节点结构、样式、图片）。从 Figma URL 解析 file_key + node_id，用 PAT 调 REST API 获取设计数据。命中设计稿链接、Figma、取设计参数等意图时使用。
---

# figma — Figma 设计稿读取

目标：用本机 PAT 直接调 Figma REST API 读取设计稿节点数据（结构、样式、色值、间距），不依赖 Figma MCP 或浏览器。

## 0. 先复用本机已验证状态

所有仓库内相对路径以 `router.md` 所在目录为根。

先看 `.local/runtime.json`：

- `credentials.figma_pat`

若已缓存且文件存在，**直接用，不要重新探测**。

只有以下情况才重新 discovery：

1. 本机从未跑过本 skill；
2. 缓存的文件路径不存在（文件被移动/删除）；
3. API 调用返回 401/403（token 失效）。

Discovery 跑通后把 locator 写回 `.local/runtime.json`。禁止把 PAT 明文写入缓存。

## 1. PAT 定位

### 已知来源（按优先级）

1. `.local/runtime.json` → `credentials.figma_pat`（type + path）
2. 常见路径探测（只读，不打印内容）：
   - `/mnt/.config/figma/token`
   - `~/.config/figma/token`
   - `~/.config/figma/pat`
3. 以上都不存在 → 问用户 PAT 文件路径，拿到后写回 runtime。

### 缓存格式

```json
{
  "figma_pat": {
    "type": "file",
    "path": "<machine-local-path>",
    "note": "Figma Personal Access Token，纯文本单行；读取后只用于 X-Figma-Token header，禁止打印明文"
  }
}
```

## 2. 从 Figma URL 解析参数

Figma URL 格式：
```
https://www.figma.com/design/<file_key>/<file_name>?node-id=<node_id>&...
https://www.figma.com/file/<file_key>/<file_name>?node-id=<node_id>&...
```

解析规则：
- `file_key`：URL path 第一段（`/design/` 或 `/file/` 后面）
- `node_id`：query 参数 `node-id`，格式如 `3071-2`，API 调用时 `-` 不变
- 无 `node-id` 时取整个文件（大，慎用）

## 3. API 调用

Base URL：`https://api.figma.com`
Auth header：`X-Figma-Token: <PAT>`

### 读指定节点（最常用）

```bash
curl -s -H "X-Figma-Token: <PAT>" \
  "https://api.figma.com/v1/files/<file_key>/nodes?ids=<node_id>&geometry=paths"
```

- `ids` 支持多个，逗号分隔：`ids=3071-2,3071-5`
- `geometry=paths` 返回矢量路径数据（可选，不需要图片渲染时去掉）
- 响应 JSON：`nodes["<node_id>"].document` 是节点树

### 读整个文件（慎用，大文件很慢）

```bash
curl -s -H "X-Figma-Token: <PAT>" \
  "https://api.figma.com/v1/files/<file_key>"
```

### 下载节点图片（PNG/SVG）

```bash
curl -s -X POST -H "X-Figma-Token: <PAT>" \
  -H "Content-Type: application/json" \
  -d '{"nodes":[{"id":"<node_id>","renderOptions":{"format":"png","scale":2}}],"format":"png"}' \
  "https://api.figma.com/v1/images/<file_key>"
```

响应：`{"images": {"<node_id>": "https://..."}}` — 返回图片 URL，再 curl 下载。

### 读文件元信息（验证 token）

```bash
curl -s -H "X-Figma-Token: <PAT>" "https://api.figma.com/v1/me"
```

注意：`/v1/me` 返回 403 **不能单独判 PAT 失效**；只有文件读权限的 token 也可能 403。以实际文件读取为准。

## 4. 节点树解读

`document` 字段是 Figma 节点树，关键属性：

| 字段 | 含义 |
|------|------|
| `type` | FRAME / TEXT / RECTANGLE / VECTOR / GROUP / COMPONENT 等 |
| `name` | 图层名 |
| `absoluteBoundingBox` | `{x, y, width, height}` 绝对坐标 |
| `fills` | 填充（`type: "SOLID"` → `color: {r,g,b,a}` 0-1 范围） |
| `strokes` | 描边 |
| `cornerRadius` / `rectangleCornerRadii` | 圆角 |
| `style` | TEXT 节点的 `fontSize`、`fontWeight`、`letterSpacing`、`lineHeightPx` |
| `characters` | TEXT 节点的文字内容 |
| `constraints` | 自动布局约束 |
| `layoutMode` | HORIZONTAL / VERTICAL / NONE（auto-layout） |
| `itemSpacing` | auto-layout 间距 |
| `paddingLeft/Right/Top/Bottom` | auto-layout padding |
| `children` | 子节点数组 |

### 颜色转换

Figma 颜色 `r/g/b` 是 0-1 浮点。转 hex：
```
hex = "#{Math.round(r*255).toString(16).padStart(2,'0')}..."
```

### 尺寸

Figma 设计稿尺寸就是 px（移动端 750 设计稿 → 项目用 postcss-pxtorem 自动转 rem，直接写设计稿 px 值即可）。

## 5. 使用流程

1. 从用户提供的 Figma URL 解析 `file_key` + `node_id`
2. 从缓存/探测获取 PAT（不打印）
3. `curl` 调 nodes API 获取节点树
4. 解析 JSON，提取需要的信息（布局、颜色、字号、间距、文案）
5. 将设计参数映射到代码实现
6. 如需视觉参考，调 images API 下载 PNG 截图

## 6. 注意事项

- PAT 是敏感信息：不打印、不写入 repo、不写入日志
- 大文件（>100 页）避免读整个 file，只读指定 node
- `geometry=paths` 会让响应大很多，只在需要矢量路径时加
- 图片下载 URL 有时效性（通常几小时），需要立即下载
- 设计稿中的 auto-layout 参数（`layoutMode`、`itemSpacing`、padding）直接对应 CSS flex 属性

## 7. 收尾

- 报告读取了哪些节点、提取了哪些设计参数
- 若首次探测出新的 PAT 路径且验证成功，确认已写回 `.local/runtime.json`
