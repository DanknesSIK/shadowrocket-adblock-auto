# Shadowrocket AdBlock Auto

将多个公开规则仓库的 Shadowrocket 广告规则聚合到**一个远程订阅模块**，由 GitHub Actions 自动更新。原来的节点订阅与代理分流配置不需要改变。

## 安装地址

```
https://raw.githubusercontent.com/DanknesSIK/shadowrocket-adblock-auto/main/dist/AllApps-Auto.sgmodule
```

进入 Shadowrocket → 配置 → 模块 → 添加远程模块，粘贴上述地址。确认已选用含有效 HTTPS 解密证书的主配置，开启模块后刷新订阅。

- [查看生成模块](dist/AllApps-Auto.sgmodule)
- [查看构建报告](dist/build-report.json)
- [查看自动构建](../../actions/workflows/build.yml)
- [调整来源与许可脚本](sources.json)

## 启用的来源

- fmz200/wool_scripts：全 App 广告域名与 URL/Body 规则。
- blackmatrix7/ios_rule_script：补充去广告规则。
- semomanli/Shadowrocket：知乎、小红书独立规则。
- letswish/Shadowrocket-Module：15 款 App 聚合规则，含经过挑选的第三方 R-Store 响应脚本。
- 其他来源已经保留在 `sources.json`，默认关闭。

## 已允许的第三方 JavaScript

脚本**不是全部放开**。只启用 `letswish-curated` 模块引用、并同时匹配以下精确文件路径与服务域名的 HTTP 响应脚本：

| 脚本 | 允许的目标 |
|---|---|
| `zhihu.js` | 知乎 |
| `xiaohongshu.js` | 小红书 |
| `weibo.js` | 微博 |
| `bilibiliJson.js` | B站 |
| `amap.js` | 高德 |
| `goofish.js` | 闲鱼 |

这些脚本来源：`https://raw.githubusercontent.com/zirawell/R-Store/main/Res/Scripts/AntiAd/`

模块构建会屏蔽其他脚本来源、非 HTTP 响应脚本，以及匹配敏感服务域名的规则。付款、登录、ChatGPT、Telegram、群晖等维持原保护规则；不会注入证书私钥或节点信息。

**风险提示：** 第三方脚本能够访问所匹配服务的解密响应正文，部分可能包含个人数据；脚本文件在上游的 `main` 分支更新时，内容可能改变，不经过独立人工复核。规则过滤和域名白名单**不能保证脚本绝对安全**，也不能保证去掉所有广告。本项目并未在你的 iPhone 上进行实机测试。出现加载异常时，先关闭本模块并恢复原配置。不要把支付、登录、验证码、银行业务添加到允许解密的域名列表。

## 自动更新

工作流 `.github/workflows/build.yml` 在每天北京时间 **11:17 左右** 运行（GitHub 定时任务可能延迟），拉取上游模块、去重、过滤、检查输出并提交 `dist/AllApps-Auto.sgmodule` 与 `dist/build-report.json`。

在 Shadowrocket 中需要**刷新远程模块订阅**才能获取新的生成文件，手机不会随 GitHub 构建立即更新。自动构建失败时原来的生成文件保留。

如需关闭全部第三方 JS：将 `sources.json` 的 `settings.include_remote_scripts` 改为 `false`，提交后等待构建成功，再在 Shadowrocket 刷新订阅。
