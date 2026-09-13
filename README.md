# personal-magic

以 blackmatrix7 的原版分流规则作为固定基础，未来的个人扩展单独维护。

**当前基础范围：OpenAI、Twitter、Telegram、Global、China 五组，各自使用上游 Quantumult X、Shadowrocket、Clash 原生文件。不是整个上游仓库的全量镜像。**

基础规则与 `upstream/lock.json` 指定的同一个上游 commit **逐字节一致**：保留注释、规则类型、顺序、重复项和原有选项；不再过滤关键词/ASN/进程规则，不做跨客户端转换。上游给不同客户端提供的内容本来可能不同，因此不承诺三个客户端的规则数量或实际行为完全相同。

## 安装及旧版迁移

日常订阅 `stable`，编辑和审核使用 `main`。两个分支不会自动同步。

| 客户端 | 稳定版入口 | 使用方式 |
| --- | --- | --- |
| Quantumult X | [一键添加与手工配置说明](https://github.com/wjykyhhh/personal-magic/blob/stable/dist/quantumultx/import.md) | 添加五个原版分流资源，按说明设置策略绑定和本地兜底 |
| Shadowrocket | [配置订阅](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/shadowrocket/personal-magic.conf) | 配置页添加/更新后选用，首页使用“配置”路由模式 |
| Clash / Mihomo | [配置片段](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/clash/providers.yaml) | 合并 `rule-providers` 和 `rules`，将 `PROXY` 绑定到现有代理组 |

**QX 用户需迁移一次：停用旧的 `personal-magic` 混合分流资源，使用上述入口添加五个原版资源。旧 `dist/quantumultx/rules.list` 已撤下，客户端可能保留旧缓存，单纯刷新旧地址不能完成迁移。** 保留已有节点订阅。添加链接只追加分流资源，不会替你删除旧规则，也不会修改 `[filter_local]` 的兜底。

QX 原版文件含 `OpenAI` 等类别策略名；导入说明通过资源的 `force-policy` 将前四组绑定到 `proxy`，China 绑定到 `direct`。这与旧混合资源的设置方式不同。检查本地规则和其他分流资源，避免抢先匹配。

Shadowrocket 的配置入口保持原地址，内部改为引用原生 RULE-SET，并为 Global、China 同时引用上游配套 DOMAIN-SET。更新配置后也要刷新远程规则集。当前沿用原有 DoH/DNS/IPv6 设置；这些是本项目的配置选择，不属于上游规则文件。

Clash 使用完整的原生 classical YAML（带上游 `no-resolve` 的版本）。`providers.yaml` 与 `rules.yaml` 现在均包含 `rule-providers` 和 `rules` 两部分，均为合并片段。原有五组 `dist/clash/<category>.yaml` 地址也已换成逐字节相同的原版。旧 LAN、自定义直连、自定义代理 provider 已撤下，迁移时请更新整个片段。

节点继续在客户端管理；本仓库仅保存公开规则、接入配置和维护程序。

## 原版基础与扩展的边界

| 位置 | 用途 | 是否修改上游规则 |
| --- | --- | --- |
| `upstream/blackmatrix7/rule/` | 原生文件和对应 README 快照 | 否，按 Git blob 校验 |
| `upstream/lock.json` | 精确上游版本、文件大小和 Git blob SHA | 记录来源 |
| `dist/base/` | 可订阅的 17 个原生规则文件 | 否，逐字节复制 |
| `routing.json` | 类别顺序、直连/代理绑定与兜底 | 仅配置引用方式 |
| `dist/quantumultx/`、`dist/shadowrocket/`、Clash 配置片段 | 客户端接入说明/配置 | 本项目生成，不能称为上游整份配置 |
| `custom/` | 早期个人规则和未来扩展草稿 | **目前不读取、不启用** |

保留 37 个上游文件：17 个用于订阅的原生规则文件、15 份类别 README、5 份 Clash `.list` 参考原文。Clash 选择上游 `*_No_Resolve.yaml`，Global/China 选择完整的 `*_Classical_No_Resolve.yaml`；没有镜像同一分类的全部格式变体。具体路径见 [sources.json](sources.json)。

接入配置顺序是 OpenAI → Twitter → Telegram → Global → China，前四组代理、China 直连，最后中国 GeoIP 直连、其余代理。这些是我们绑定类别的选择，上游本身不是一个完整配置。基础文件不会因规则相互重叠而删行。

之前补充的飞书、银行、Grok、Typeless 和局域网规则保留在 `custom/`，目前均未加入订阅；实际覆盖以五组上游原文为准。未来扩展生成独立资源，明确启用和优先级，保持基础原文件不变。详见 [扩展说明](custom/README.md)。

## 维护与校验

**没有定时同步上游。** 更新只在需要时手动运行：

```sh
python3 scripts/sync.py
python3 scripts/rules.py check
python3 -m unittest discover -s tests -v
```

也可手动运行 Actions 的 `Propose upstream update`。更新先进入候选，审核后再单独发布 `stable`。客户端每 24 小时检查已发布内容，与仓库主动更新上游是两回事；手工刷新订阅不会触发同步。

构建、校验原版基础与接入配置：

```sh
python3 scripts/rules.py build
python3 scripts/rules.py check
```

修改 `custom/` 不会影响当前生成结果。更新程序对下载内容核对上游 Git blob/大小，在完整批次通过后才写入；任一规则文件条目增删超过 20% 时停止，留待审查。此阈值不会删减规则或改写内容。

[构建报告](dist/report.json) 记录原版校验值和路径。检查包括原文到发布文件的一致性、配套文件齐全、扩展隔离、失败下载不污染快照。**这些是离线校验，尚未替代手机实测**，无法保证节点、DNS、登录风控或某条帖子的媒体可用。

试用、固定版本、发布和回退见 [维护说明](docs/maintenance.md)。

## 上游与许可

来源：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)。固定版本见 [upstream/lock.json](upstream/lock.json)，原始来源说明随各分类 README 一并保留。GPL-2.0，详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE.md)。
