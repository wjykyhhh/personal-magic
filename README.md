# personal-magic

**完整复制 blackmatrix7 的 `rule/` 规则库作为原版基础，未来的个人扩展单独维护。**

固定版本：`0087bb74e91b335e17a79fd07a8514277f7d77b4`。包含全部客户端、全部分类、全部格式变体和目录内 README，共 **8,841 个文件**。原文、文件名、目录结构、顺序、重复项、规则类型及选项全部保留。整个目录的 Git tree SHA 与上游相同：`ed757c41f280ef6fff02f23ca9e3cd6449df6429`。

这里的完整规则库指上游 `rule/` 目录；复写、脚本、图标等属于上游其他功能目录。它们不影响本次分流规则库的完整性。

## 完整基础目录

| 客户端 | 稳定版原版目录 | 文件数（含说明和格式变体） |
| --- | --- | ---: |
| Quantumult X | [全部分类](https://github.com/wjykyhhh/personal-magic/tree/stable/upstream/blackmatrix7/rule/QuantumultX) | 1,376 |
| Shadowrocket | [全部分类](https://github.com/wjykyhhh/personal-magic/tree/stable/upstream/blackmatrix7/rule/Shadowrocket) | 1,504 |
| Clash / Mihomo | [全部分类](https://github.com/wjykyhhh/personal-magic/tree/stable/upstream/blackmatrix7/rule/Clash) | 2,884 |
| Surge | [全部分类](https://github.com/wjykyhhh/personal-magic/tree/stable/upstream/blackmatrix7/rule/Surge) | 1,557 |
| Loon | [全部分类](https://github.com/wjykyhhh/personal-magic/tree/stable/upstream/blackmatrix7/rule/Loon) | 1,507 |
| AdGuard | [全部分类](https://github.com/wjykyhhh/personal-magic/tree/stable/upstream/blackmatrix7/rule/AdGuard) | 13 |

基础原文位于 `upstream/blackmatrix7/rule/`。所有文件都可以通过本仓库 Raw 地址读取，例如：

```text
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/upstream/blackmatrix7/rule/QuantumultX/OpenAI/OpenAI.list
```

选中客户端和分类后，保持上游剩余路径不变，使用本仓库前缀。原始 README 中的上游链接也原样保留，因此直接点击那些链接会访问上游；订阅本项目固定版本时请使用本项目的 Raw 地址。

精确版本和逐文件校验值见 [upstream/lock.json](upstream/lock.json)，全库验证统计见 [dist/report.json](dist/report.json)。本说明中的数字对应上述初始完整快照；以后手动更新后的状态以清单和报告为准。

## 当前客户端接入方案

**完整保存规则库，与手机启用哪些规则，是两件分别配置的事。** 仓库已保存全部分类；当前接入方案仍选用 OpenAI、Twitter、Telegram、Global、China 五组，没有将所有分类一起启用。分类之间可能重复，并且直连、代理、拦截的策略不同，新增时需要明确策略和顺序。

| 客户端 | 接入入口 |
| --- | --- |
| Quantumult X | [五组资源的一键添加及手工说明](https://github.com/wjykyhhh/personal-magic/blob/stable/dist/quantumultx/import.md) |
| Shadowrocket | [配置订阅](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/shadowrocket/personal-magic.conf) |
| Clash / Mihomo | [合并配置片段](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/clash/providers.yaml) |

这些接入配置的策略绑定、顺序、DNS 和兜底由本项目设置，不是上游提供的整份配置。五组对应的 17 个原生文件在 `dist/base/` 保留兼容订阅地址，仍与完整基础内的原文件逐字节一致。

如果已经迁移到这五组原生订阅，本次补齐完整库不用重新导入。更早的单个 QX 混合资源 `dist/quantumultx/rules.list` 已停用，需要按上面的 QX 说明迁移一次。已有节点继续在客户端管理。

## 以后怎么扩展和更新

| 位置 | 职责 |
| --- | --- |
| `upstream/blackmatrix7/rule/` | 上游完整原版基础，保持整目录一致 |
| `upstream/lock.json` | 上游提交、整目录 Git tree SHA、每个文件的大小/模式/哈希 |
| `custom/` | 个人扩展草稿，当前未启用；未来独立生成和接入 |
| `sources.json` 的 `files` | 当前接入方案选用的输入文件，**不限制全库同步范围** |
| `routing.json` | 当前方案的类别顺序和策略绑定 |
| `dist/` | 当前方案的订阅文件、说明和验证报告 |

以后补域名或调整某个服务的去向，写独立扩展并显式设置优先级，保持原版基础不变。之前的飞书、银行、Grok、Typeless 等个人补充仍放在 `custom/`，目前不读入基础订阅。

**没有定时更新。** 需要升级基础时手动运行 Actions 的 `Propose upstream update`，或执行：

```sh
python3 scripts/sync.py
python3 scripts/rules.py check
python3 -m unittest discover -s tests -v
```

同步程序每次完整复制同一个上游提交的 `rule/`，核对整个 Git tree，先生成候选再人工发布 stable。未知分类和格式也原样保存，不靠类型白名单决定是否收入基础。详细发布与回退流程见 [维护说明](docs/maintenance.md)。

本地/云端检查验证文件完整性和接入配置，不代表手机实际联网已测试。节点、DNS、地区限制和客户端版本仍会影响实际使用。

## 来源与许可

[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，GPL-2.0。保留上游许可证和全部规则目录内的来源说明；本项目代码及扩展同样按 GPL-2.0 提供。见 [LICENSE](LICENSE)、[NOTICE](NOTICE.md)。
