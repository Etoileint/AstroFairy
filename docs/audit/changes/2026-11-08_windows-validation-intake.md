# Windows回交初步查收与CI核验

日期：2026-11-08。结论：**已收到部分通过报告，尚未完成原件验收；两平台CI失败，不整体验收、合并或发布。**
本次只核对报告、GitHub原始CI及相关源码，不实施产品修复，不将报告自述直接登记为通过。

## 固定对象与到件状态

- [草稿PR #5](https://github.com/Etoileint/AstroFairy/pull/5)，交接HEAD为
  `3f402b42797694d752c6cde7452980f0febbf14c`，产品候选为`c9824b24b1627dd10de70fbcfe028a0dc9dfcfd5`。
- [Windows回交评论](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6725662114)报告安装、导入、
  BagIt、多处junction和三制品运行部分通过；完整检查不通过。源码/制品前后373件身份一致为执行者自述，原件待核。
- 执行者明确原ZIP尚未上传：87,226字节，声称SHA256为
  `e0b7a89f1ae3ce46b6bfd3a9c244133b653a0511a0f147545cd47f6622de93df`。
  `runs.json`、探针、结果、inventory等仍不可取得；给出摘要不等于已取得原件。
- 原会话已在[补件请求](https://github.com/Etoileint/AstroFairy/pull/5#issuecomment-6725855866)给出GitHub评论Base64分片方法，
  可用现有gh CLI传回完整ZIP，无需附件API或新服务。另要求补祖先/task junction的repair两例。
  原始报告/ZIP应保留；分类更正和补测另行回交。

## 已独立取得的CI事实

取证对象为[PR Check运行](https://github.com/Etoileint/AstroFairy/actions/runs/42503068268)，HEAD与上述交接一致。

| 原生通道 | 已观察结果 | 不能据此声称 |
|---|---|---|
| 托管ubuntu | core/delivery/search安装、editable安装、pip check成功；249运行测试通过（2skip）；42开发测试中uv夹具1error，整体失败 | 最小任务、构建与skill出件步骤因前置失败未运行；不是Linux通道全部通过 |
| 托管Windows | 同类安装和pip check成功；249运行测试，12failure/12error、2skip，整体失败 | 开发测试面及后续smoke/构建未在该CI继续执行，不能用开发机的单独运行冒充CI继续成功 |

开发机报告的249运行/42开发失败计数与托管runner不同，尚未核对其原始清单；不合并成唯一失败数。
CI两项skip分别为缺固定模型缓存的消费检查和显式启用的真实模型烟测，不冒充模型验证。

## 对失败分类的独立判断

1. **跨盘漏捕获的产品分类不成立于现有证据。** Windows CI完整trace显示`ntpath.relpath`的ValueError
   已由`_delivery._manifest_identity`转成`FairyError: BagIt manifest path is outside the bag root`，
   随后失败的是测试要求`foreign absolute`文案。源码已有捕获，原会话亦通过实际函数的纯路径分支佐证。
   该佐证不是本机Windows运行；原生CI原件是主要依据。不要据报告建议重复加catch或把cause误认作未处理异常。
2. **uv夹具确实依赖维护者目录。** 开发测试硬编码`.venv/bin/uv`、POSIX布局与解释器位置；
   托管Linux无项目内venv时直接FileNotFound。原会话在使用已准备解释器的干净clone中复现同一失败。
   后续应从实际解释器、上游uv与环境布局取得路径，不继续增加机器路径例外。
3. **数据库清理不能只归因环境。** 测试中找到12处直接`with sqlite3.connect(...)`；
   [Python3.12官方文档](https://docs.python.org/3.12/library/sqlite3.html#how-to-use-the-connection-context-manager)
   明确该上下文管理器不关闭连接。独立最小试验也确认with后仍可查询，显式close后才关闭。
   `_Archive`普通freeze路径捕获到的产品连接正常关闭；现有证据不能把这些测试连接的遗漏升级为产品普遍泄漏。
   后续需分清连接所有权与事务，确保commit/rollback和close各自成立，不能靠忽略WinError32或清理重试遮蔽。
4. **路径/权限能力断言需要原生语义。** CI中上游payload键、原生目标路径与POSIX固定字符串不符，
   多处POSIX mode断言及不可读树场景在Windows不等价。开发机缺symlink权限也不能用skip伪造安全验证；
   应明确能力条件并保留原生junction/权限反例。不要把Windows chmod位当作ACL证明，也不要全量跳过安全测试。

本轮没有独立确认报告所列的新增跨盘产品缺陷；这不证明所有产品路径均无缺陷。
当前有明确、可修复的测试/CI机制缺口和证据缺口，不能用边界无限这一理由忽略已红的检查。

## 接续与记录

先补原ZIP与两项repair，再核对每项探针的断言、源身份和原件摘要；T04/T13/T14/T32目前仅登记报告及CI已证子步骤，
不据自述闭合整项。T10/T11/T34、真实E5与完整skills CLI矩阵仍按原范围保留未执行。
原会话据原件收敛修正范围，以资源生命周期、路径表示、能力条件和环境发现为单位处理，不做逐条异常补丁。

本机原始取证在忽略目录`.evaluation/windows-acceptance/20261108/`：PR评论快照、CI元数据/全日志、
源码分类探针与结果、官方SQLite文档快照及摘要。它们不替代尚未取得的Windows开发机ZIP。
本次没有修改产品、锁、版本、旧验收或兄弟仓；没有合并、发布或改变四条用户Issue。
