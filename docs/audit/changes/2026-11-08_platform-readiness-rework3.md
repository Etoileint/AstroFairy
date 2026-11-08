# 平台、准备状态与交付恢复第三次定向返工

日期：2026-11-08。基准：`c330e72b56bd3a3f5486054addc1b59e8990dae8` 加前两轮实施/返工后的未提交工作树。
状态：第二次返工独立复验剩余的 STD01 与 F1/F2/F3 四类 P2 已按机制边界修复并自检；未提交、未推送、
未发布、未关闭 Issue；再次独立复验与维护者接受尚未发生。

依据：[第二次返工独立复验](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck2-2026-11-08/README.md)
与[剩余机制边界定向返工](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck2-2026-11-08/rework.md)。
三次既有回交、两轮验收记录与全部旧证据保持原样；本记录只声明本轮返工与执行者自检。

## 逐项处置

| ID | 根因处理 | 回归 |
|---|---|---|
| STD01 | 不再按 Python 邻接路径猜 uv。对 `-I -m uv`，在同一隔离解释器内调用上游 `uv.find_uv_bin()` 取得实际执行体，再读取该文件摘要；update 在无法确认执行体或摘要时拒绝写入，check 拒绝缺失/非 64 位十六进制的 `tool.sha256` | `test_tool_executable_digest_is_the_upstream_target_binary`（真实 target 布局：模块与 bin 在 site-packages）、`test_check_rejects_a_missing_recorded_tool_digest`；原 `expanded-probe.py` 两布局摘要一致 |
| F1 / SPEC04 | 一个进度边界从已验 staging 覆盖安全检查、两次 rename、发布后复核、结果生成和锁释放；原生 OSError 与 FairyError 共用 `task`/`completed`/`published`/`quarantined`/`recovery`；释放失败不覆盖原错误，已发布结果不降级为无身份失败；清理自身失败不遮蔽 | `test_first_rename_native_oserror_keeps_delivery_progress`、`test_unlock_failure_after_publication_keeps_delivery_identity`、`test_unlock_failure_does_not_mask_the_delivery_error`；原 `boundary-probe.py` 三个交付场景 |
| F2 / T29 | Store 事务层统一 BEGIN、事务体原生 sqlite3.Error 与 COMMIT 的确定性：已知回滚 `committed=false`，无法确认 `committed="unknown"`，回滚再失败保留原始错误为 cause 并记录回滚结果；运行时只补 task/operation/seq，不恢复整段 `_precommit` | `test_real_authorizer_refusal_reports_rolled_back_certainty`（真实 SQLite authorizer）、`test_body_error_with_failed_rollback_preserves_original_cause`、`test_observed_statement_acknowledgment_loss_is_unknown`；原 `sqlite-probe.py` 三场景 |
| F3 / T29 | invoked 提交失败/未知回包保留 `call`、`operation`、`known_seq`、`attempted_seq`、`stage` 和 `inspect TASK --history` 调查动作；未知不等于已提交，也不授权重放；handler 未运行不声称效果 | `test_invocation_commit_unknown_keeps_call_and_investigation`、`test_invocation_rollback_reports_false_with_call_identity`；原 `boundary-probe.py` invoked 场景与库中 pending call 一致 |
| 保留项 | STD02–06、SPEC01–03、GAP01/T35 与原 REG02 未改其机制，回归继续通过 | 全量测试、`standards/probe.py`、`spec/probe.py`、`unsafe-walk`、`invoke-progress`、`late-observation`、`historical` |

## 已执行检查

- 完整 `dev/check.py` 退出 0：**249 项运行测试（默认跳过 1 项真实模型）＋ 42 项开发测试**；
  锁 core 10/search 41、消费者审计、vendored BagIt、原生任务冒烟、ruff/mypy、skill 与文档链接通过。
- 本轮新增 10 项回归（8 项运行＋2 项开发）；acceptance 的 `boundary-probe.py`、`sqlite-probe.py`、
  `expanded-probe.py` 均在当前候选上重跑并给出预期字段；旧探针（spec/standards）重新执行。
- 分发：由最终候选重建 wheel、sdist、skill ZIP 至新证据目录（不覆盖旧制品）；全新 venv 安装与
  `pip check`、`doctor`、最小任务交付通过；提取 skill ZIP 后 doctor 与最小任务通过。
- 真实缓存（非下载）：`assets prepare` 六文件 SHA-256、空库 `assets search --refresh`
  `projection.state=empty`、`doctor --verify-search` `verified` 且未创建 home。

## 限界

- 未执行原生 Windows x64、Linux x86_64 CI、macOS；CI 矩阵只是配置。
- 未执行真实冷模型下载/中断恢复或真实 E5 推理；只验证既有缓存字节。
- 未执行 junction/reparse 原生负例、跨进程缓存锁、完整 skills CLI 安装矩阵与真实 host 恢复交互。
- STD01 的 target 布局验证是 Linux/POSIX 真实 uv 包与二进制；不是原生 Windows 安装布局矩阵。
- 执行者自检不代替再次独立复验、维护者接受、提交或发布；四条 Issue 保持开放。

## 证据

本轮证据根：`.evaluation/issue-repair-implementation/rework3-2026-11-08/`（本机忽略目录，普通 clone
不含；转交须附清单与 SHA256）。制品在 `artifacts/`，命令日志在 `logs/`，探针与结果在 `selfcheck/`，
分发安装与真实缓存工作目录在 `dist-check/` 与准备 home。前三次回交与两轮验收目录未改写。
