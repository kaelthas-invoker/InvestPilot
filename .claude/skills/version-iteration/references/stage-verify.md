# Stage: Verify

## 目标

独立验证任何将被下游消费或交付用户的 Stage 产出、结论或证据包是否满足 acceptance criteria、项目约束和证据标准；纯验证记录按下述终止 Gate 规则收口。

## 进入条件

- 任一 Stage 产出、结论或证据包将被下游消费或交付用户；
- C0 或简单任务已经形成产出；
- 被验证对象在上次 PASS 后发生修改，需要重新验证；
- 需要对完成声明、风险或证据充分性做 Four Eyes 检查。

## 必做规范

- 验证者必须是不同于被验证对象 producer 的独立实例。
- Design Verify 默认使用 `plan-reviewer`。
- Diff/代码/配置验证默认使用 `code-reviewer`。
- API/UI/运行环境验证按对象使用 `api-tester`、`e2e-tester`、`sre`。
- 证据包可使用 `evidence-collector`；高影响完成声明可用 `reality-checker`。
- 必须按 acceptance criteria 检查真实结果，不接受“看起来完成”。
- 只验证当前实际版本；被验证对象发生任何修改后，原 PASS 立即失效并重新进入 Verify。
- 独立 Verify 未 PASS 时禁止 Advance / Complete。
- verifier Envelope 仅可记录被验证对象、检查范围、证据、`PASS/FAIL`、缺陷/风险和 Gate 建议；未新增或修改业务结论或交付物时，它是终止 Gate 记录，本身不再触发 Verify。
- 若 verifier 修改或新增业务结论、文件或其他交付物，这些新增或修改对象必须由另一个独立 verifier 验证。

## 输出标准

Verify 通过时必须提供：

- 被验证对象；
- 执行的命令、检查或审查范围；
- PASS/FAIL 结论；
- 缺陷、风险和 root-cause Stage；
- 下游建议：Advance、Refinement、Replan 或 Escalate。

## Gate 标准

PASS 必须来自独立 verifier 实例，且无未关闭风险、无用户接力、证据充分。发现实现缺陷回 Execute；发现方案缺陷回 Design；发现目标/验收缺陷回 Clarification。修复或改写完成后必须对新版本重新独立 Verify，原 PASS 不得复用。
