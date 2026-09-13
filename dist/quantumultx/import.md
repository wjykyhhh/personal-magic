# Quantumult X

[添加 personal-magic 分流订阅](https://quantumult.app/x/open-app/add-resource?remote-resource=%7B%22filter_remote%22%3A%5B%22https%3A%2F%2Fraw.githubusercontent.com%2Fwjykyhhh%2Fpersonal-magic%2Fstable%2Fdist%2Fquantumultx%2Frules.list%2C%20tag%3Dpersonal-magic%2C%20update-interval%3D86400%2C%20opt-parser%3Dfalse%2C%20enabled%3Dtrue%22%5D%7D)

这是添加分流资源，不会替你整理已有规则。保留节点订阅，停用其他重叠分流资源，检查本地规则是否覆盖本资源。不要设置 force-policy；资源内混合了 direct/proxy。选择分流模式，并选择可用的代理节点。

手工添加至 `[filter_remote]`：

```ini
https://raw.githubusercontent.com/wjykyhhh/personal-magic/stable/dist/quantumultx/rules.list, tag=personal-magic, update-interval=86400, opt-parser=false, enabled=true
```
