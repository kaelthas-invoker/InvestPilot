---
name: version-iteration
description: 用于 InvestPilot 项目变更的流程控制 skill。根据需求清晰度、项目复杂度和任务复杂度，沿用并扩展 ~/.claude/CLAUDE.md 的 CC 分类、动态 Stage DAG、Gate、Envelope 和 Complete 规则；为每个 Stage 提供按需加载的 reference 规范。
---

# InvestPilot 版本迭代流程控制

## 定位

本 skill 只做流程编排，不替代全局 `~/.claude/CLAUDE.md`。

必须继承全局规则：

- 主 Agent 对目标理解、DAG 编排、Gate 判断、最终验收负责；
- 按 Clarification / Complexity 判定流程深度；
- 按 Stage DAG 推进，而不是固定线性流程；
- `Advance` 后若仍有下游 Stage / SubAgent 接力，不得结束任务；
- Complete 只能在当前有效 DAG 全部必要终端节点通过后成立。

## 启动流程

1. 分析任务清晰度。
2. 生成当前有效 Stage DAG；每个节点写清目标、输入、输出、Gate、producer、verifier。
3. 只加载当前 Stage 对应 reference；不要一次性加载全部 reference。

## 独立 Verify 硬规则

- 任何会被下游 Stage 消费或交付用户的 Stage 产出、结论和证据包，都必须先由独立 verifier 实例检查并取得 `PASS`；producer 与 verifier 不得是同一实例。
- C0、简单任务和纯文档/结论产出也不得绕过：最小 DAG 仍须为 `产出 -> Verify`。
- 独立 Verify 未完成或未 `PASS` 时，不得 `Advance`，也不得声明 `Complete` 或向用户交付该产出。
- Verify 后只要被验证对象发生任何修改，原 `PASS` 立即失效；必须对修改后的实际对象重新独立 Verify。
- 最终回复只能汇总已经独立 Verify `PASS` 的产出和结论，不得引入未经验证的新结论。仅记录被验证对象、检查范围、证据、`PASS/FAIL`、缺陷/风险和 Gate 建议，且不新增或修改业务结论或交付物的 verifier Envelope，是终止 Gate 记录，本身不再触发 Verify；若 verifier 修改或新增业务结论、文件或其他交付物，这些新增或修改对象必须交给另一个独立 verifier。

动态调整：

- 需求边界不清时先进入 `Clarification`。
- 架构拓展、架构调整时插入 `Research`，调研业界优秀设计和最佳实践案例，不要为了设计而设计，得出反模式的方案。
- 代码、数据、依赖或外部事实不明时插入 `Research`。
- 验证发现实现缺陷时回到 `Execute` Refinement。
- 验证发现方案缺陷时从 `Design` Replan。
- 验证发现目标/验收错误时根据 root-cause Replan，插入 `Clarification`。
- 当前版本可修问题不得写成“后续优化”直接收口。

## Stage References

| Stage | 何时读取 | Reference |
|---|---|---|
| Clarification | L1/L2 或 acceptance criteria 不完整 | [stage-clarification.md](references/stage-clarification.md) |
| Research | 需要代码、数据、依赖、市场/投资事实证据 | [stage-research.md](references/stage-research.md) |
| Design | C2+、跨文件、跨层、公共边界或风险变更 | [stage-design.md](references/stage-design.md) |
| Execute | 进入实际文件/配置/文档修改 | [stage-execute.md](references/stage-execute.md) |
| Verify | 任何 Stage 产出、结论或证据包进入下游或交付用户前 | [stage-verify.md](references/stage-verify.md) |
| Reflection | C4、重复返工、高影响偏差或用户要求复盘 | [stage-reflection.md](references/stage-reflection.md) |

## 文档产物

小任务可以只在最终回复报告 DAG、改动和验证结果。

中大型任务按需写入 `docs/iterations/<version>/`：

- `SPEC.md`：目标、范围、非目标、验收检查、开放问题；
- `PLAN.md`：Stage DAG、任务拆分、producer/verifier、验证路径、可勾选 Runbook Todo；
- `RETRO.md`：事实、偏差、根因、已应用改进、下一轮输入。

## 收口标准

交付用户前必须确认：

- 当前有效 DAG 的必要节点已通过 Gate；
- 所有将被下游消费或交付的产出、结论和证据包均由不同实例的独立 verifier 对其最新版本给出 `PASS`；
- 证据来自真实文件、命令、diff、日志、截图、数据样本或可信资料；
- 没有未关闭风险、用户接力或 SubAgent / Stage 接力；
- 已报告改动文件、验证命令和结果；
