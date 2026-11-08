# 跨平台测试与CI机制修正

日期：2026-11-08。依据维护者“继续推进、Windows随时可复验”的指示，处理
[原件复核](2026-11-08_windows-validation-evidence-review.md)已确认的四组测试/验证机制问题。
基准交接HEAD为`3f402b42797694d752c6cde7452980f0febbf14c`；产品候选为`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`。

## 修正与依据

- 测试自建SQLite连接采用`closing(connection)`管理生命周期，同时保留连接自身的事务上下文，
  确保成功提交、失败回滚、最终关闭分别成立。修改12处，没有吞清理错误或增加GC/删除重试。
  依据为[Python3.12连接上下文说明](https://docs.python.org/3.12/library/sqlite3.html#how-to-use-the-connection-context-manager)。
- uv夹具从当前实际工具和`venv.EnvBuilder`上下文、子解释器`sysconfig`取得二进制/解释器/site-packages，
  验证真实上游解析到的非邻接执行体及摘要，不再依赖维护者`.venv/bin/uv`或固定Python目录。
  版本期望从现有pin入口读取，无新增工具pin副本。
- 本机文件系统路径按Path语义比较；BagIt文本/交付成员保持POSIX规范表示。
  外部路径必须被稳定的`integrity`错误拒绝，不再用另一平台分支的文案判失败；产品catch保持原样。
- 公用测试夹具在Windows通过原生junction创建目录重定向，使用
  [New-Item](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item?view=powershell-5.1)
  的literal Path语义；固定EncodedCommand，路径仅从环境数据读入，不拼接为脚本。
  清理只移除链接，不跟随目标或删除替换后的普通目录。
- 正式owner测试覆盖home外sentinel的四个位置、ordinary/repair、任务事实不变；
  cheap next不扫描payload，payload重定向仍应先提示verify_delivery，再由完整deliver拒绝，未扩大cheap probe成本。
- POSIX模式/DAC性质拆为明确的平台用例，原断言保留；Windows仍执行共同安全行为、原生junction与拒绝遍历信号测试。
  文件symlink仅在真实WinError1314时登记能力skip，其他失败继续抛出；混合用例拆开，通用备份/缺失内容测试不受skip影响。
  这不是Windows ACL认证，也没有放宽产品权限承诺。

## 实际验证与复核

本机完整检查255运行（默认1真实模型skip）＋42开发通过；两名独立验证者按review技能分别检查Standards/Spec，
各0项open。规范验证另运行事务/关闭、原生夹具代码与Linuxowner边界探针；原生Windows结果尚不能由此推定。
干净checkout用已准备解释器重现旧uv测试缺本地venv的红色信号，修正测试在相同夹具转绿。
第一组100项定向测试曾暴露新增payload next断言与cheap probe契约不符，已修正测试而非修改产品；原始失败保留。

产品runtime、协议、依赖锁与版本保持字节不变；没有新增兼容层或后台机制。
`dev/smoke_task.py`新增外部cwd/launcher和逐CLI原始字节追踪，doctor不得创建不存在的home。
交接收集器统一运行canonical、原生smoke与三制品新环境任务；即使失败也保留参数、cwd、时间、退出码、
原始输出及程序，生成清单和ZIP；显式sender仅向授权PR发送校验过的ZIP分片。
旧制品保留于原Git提交，新候选将从Git归档重建三件并重新钉住身份，开发版本号不代表已发布旧附件。
证据在维护者忽略目录`.evaluation/platform-test-repair/20261108/`，含红/绿复现、完整检查、两个独立报告及官方文档快照。

## GitHub和Windows接续

本修正正常通过hooks后固化，再以新的测试/检查候选更新交接身份及可重复收集入口。
Windows端从固定提交统一复验；现有CI两平台均须实际复跑，不能将本机通过改写为原CI已绿。
旧交接、旧包和旧报告保留原身份。原件取证和修正记录随本轮提交，补录不覆盖原回交。
冷下载/中断、跨进程缓存锁、真实宿主和完整安装矩阵仍独立登记；不因测试修正自动闭合。
本次授权不包含主分支合并、tag、发布或四条用户Issue变更，也不修改兄弟仓。
