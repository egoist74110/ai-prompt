# Customer version template (客户版)

Output language: Simplified Chinese. Keep the layout exactly; drop sections per the rules in `../SKILL.md`.

## Layout

```text
后台公告-版本更新

【版本更新】v<YYYY.MM.DD.N>   发布时间：<YYYY-MM-DD[ HH:mm]>

新增：

- <功能>：<客户现在可以做什么>。

优化：

- <改进>：<对客户变好了什么>。

修复：

- <问题>：<不再出现什么问题>。

需要您做的：<租户需要执行的操作>

影响页面：

- <一级菜单> > <二级菜单>[ > <页面/Tab>]
```

Placeholders for unknown values:

- Unknown release time: `待定`

## Reference example

```text
后台公告-版本更新

【版本更新】v2026.09.25.1   发布时间：2026-09-25

新增：

- 会员详情新增「游戏统计」Tab，支持在会员详情内查看当前会员的子游戏统计明细。
- 「投注统计」列表中的游戏平台名称支持点击跳转至「游戏统计」Tab，并自动带入会员账号、游戏平台、投注时间等条件查询。
- 现金记录新增 WG 电子额度转换类型，支持识别 WG 电子转入、转出及失败流水。

优化：

- 「游戏统计」Tab 支持查询、重置、导出当页；无数据时展示空态。
- 「游戏统计」Tab 内切换后保留上次查询条件与结果，关闭会员详情后重新打开恢复默认。
- 支付通道管理「前台提示信息」列宽优化，提升长内容展示效果。

影响页面：

- 会员管理 > 会员详情
- 会员详情 > 投注统计
- 会员详情 > 游戏统计
- 现金系统 > 现金记录
- 现金系统 > 支付设定 > 支付通道管理
```

Recipient metadata (not body text): `发送对象：全体租户` or `发送对象：指定租户（<租户列表>）`.
