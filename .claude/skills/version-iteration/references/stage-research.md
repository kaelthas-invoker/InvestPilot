# Stage: Research

## 目标

用可追溯证据补齐下游设计或实现需要的事实。

## 进入条件

- 代码结构、调用链、依赖、测试方式或现有行为不明；
- 需要确认项目文档、命令、数据格式、外部 API 或投资研究口径；
- 多个方案依赖事实判断，而不是偏好判断。

## 必做规范

- 优先读取仓库事实：`CLAUDE.md`、`README.md`、`pyproject.toml`、相关源码、测试和现有 docs。
- 代码检索优先用 `rg` / `rg --files`。
- 投资、市场、价格、法规、模型文档等可能变化的信息必须查证实时来源。
- 明确区分事实、推断和未知项。
- 不在 Research 中改文件；只产出证据和结论。

## 输出标准

Research 通过时必须提供：

- 已查证事实和证据位置；
- 与当前任务相关的影响面；
- 仍未知但不阻塞的事项；
- 推荐进入 Design、Execute 或 Escalate 的依据。

## Gate 标准

Research 的事实、结论和证据包必须由不同实例的独立 verifier 对最新版本给出 PASS，且证据足以支撑下游 Stage。证据不足、事实冲突、独立 Verify 未 PASS 或外部授权缺失时不得 Advance；根因属于目标/范围时 Replan 到 Clarification。
