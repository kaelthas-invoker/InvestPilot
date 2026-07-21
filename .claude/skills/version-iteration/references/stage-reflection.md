# Stage: Reflection

## 目标

在高复杂度、重复返工或高影响偏差后，把证据转成当前流程可执行的改进。

## 进入条件

- C4 任务；
- 同一根因多次 Refinement / Replan；
- 验证或用户反馈显示目标、方案、实现或流程判断有偏差；
- 用户明确要求复盘。

## 必做规范

- Reflection 不替代当前版本仍可完成的修复。
- 先定位偏差属于 Clarification、Research、Design、Execute 还是 Verify。
- 当前可修问题必须 Replan 回 root-cause Stage。
- 只记录会改变下一次决策的经验，不写泛泛“以后注意”。
- 不恢复旧 learning ledger / checkpoint 机制，除非当前迭代有重复痛点和用户确认。

## 输出标准

Reflection 通过时必须提供：

- 发生了什么；
- 证据；
- 根因 Stage；
- 已应用到当前生命周期的改进；
- 下一轮输入或明确“无”。

## Gate 标准

Reflection 的结论、改进和证据包必须由不同实例的独立 verifier 对最新版本给出 PASS。若暴露当前完成结论不成立，必须 Replan，不得 Complete；只有偏差已关闭或转成明确下一轮输入且独立 Verify 已 PASS，才可进入下游或交付。
