# 来源与修改说明

上游：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，GNU GPL version 2。本仓库保留其 LICENSE。

2026-09-13：将此前选取五组规则的快照扩展为上游完整 `rule/` 目录，保存全部客户端、分类、格式变体及 README。精确上游提交和目录 Git tree SHA 记录在 `upstream/lock.json`；逐文件大小、模式和 blob 校验值也一并记录。没有删减、去重、改写或跨客户端转换基础原文。

完整规则库保存在 `upstream/blackmatrix7/rule/`，其中来源说明和链接也保持原文。上游其他顶层目录（如复写、脚本和图标）不属于本次分流规则库镜像。

本项目自行提供接入配置、类别选择、策略绑定、顺序、DNS 和兜底，以及完整快照验证、维护、发布程序和个人扩展草稿。这些外围配置不能称为上游作者提供的整份配置。`custom/` 当前未启用。

客户端接入参考：[Quantumult X 配置](https://github.com/crossutility/Quantumult-X/blob/master/sample.conf)、[QX URL scheme](https://github.com/crossutility/Quantumult-X/blob/master/url-scheme.md)、[Mihomo 规则集](https://wiki.metacubex.one/config/rule-providers/)。

新增代码、接入配置与扩展同样以 GPL-2.0 提供。上游作者未对本项目配置或联网效果作出背书，具体条款以 LICENSE 为准。
