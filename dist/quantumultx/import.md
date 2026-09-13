# Quantumult X 原版基础

[一键添加五组原版分流资源](https://quantumult.app/x/open-app/add-resource?remote-resource=%7B%22filter_remote%22%3A%5B%22https%3A%2F%2Fraw.githubusercontent.com%2Fwjykyhhh%2Fpersonal-magic%2Fstable%2Fdist%2Fbase%2FQuantumultX%2FOpenAI%2FOpenAI.list%2C%20tag%3Dpm-base-OpenAI%2C%20force-policy%3Dproxy%2C%20update-interval%3D86400%2C%20opt-parser%3Dfalse%2C%20enabled%3Dtrue%22%2C%22https%3A%2F%2Fraw.githubusercontent.com%2Fwjykyhhh%2Fpersonal-magic%2Fstable%2Fdist%2Fbase%2FQuantumultX%2FTwitter%2FTwitter.list%2C%20tag%3Dpm-base-Twitter%2C%20force-policy%3Dproxy%2C%20update-interval%3D86400%2C%20opt-parser%3Dfalse%2C%20enabled%3Dtrue%22%2C%22https%3A%2F%2Fraw.githubusercontent.com%2Fwjykyhhh%2Fpersonal-magic%2Fstable%2Fdist%2Fbase%2FQuantumultX%2FTelegram%2FTelegram.list%2C%20tag%3Dpm-base-Telegram%2C%20force-policy%3Dproxy%2C%20update-interval%3D86400%2C%20opt-parser%3Dfalse%2C%20enabled%3Dtrue%22%2C%22https%3A%2F%2Fraw.githubusercontent.com%2Fwjykyhhh%2Fpersonal-magic%2Fstable%2Fdist%2Fbase%2FQuantumultX%2FGlobal%2FGlobal.list%2C%20tag%3Dpm-base-Global%2C%20force-policy%3Dproxy%2C%20update-interval%3D86400%2C%20opt-parser%3Dfalse%2C%20enabled%3Dtrue%22%2C%22https%3A%2F%2Fraw.githubusercontent.com%2Fwjykyhhh%2Fpersonal-magic%2Fstable%2Fdist%2Fbase%2FQuantumultX%2FChina%2FChina.list%2C%20tag%3Dpm-base-China%2C%20force-policy%3Ddirect%2C%20update-interval%3D86400%2C%20opt-parser%3Dfalse%2C%20enabled%3Dtrue%22%5D%7D)

**从旧版迁移：先停用旧的 `personal-magic` 混合分流资源，再添加本页五组资源。旧的 `dist/quantumultx/rules.list` 已撤下，刷新旧链接不能完成迁移。**

保留节点订阅，选择分流模式和可用节点。添加链接只追加分流资源，不会清理旧资源或修改本地规则。

每组文件与固定版本的 blackmatrix7 原生 QX 文件逐字节一致，保留原有类别名策略。这里用资源的 `force-policy` 绑定：OpenAI、Twitter、Telegram、Global → `proxy`，China → `direct`。不要移除该绑定，否则需自行建立同名策略。

以下是合并片段，不是整份 QX 配置。将 `[filter_remote]` 的行加入现有对应区段；检查原有 `[filter_local]`，在其中设置末尾兜底（相同区段不要重复建）。一键添加不会设置兜底。

```ini
# personal-magic client adapter; upstream rule bytes are in dist/base/
# Custom extensions are disabled. Policy bindings/fallbacks are local choices.
[filter_remote]
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/base/QuantumultX/OpenAI/OpenAI.list, tag=pm-base-OpenAI, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/base/QuantumultX/Twitter/Twitter.list, tag=pm-base-Twitter, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/base/QuantumultX/Telegram/Telegram.list, tag=pm-base-Telegram, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/base/QuantumultX/Global/Global.list, tag=pm-base-Global, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/base/QuantumultX/China/China.list, tag=pm-base-China, force-policy=direct, update-interval=86400, opt-parser=false, enabled=true

[filter_local]
geoip,cn,direct
final,proxy
```

`geoip` / `final` 是本项目的兜底选择，属于接入配置，不属于上游原始规则。客户端本地规则及其他资源仍可能影响实际匹配。

自定义飞书、银行、Grok、Typeless 等补充当前未启用；实际覆盖以这五组原版文件为准。仓库不自动同步上游；资源每 24 小时只检查已发布的 stable，亦可手工刷新。
