# 分发出件、fresh 安装与全快照恢复交付记录

日期：2026-11-02。工作树基准：`aaa9d3d930b94b7a46d9e47e0a226557c6340b43`，未提交。
对象：[W07 实施进度](../../optimization/2026-11-implementation/README.md)。
本记录覆盖 W07 的独立可执行部分与平台缺口；原会话独立验收与最终接受仍未发生。

## 实现与影响

本轮构建 `dist/astrofairy-0.1.0a1-py3-none-any.whl`、sdist 与便携 `fairy.zip`；wheel 和 ZIP
都含协议 10、`_limits.py`、`_pagination.py`、加权检索与当前参考/技能主文。runtime/delivery/
search 三个锁、vendored BagIt wheel、模型 profile/API 快照、插件清单均登记路径、字节和 SHA256。

使用官方 `skills@1.7.4`（Node 22.23.2）对 Codex、Claude Code、Cursor、GitHub Copilot、
Gemini CLI 五个目标做项目级复制安装，每例从复制目录以 `python -I` 运行 doctor、建任务、
发布、检查、语义审查和完整交付，五例通过。独立新 venv 按三个锁安装后安装 wheel；从 `/tmp`
运行 doctor（核心/SQLite/BagIt/搜索均 ready）并完成一个 BagIt 交付。`fairy.zip` 解包后用
fresh venv 的 `python -I` 运行 doctor 通过。原生 `.claude-plugin` 仅做结构/路径核对。

`dev/verify_recovery.py` 建立 3 个任务（含两版报告快照、嵌套目录/多成员、候选验证任务）和
1 个 stable 资产；备份后恢复到全新 home，`audit_state` 的 tasks=3/events=30/blobs=11/assets=1
前后一致，三个任务重新交付字节与恢复前相同，资产仍 stable。

## 检查与限界

新 venv 从锁定 runtime/delivery/search 文件安装，无系统站点包；wheel 导入路径位于 venv
site-packages。安装器复制目录的五例均运行完成；这证明安装布局和脚本协议，不证明原生应用
的真实模型调用或更新行为。Windows/macOS 未执行；原生插件市场安装/更新未执行，均记录 unknown。

完整 `.venv/bin/python -B dev/check.py` 结果见实施进度记录。W08 返回准备未在此签名，保持
`product_accepted=false`、`independent_acceptance=pending_original_session`。

## 接续

W08 组装最终源码清单/ZIP、78/43/V01–V24 覆盖、运行/指标/发现、证据清单与回交报告；停止
源码改动并交由原会话独立验收。
