# Windows原生验证移交准备

日期：2026-11-08。维护者提供Windows开发机信息并询问下一步；本次完成固定候选与任务包准备，未在Windows执行。
后续目标来自[原计划剩余验证](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/remaining-validation.md)，
本轮代码技术结论仍见[第三次独立复验](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/README.md)。

## 移交对象

- Git基准为`c330e72b56bd3a3f5486054addc1b59e8990dae8`，整改仍未提交。
  直接从GitHub克隆当前主分支不能取得本候选，所以同时提供Git bundle与完整未提交源码快照。
- 原接受源清单SHA256为`0a2038eb32494ad75164a00a43eb5dba9529f225d12778d5e4060afc812c2166`。
  转交快照371件现存＋4件删除；相对原接受候选只含验收/导航Markdown更新，产品字节未变。
- 同时包含接受候选的wheel、sdist、skill ZIP原件、逐文件清单、Windows任务单和标准库恢复器。
  不包含虚拟环境、模型权重、业务数据、Git配置或凭证；恢复器只创建新验证checkout并保留必要Git历史。

包位于维护者本机忽略目录`.evaluation/windows-validation-kit/20261108/`，普通clone不含：

- `AstroFairy-Windows-validation-20261108.zip`：5,033,475字节。
- SHA256：`c720a021756e12365f26674ee571092f50c7e7417ba039100982245480e0535f`；相邻`.zip.sha256`记录相同值。
- 包内`WINDOWS-VALIDATION.md`给出原生安装、BagIt全链、junction/reparse、恢复、三制品安装与宿主试验任务，
  并列明源码/制品身份、实际命令、退出码、原始日志、覆盖状态和回交哈希要求。
- 已指出当前测试中的POSIX路径/权限夹具；完整检查仍须执行，夹具、环境、产品失败分别登记，不能改skip伪报通过。

该包未公开上传。需要转交时由维护者使用认可的文件通道复制完整包及摘要给Windows执行者；本机路径不是公共下载地址。
包中源码冻结在移交准备时点，不包含此后新增的本篇登记；产品候选身份不受影响。

## 本机验证与限界

Linux aarch64上离线恢复演练通过：371件源码与4件删除逐字节/状态匹配，Git历史可读取，文档结构检查通过；
目标目录已存在时拒绝，防止覆盖现有checkout。读取最终ZIP再次核对10件成员及内部清单全部一致。
原接受目录97件封存证据仍匹配。原始日志、`preparation-checks.json`、`package.json`保存在包的同级目录。

这证明本机上的移交包/恢复流程，不是Windows运行、安装、路径或宿主验证。Windows待执行状态没有改绿。
优先完成无需模型权重的原生安装与交付，再单列大模型下载/中断和缓存并发，避免一次绑定全部长任务。
Windows结果不能代替Linux x86_64 CI或其他未执行格；若暴露新根因，回交原会话定界修复。

本次不改产品，未改兄弟仓、既有验收或发布制品；未提交、推送、发布或执行Issue外部动作。
