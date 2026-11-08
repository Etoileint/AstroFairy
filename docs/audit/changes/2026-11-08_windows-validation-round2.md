# Windows 第二轮统一复测交接

日期：2026-11-08。维护者明确要求继续，Windows机可随时执行。
在[跨平台测试修正](2026-11-08_cross-platform-test-repair.md)基础上固化源码候选
`6ced5c9a1a59d0f615c0f324564f48955c58fed1`，通过原分支及草稿PR #5接续。
旧主ZIP已完整取得；本轮不是要求重交87,226字节的旧包。

## 本轮身份

- 产品runtime仍等于`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`，锁/协议/版本未变。
- 候选清单从Git blob生成，范围为`handoff/`外376件，SHA256为
  `7671d958af0288c2a66be3c2005b637afa567644551762f656a46cf5932bad32`。
  跳过两件导航覆盖后，连同三制品共核377件，errors为空。
- 从候选Git归档重建wheel、sdist、skill ZIP。sdist365件已映射源码逐件相等且不含handoff载体；
  wheel25成员和ZIP33成员的内容字节等于上一轮（容器元数据导致整体摘要变化）。
  当前文件大小/摘要以[assignment](../../../handoff/windows-validation/assignment.json)为准。
- 旧交接和制品保留在`3f402b42797694d752c6cde7452980f0febbf14c`的Git历史；没有修改旧tag或发布附件。

## 收集与复核

[任务入口](../../../handoff/windows-validation/README.md)改为统一收集命令，逐项记录精确argv、cwd、起止时间、
exit及原始stdout/stderr。内部CLI以Base64保留原始字节，源和三制品在checkout外执行；
每种制品使用新venv及明确的安装/launcher来源，doctor不可创建不存在的任务home。
程序、环境、前后身份、runs、summary、逐件inventory及ZIP摘要一并封装。
失败结果不伪装通过；启动失败标launch_error/exit=-1，原始日志和已发分片保留。
新目录和独占ZIP写入避免覆盖旧证据；显式sender仅向授权PR #5发送校验过的包。

原测试修正和新增入口均按review技能分别做Standards/Spec独立复核，最终各0项open。
复核中发现的ZIP同stem覆盖、启动失败未记录、source cwd不明确均在本轮闭合。
负面身份试验实际拒绝验证并生成failed包；独立验者逐件核对清单/ZIP/sidecar一致。
发送器做模拟GH调用、原字节重组、摘要不符零发送、途中失败停发验证，未借探针对外发消息。
本机完整检查255运行（默认1skip）＋42开发及smoke通过；原生Windows结果仍待回交。

证据在本机忽略目录`.evaluation/platform-test-repair/20261108/`，包括两轴报告、启动失败探针、
负面封包、Git归档构建日志和制品内容比对；不假设普通clone具有维护者本机证据。
本轮推送后Linux/Windows CI须实际复跑；结果以对应GitHub run为准，旧红色CI不改写。

## 后续动作与限界

Windows机按任务入口取得最新明确任务HEAD，校验后运行collector，再向PR #5回交新包与简述。
新增正式junction用例统一覆盖home外四处重定向及ordinary/repair，补齐上轮手工脚本/目标范围缺口。
冷下载/中断、跨进程缓存、真实E5、完整skills CLI矩阵和真实宿主仍分开登记，不能被本轮脚本替代。
本轮仅写AstroFairy独立仓；不合并main、不打tag、不发布、不变更四条用户Issue。
