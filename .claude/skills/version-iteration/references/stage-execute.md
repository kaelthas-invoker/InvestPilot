# Stage: Execute

## 目标

按已通过的目标/方案完成实际交付物，并产生可独立验证的证据。

## 进入条件

- C1 任务已具备明确目标和验收；
- C2+ Design 已通过 Verify；
- 当前节点依赖已满足，写入边界清楚。

## 必做规范

- 只做当前节点范围，不借机重构或预建未来能力。
- 遵循仓库 `CLAUDE.md` 的业务分层：`interface`、`assistant`、`research`、`providers`、`core`。
- 使用现有项目工具：`uv`、`fin-agent`、`pytest`、`ruff`。
- 模型/provider 访问保持小边界；不要把供应商细节扩散到业务层。
- 投资输出保持研究辅助定位；不得添加交易执行。
- 文件编辑后记录实际 diff、命令和结果。

## 输出标准

Execute 通过时必须提供：

- 实际修改的文件；
- 基础检查结果；
- 与 acceptance criteria 对应的运行或测试证据；
- 未关闭风险或接力。

## Gate 标准

每个 Execute 产出都必须由不同实例的独立 verifier 对最新版本给出 PASS；C0 和简单任务也不得跳过。实现缺陷在当前 Stage Refinement。发现方案错误 Replan 到 Design；发现目标或验收错误 Replan 到 Clarification。没有真实证据或独立 Verify 未 PASS 时不得 Advance / Complete。
