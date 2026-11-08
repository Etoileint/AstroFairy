# GitHub Windows验证交接分支

日期：2026-11-08。维护者明确双方只能通过GitHub取得材料与通信，提出使用交接分支。
本次将当前已复验候选固化到独立分支，补充可直接克隆的任务、原制品与身份校验，替代此前仅本机可取的验证包。

## 对象和通道

- 分支：`handoff/windows-validation-20261108`；候选提交：`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`。
- 候选提交保留上轮独立复验已接受的产品字节与原有记录；此前未提交源清单的身份仍由
  [第三次复验](../../repairs/2026-11-platform-readiness-delivery/acceptance-recheck3-2026-11-08/README.md)记录。
- [交接任务](../../../handoff/windows-validation/README.md)、
  [分派数据](../../../handoff/windows-validation/assignment.json)与
  [候选Git blob清单](../../../handoff/windows-validation/candidate-manifest.json)钉住对象。
  校验脚本同时核对工作区源文件、原制品、候选祖先关系，拒绝重引旧删除项和未分派源码。
- 交接材料位于根`handoff/`，不进入当前wheel/sdist的包含规则；三种原制品按字节保留并由局部Git属性禁用文本转换。
- 本分支草稿PR作为验证回交窗口；Windows端可评论回交报告与原始证据，不要求先修改失败候选才能传回失败。
  本机hooks阻止提交时不得绕过，不能把测试失败隐藏为成功；没有附件/评论权限则明确通道缺口。

## 边界与验证

主分支保留原指向；交接分支不等于发布，未改版本、标签或已发布附件，不关闭或评论四条用户Issue。
Windows端只做验证和取证，产品修改、修复提交、合并及发布仍需后续明确任务。
推送将触发现有Check矩阵（Linux x86_64、托管Windows），结果以实际run为准，配置不代表通过。
开发机的原生junction/reparse、真实宿主与下载/进程锁验证仍单独登记，不能由托管runner代替全部证明。

候选提交通过正常pre-commit完整检查（249运行、默认1真实模型skip；42开发）并固化；
交接工具额外执行身份校验、Ruff、文档链接和制品摘要检查，交接提交同样须正常通过hooks。
原始运行日志保存在维护者忽略的`.evaluation/windows-validation-kit/20261108/`，旧验收97件证据未改。
本记录登记交接意图与候选身份；远程是否接收、PR号及CI状态以GitHub记录与实际交接回执为准。

本次未执行Windows开发机验证，不改写旧验收的未执行项，不修改兄弟仓或复制私有开发组织原文。
