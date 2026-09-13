# personal-magic

个人维护的纯分流规则。选取 blackmatrix7 的完整规则快照，加上自定义覆盖，生成 Quantumult X、Shadowrocket 和 Clash/Mihomo 各自的格式。

**节点继续在客户端管理。本仓库不包含节点、机场订阅、账号密码、复写脚本或 MITM 证书。**

## 订阅与安装

日常使用 `stable` 分支。`main` 用于编辑、审核和试用，合并到 main 不会自动发布到 stable。

| 客户端 | 稳定版入口 | 使用方式 |
| --- | --- | --- |
| Quantumult X | [一键添加说明](https://github.com/wjykyhhh/personal-magic/blob/stable/dist/quantumultx/import.md) · [规则订阅](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/quantumultx/rules.list) | 添加到分流资源，保留文件内的 direct/proxy 策略 |
| Shadowrocket | [配置订阅](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/shadowrocket/personal-magic.conf) | 在“配置”页添加远程配置，下载后选用 |
| Clash / Mihomo | [远程规则集配置片段](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/clash/providers.yaml) · [完整 rules 片段](https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/clash/rules.yaml) | 合并到现有配置，按下文绑定代理策略组 |

### Quantumult X

1. 打开上表“一键添加说明”，点击其中的添加链接；也可以复制规则订阅地址，在分流资源中手工添加。
2. **不要设置强制策略 `force-policy`**：这一份规则同时包含直连和代理。保留节点订阅，选择可用节点和分流模式。
3. 停用原来重叠的分流资源，检查本地规则是否抢先匹配。添加链接只追加资源，不会替你清理旧规则；同时启用几套规则，结果仍可能被旧规则覆盖。

文件使用内置 `proxy` 和 `direct`，已经包含局域网、中国 GeoIP 直连和最终代理。节点能否访问某个服务仍取决于实际出口。资源设置为每 24 小时检查更新，也可手工更新。

### Shadowrocket

在“配置”页添加上表配置地址，下载并选用 `personal-magic.conf`；首页全局路由选择“配置”，选一个可用节点。先保留原来的 lazy 配置，便于切回。

这是完整的、无节点的分流配置，规则嵌入一个文件，不需要另找 DOMAIN-SET 配套。它使用腾讯/阿里 DoH、系统备用 DNS、IPv6 开启、不优先 IPv6；直连域名 DNS 失败不会自动改走代理。未额外禁止 QUIC；节点不支持 UDP 时仍拒绝对应 UDP 请求。语音、通话问题需检查节点的 UDP 支持。

### Clash / Mihomo

`providers.yaml` 是 JSON 写法的合法 YAML，包含 `rule-providers` 和 `rules` 两部分；**它是配置片段，不是节点订阅或完整 Clash 配置**。

将两部分合并到你现有配置中，并把规则中的 `PROXY` 替换为现有代理策略组名称。保留规则顺序与末尾 `GEOIP,CN,DIRECT`、`MATCH,PROXY`。如果客户端会用节点订阅覆盖整份配置，请使用该客户端的覆写/合并功能保存这些修改。

各远程规则集设置为每 24 小时检查。发布后建议一起更新这些规则集，避免客户端缓存暂时混用前后版本。需要固定版本时，把所有地址中的 `stable` 换成同一个已发布 commit SHA。

## 首版分流意图

| 服务 | 预期策略 | 覆盖范围 |
| --- | --- | --- |
| OpenAI / ChatGPT | 代理 | 主域名、静态资源、上传内容及上游补充 |
| Grok | 代理 | `grok.com`、`x.ai` 及其子域名 |
| Typeless | 代理 | `typeless.com`、官网使用的 `typeless-static.com`；不是完整 App 抓包清单 |
| X | 代理 | `x.com`、Twitter、`twimg.com` 图片/视频、`twvid.com` 等 |
| Telegram | 代理 | 主域名、媒体域名和上游 IPv4/IPv6 网段 |
| 中国大陆飞书 | 直连 | `feishu.cn`、`feishu.net`、`feishucdn.com`、`feishupkg.com` |
| 常用大陆银行 | 直连 | 工/农/中/建/交、招行、邮储等已列主域名；不承诺所有银行、第三方 SDK 均已覆盖 |
| 其他流量 | 按规则判断 | 明确代理规则优先，国内域名和中国 GeoIP 直连，其余代理 |

具体优先级：局域网 → 自定义直连 → 自定义代理 → OpenAI / Twitter / Telegram → Global → China → 中国 GeoIP → 最终代理。自定义直连/代理中完全相同的规则冲突会报错；嵌套域名应按意图调整，不能只靠去重。

## 如何维护

| 位置 | 内容 |
| --- | --- |
| `custom/direct.list` | 自定义直连覆盖 |
| `custom/proxy.list` | 自定义代理覆盖 |
| `custom/exclude.list` | 从上游排除完全相同的规则 |
| `custom/lan.list` | 局域网直连 |
| `upstream/blackmatrix7/` | 原始规则快照，保留来源注释 |
| `upstream/lock.json` | 固定上游 commit 与每个文件的 Git blob 校验值 |
| `sources.json` | 所选分类、数量下限和明确跳过的类型 |
| `scripts/` | 下载、编译、检查与发布程序 |
| `dist/` | 自动生成的各客户端文件；不要直接手改 |

在本地修改 custom 后运行：

```sh
python3 scripts/rules.py build
python3 -m unittest discover -s tests -v
```

查询某个域名或 IP 的显式匹配：

```sh
python3 scripts/rules.py match pbs.twimg.com
```

**上游更新仅在需要时手动发起，已关闭每日定时检查。** 在 Actions 中运行 `Propose upstream update`，或在本地运行 `python3 scripts/sync.py`，即可检查上游；通过检查的更新再审核、试用和发布。具体操作和回退见 [维护说明](docs/maintenance.md)。

## 检查能覆盖什么

- 严格解析、文件总数核对、空响应/HTML 错误拦截、快照完整性检查。
- 相对当前快照，任一分类新增或删除超过 20% 时中止本次上游更新。
- 关键域名/IP 的预期策略检查，以及 QX、Shadowrocket、Clash 输出的交叉校验。
- 生成结果必须与源文件一致，检查未通过不发布。

这些是离线规则检查，不能验证手机实际联网、节点解锁地区、DNS、登录风控、QUIC 或某条 X 帖子是否仍有媒体。出现问题时，先在客户端连接日志查看实际域名、命中规则和出口，再决定补规则还是换节点。

## 上游与许可

本项目使用 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) 的 OpenAI、Twitter、Telegram、Global、China 分类，选择完整的 Clash `.list` 作为共同输入，再生成目标客户端格式。

上游部分 Shadowrocket 分类将域名拆为单独的 `*_Domain.list`，需要按其说明配套使用；本项目的生成结果已经包含域名，不能按上游文件名猜格式。

为减少宽泛匹配、保持三端适用，明确跳过上游 `DOMAIN-KEYWORD`、`IP-ASN`、`PROCESS-NAME`，保留域名及 IP 网段。跳过数量和相反策略的重复项见 [构建报告](dist/report.json)。因此本项目不是 blackmatrix7 原规则的无损镜像。

保留上游的 GPL-2.0 许可证和来源。新增代码、规则覆盖及生成文件同样按 GPL-2.0 提供。详情见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE.md)。
