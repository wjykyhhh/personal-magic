# 来源与修改说明

上游：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，GNU GPL version 2。本仓库保留其 LICENSE。五组分类各客户端原生文件、配套来源 README 和 Clash `.list` 参考原文按固定 commit 保存于 `upstream/blackmatrix7/rule/`，完整路径与 Git blob 校验值见 `sources.json`、`upstream/lock.json`。

2026-09-13：将旧版过滤/去重/跨客户端转换流程替换为原生文件镜像。`dist/base/` 的每个文件与指定版本的对应上游文件逐字节相同，不改规则类型、选项、策略名、重复项、顺序或注释。该范围是五个选中分类的指定格式，不是整个上游仓库。

personal-magic 自行提供客户端接入配置（类别绑定、先后顺序、DNS 及兜底）、下载验证/构建/发布程序、说明及扩展草稿。它们均不应被称为上游原作者提供的完整配置。旧自定义规则保留在 `custom/`，当前基础不会加载它们。过去版本中的过滤及转换只存在于 Git 历史。

客户端接入参考：[Quantumult X 官方配置](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)、[QX URL scheme](https://github.com/crossutility/Quantumult-X/blob/master/url-scheme.md)、[Mihomo 规则集](https://wiki.metacubex.one/config/rule-providers/)。Shadowrocket 组合方式依照本仓库保留的上游各分类 README。

本项目维护代码、接入配置与扩展草稿同样按 GPL-2.0 提供。上游作者未对本项目配置或实际联网效果作出背书，具体许可条款以 LICENSE 为准。
