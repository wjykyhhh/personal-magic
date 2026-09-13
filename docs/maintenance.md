# 维护、试用与回退

## 两个分支

- `main`：规则源、自动更新候选合并后的试用版本。
- `stable`：日常订阅。只有发布操作才会更新；main 的 PR 合并不会改动它。

首版经过离线校验后初始化 stable，尚未代替使用者进行手机实测。之后在发布工作流中确认已试用。

## 修改自己的规则

修改 `custom/direct.list` 或 `custom/proxy.list`，格式是 `DOMAIN-SUFFIX,example.com` 或 `DOMAIN,api.example.com`，不填写策略。自定义文件不由上游同步程序覆盖。

`exclude.list` 排除的是标准化后完全相同的上游规则；若想将上游代理域名改为直连，通常直接写进 `direct.list` 更清楚。自定义直连优先于自定义代理，嵌套域名的冲突应主动调整；例如把整个 `example.com` 直连后，再把 `api.example.com` 放进代理文件，会被前面的直连覆盖。

运行编译和测试后提交源文件与 dist。GitHub Check rules 会检查是否遗漏重新生成。

## 上游更新

Actions → **Propose upstream update** 可手工检查，也有每日定时检查。所有选中分类使用同一个上游 commit，下载到临时目录，全部通过校验才写入候选文件。

若无变更，不提交。若有合格变更，创建 `automation/upstream-…` 分支及 PR；PR 描述列出增删数。20% 异常变更阈值、数量下限、格式错误或关键规则回归会中止流程，不改 stable。超过阈值时需阅读差异，确认合理后再手动更新快照或调整阈值；不要为消除报错直接关闭检查。

GitHub 如果提示 Actions 无法创建 PR，在仓库 Settings → Actions → General → Workflow permissions 中允许 GitHub Actions 创建 PR。候选分支仍会保留，日志提供比较链接，可自行开 PR。自动创建的 PR 可能不会触发另一个 PR 工作流，但同步作业本身已运行测试，发布作业还会再验证。

定时检查不代表上游每天都有新规则。GitHub 在仓库长期无活动时可能停用定时工作流，可在 Actions 中重新启用。

## 试用与发布

1. 审查更新 PR，合并到 main。更新前可记录 stable 当前 commit，作为立即回退地址。
2. 测试设备临时把订阅 URL 中的 `stable` 替换成待发布的 main commit SHA，避免试用过程中版本漂移。QX 停用旧资源后测试新资源；Shadowrocket 下载为另一个配置；Clash 同批规则集固定为相同 commit。
3. 实测 X 图片/视频、Telegram 媒体、AI 登录/上传、飞书文档/通话及自己的银行 App，结合连接日志确认命中路径。
4. Actions → **Publish stable** → Run workflow，工作流分支选择 main。可填写 main 上已试用的完整 40 位 commit SHA，勾选已审核/试用后运行。留空使用运行时检出的最新 main，请避免误发未试用的新提交。
5. 发布作业重新编译校验并运行测试，然后一次移动 stable 引用。记录 `PUBLISHED.json` 和版本标签。各客户端需刷新订阅/配置，GitHub Raw 与客户端缓存可能延后生效。

发布程序只允许 main 历史中的 source commit，stable 更新不使用 force push。自动化流程是约定的发布路径，并未配置 GitHub 分支保护；拥有仓库写权限的人仍能手动修改 stable。

## 回退

立即回退某个客户端：将订阅 URL 中的 `stable` 替换为之前可用的已发布 commit SHA，刷新订阅；同一个版本的多个 Clash 规则集应一起固定。

回退所有跟随 stable 的客户端：在 stable 历史或对应 `PUBLISHED.json` 找到之前版本的 `source_commit`，运行 Publish stable 并填写该值。会追加一个恢复旧内容的新提交，不删除历史。首版若没有 PUBLISHED.json，使用初始化 main 的规则提交 SHA。

## 排查“网页能开，图片不行”

在 QX/Shadowrocket 的连接记录中找到失败的图片请求，记录域名、命中规则、最终策略及节点，区分以下情况：

- 命中旧配置/旧资源：检查当前启用配置、本地规则和重复分流资源。
- 命中直连但应代理：补入 custom/proxy，并添加 tests/routes.json 的预期用例。
- 已命中代理仍失败：换可用节点试验，检查 DNS、出口地区和 UDP；规则本身不能修复节点。
- 银行/飞书仍异常：确认实际请求域名，按需增加精确直连域名，避免把公共云/CDN整网改为直连。
