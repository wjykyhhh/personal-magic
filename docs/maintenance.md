# 完整基础的维护、扩展和回退

## 保持完整一致

`upstream/blackmatrix7/rule/` 是上游完整 `rule/` 目录快照，包含全部客户端、分类、格式变体和 README。`scripts/library.py` 按 Git 对象格式计算整目录 tree SHA，并核对每个文件的 Git blob、大小、模式和文件集合；漏文件、多文件、改内容都会失败。

`sources.json` 的 `files` 仅选择当前接入配置所需的输入文件，不能用它缩小基础同步范围。新的类别和格式也必须被完整保存。`dist/base/` 保留当前选用的 17 个文件的兼容订阅入口；全库其他文件直接使用 `upstream/blackmatrix7/rule/` 的 Raw 地址。

## 添加扩展

修改自己的规则时使用 `custom/`，不要修改上游基础。当前这里是未启用草稿；后续扩展需有独立输出文件、明确策略与优先级，以及实际域名/请求的验证记录。修改 custom 不会改变现有基础构建。

新接入某个上游分类时，从已保存的完整库选取该客户端的原生文件，再调整接入方案；Shadowrocket 等客户端的配套域名文件必须同时引用。不能把整个规则库无差别设置成一个策略。

## 手动升级基础

没有 cron/schedule。Actions → **Propose upstream update** → Run workflow，或在本地运行：

```sh
python3 scripts/sync.py
```

也可用 `--commit <完整40位上游SHA>` 指定版本。程序通过 Git 获取固定提交，完整归档 `rule/` 并核对整目录 tree SHA；上游脚本和 Actions 不会在导入时执行。

下载、目录哈希验证、当前接入方案检查及构建均在临时目录完成后，才替换工作区；安装中断会恢复旧目录。当前文件数量增删超过 20%，或已接入资源条目变化超过 20%，会停止等待审查。检查不会删规则来适配阈值。首次从五组快照扩为完整库是明确授权的范围迁移，不套用全库数量变化阈值。

如果上游删除或拆分了正在接入的文件，先调整接入方案，再重新导入完整库；不会悄悄遗漏分类来通过检查。所有变化先进入候选分支/PR，stable 不会自动更新。

## 校验和发布

```sh
python3 scripts/rules.py build
python3 scripts/rules.py check
python3 -m unittest discover -s tests -v
```

`main` 用于编辑、审核与试用，`stable` 用于日常订阅。审核全库来源/tree SHA、文件变化和接入方案后，合并 main；再单独运行 **Publish stable**，选择试用过的 source commit。发布程序追加提交、保留历史，不 force push。

试用指定版本时，把接入配置里所有 personal-magic 资源 URL 的 `stable` 换成同一个 main commit SHA。只替换外层配置 URL 不会改变内部资源地址。实测后结合客户端连接日志确认命中策略和节点。

本次初始完整导入使用了绑定单一版本和专用分支的一次性作业；作业在保存候选时移除自身，不留持续触发器。后续只有按需手动同步。

## 回退与订阅缓存

将所有资源 URL 固定为之前可用的同一个已发布 commit SHA，可在设备上立即回退。回退所有 stable 用户时，从以前的 `PUBLISHED.json` 取 `source_commit`，通过 Publish stable 发布该来源，会追加恢复旧内容的提交。

客户端每 24 小时检查已发布资源，与仓库自动同步上游无关；刷新手机订阅不会触发上游更新。本次补齐完整库没有变更已接入五组的原文，也未增加手机启用的资源，所以已使用五组原生方案的设备无需重复导入。

原始分类 README 中的链接保留上游地址。引用本项目快照时，要使用本仓库路径前缀，避免意外订阅了上游 master 而绕过固定版本。
