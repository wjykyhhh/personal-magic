# 维护、试用与回退

## 基础与扩展

`sources.json` 精确列出五组分类使用的客户端原生文件，以及配套 README/参考文件。`upstream/lock.json` 固定同一个上游 commit 和每个文件的 Git blob/大小。`scripts/rules.py` 对字节进行验证并原样复制到 `dist/base/`，只生成外围接入配置，不解析转换规则内容。

请勿手工编辑原版快照来补域名。`custom/` 是独立草稿区，目前构建不读取它。未来扩展应独立输出、独立启用，并为具体请求记录来源、预期策略和实际验证结果。修改扩展不得改变基础文件的校验值。

`routing.json` 管理类别引用顺序及策略绑定。它属于我们的接入配置，不能被描述为上游原作者规定的唯一顺序。QX/Shadowrocket/Clash 各自的原生内容和能力不同，逐字节一致指与各自上游文件一致，不表示三端完全相同。

## 手动更新上游

没有 `schedule`/cron。Actions → **Propose upstream update** → Run workflow，或执行：

```sh
python3 scripts/sync.py
```

需要选择特定上游版本时，使用 `python3 scripts/sync.py --commit <完整40位上游SHA>`。脚本从同一固定提交读取文件清单和原文，逐个验证 Git blob/大小；新出现的 Shadowrocket 配套域名文件会要求先更新来源清单，避免只取一半规则。

所有下载及完整构建在临时目录验证后，才替换工作区的 upstream/dist；失败时保留已有版本。任一规则文件条目增删超过 20% 会中止，不会通过删规则来凑阈值。确认上游变化合理后，单独审查并调整阈值，再运行更新。

Actions 仅推送候选分支并开 PR，不直接发布 stable。脚本不会覆盖 custom。PR 描述给出各文件条目增删数；空行、注释、格式变化仍会原样保存。

## 试用与发布

`main` 是编辑/审核版本，`stable` 是日常订阅。合并 main 不会自动发布。

1. 审查 diff，运行 `python3 scripts/rules.py check` 和 `python3 -m unittest discover -s tests -v`。
2. 试用时，将接入配置里的**所有** personal-magic 资源 URL 的 `stable` 替换为同一个 main commit SHA。只替换外层配置 URL 不会修改其内部链接；QX 五组、Shadowrocket 七个资源、Clash 五个 provider 都要固定。
3. 在手机/目标客户端检查资源加载成功、实际命中策略，并试用 X/TG 媒体、AI 登录/上传、飞书及自己的银行 App。离线字节验证不能代表联网成功。
4. Actions → **Publish stable** → Run workflow，分支选 main。填写审核/试用过的完整 main commit SHA，勾选试用确认；留空使用作业检出的 main。
5. 发布脚本重新校验并运行测试，再追加一个 stable 提交，记录 `PUBLISHED.json` 和版本标签。客户端同批刷新配置及全部远程规则集。

发布程序不 force push。原始文件精确匹配 `upstream/lock.json`，并不表示永远跟随上游最新 master。客户端缓存也可能暂时保留上次内容。

通过连接器人工发布时，同样先校验完整本地树和文件哈希，记录来源提交、上游提交、前一版 stable 及验证范围；不得将未进行的云端或设备测试写成通过。

## 旧版迁移与回退

旧 QX 混合资源 `dist/quantumultx/rules.list` 已撤下。停用旧资源，按 [新导入说明](../dist/quantumultx/import.md) 添加五组原生资源并配置策略、兜底；一键添加只增加远程资源。旧版“不要设置 force-policy”的说明已不适用。

Shadowrocket 保留配置 URL，需要更新配置并刷新其远程资源。Clash 更新 `rule-providers` 和 `rules` 整个片段；旧 custom/lan provider 已撤下。

立即回退设备：将全部资源 URL 固定到以前可用的同一个已发布 commit SHA。也可下载该提交的旧版配置。旧版本的文件和原混合订阅仍在 Git 历史中。

回退所有 stable 订阅：从过去的 `PUBLISHED.json` 取 `source_commit`，使用 Publish stable 发布它，会追加恢复旧内容的提交，不删除历史。不同版本的 QX 资源结构可能不同，回退跨越这次迁移时需同步恢复旧资源设置。

## 排查规则问题

从客户端连接记录中找到失败请求的实际域名/IP、命中规则、策略和最终节点。先确认启用配置及旧分流资源是否抢先匹配。

需要补域名或改去向时，记录到独立扩展草稿并验证后再显式接入；不要改动原版基础。已命中正确代理仍失败时，检查节点、DNS、出口或 UDP。不能仅凭网页能开、图片失败就断言一定缺规则。
