# Stage: Design

## 目标

把已明确的目标和事实转成可执行、可验证、可回滚的 Stage DAG 或实现方案。

## 进入条件

- C2+ 任务；
- 跨文件、跨业务层、公共接口、模型 provider、数据边界或用户可见行为变更；
- 实现前需要拆解任务、定义 producer/verifier 或控制风险。

## 必做规范

- 读取 `~/.claude/.contract/runbook.md`。
- 保留已有目标和方案内容，不用 Runbook 替代设计。
- 方案必须说明范围、变更对象、执行顺序、验证路径、回滚/缓解方式。
- 对每个任务指定 producer 和独立 verifier；生产者和验证者必须是不同实例。
- 对 InvestPilot 保持 MVP 边界：先 TUI 聊天闭环，避免未来式基础设施。
- 涉及交易执行、凭据、敏感金融数据、发布、push 或 tag 时标明需要用户批准。

## 输出标准

Design 通过时必须提供：

- 当前有效 DAG；
- 每个节点的输入、输出、Gate；
- 文件/模块影响面；
- Runbook Todo：每项包含“做什么、目标、边界”；
- 验证计划。

## Gate 标准

所有 Design 产出均必须由不同实例的独立 verifier 对最新版本给出 PASS 后才能进入 Execute；C2+ 默认使用 `plan-reviewer`。缺少验收、验证路径、风险边界或 Runbook 时 Refinement。
