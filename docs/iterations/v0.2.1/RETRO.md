# InvestPilot v0.2.1 RETRO — 柴犬 Logo 与加载动画

> 日期：2026-07-25

## 事实

- Task 1（logo 资产）与 Task 2（TUI 集成）按 PLAN 完成并分别提交。
- 验收阶段发现并修复两个缺口：
  1. TUI 启动即崩溃（`dfaf92a` 修复，并补 `test_tui_app.py` 应用级冒烟测试）。
  2. `test_anthropic_auth_token_accepted` 未隔离 `ANTHROPIC_BASE_URL`，在设置了该变量的开发机上失败；补 `monkeypatch.delenv` 修复。
- 收口时同步版本号 0.2.0 → 0.2.1（pyproject、`__init__.py`、`test_smoke.py`），`uv.lock` 已同步。
- 最终验证：`uv run pytest` 29 passed；`uv run ruff check .` 通过。

## 偏差与根因

| 偏差 | 根因 | 已应用改进 |
|------|------|-----------|
| 集成后 TUI 无法启动，PLAN 未预判 | Task 2 只跑了 helper 级测试，缺应用启动冒烟 | 新增 `test_tui_app.py`（run_test 启动 + 发送一轮）纳入回归 |
| 全量 pytest 在开发机红、CI 视角绿 | 测试依赖真实环境变量，非 hermetic | 约定：涉及 env 的测试一律 `monkeypatch.delenv` 相关变量（含 BASE_URL） |
| 版本号未随迭代推进 | SPEC 未列版本同步项 | 收口检查加入"版本号与迭代号一致" |

## 验收对照（SPEC §7）

1. 启动狗头：`on_mount` 挂载染色狗头，`test_tui_app.py` 验证 transcript ≥2 条 .msg —— 通过
2. 发送后跑狗：`_start_thinking` 显示状态行并启动 0.15s interval —— 通过（冒烟覆盖发送路径）
3. 流式开始停止：首个 text chunk 调 `_stop_thinking`，冒烟断言结束后无 active —— 通过
4. 报错停止：`finally` 中 `_stop_thinking` —— 通过
5. 多轮不受影响：全量测试通过 —— 通过
6. pytest / ruff + 资产单测：29 passed，ruff clean，`test_logo.py` 5 项 —— 通过

## 剩余风险

- 动画"出现瞬间"依赖肉眼/时序，自动化只覆盖最终停止态；真机观感（步长 1 列、0.15s）未调参，后续按实际体验再调。
- 终端宽度 < 24 列时狗头截断，按 SPEC 不缩放。
