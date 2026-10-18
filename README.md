# Shadowrocket AdBlock Auto

跨仓库去广告规则自动聚合工程。使用 **GitHub Actions** 定时拉取上游 Shadowrocket 模块，去重并生成一份可订阅的 `.sgmodule`。

- 项目名称：**Shadowrocket AdBlock Auto**
- 维护方式：GitHub Actions 每日自动构建（北京时间约 11:17）
- 模块文件：[`dist/AllApps-Auto.sgmodule`](dist/AllApps-Auto.sgmodule)（首次成功构建后生成）
- 构建报告：[`dist/build-report.json`](dist/build-report.json)

### Shadowrocket 订阅地址

```
https://raw.githubusercontent.com/DanknesSIK/-/main/dist/AllApps-Auto.sgmodule
```

> 首次构建成功前此链接尚不存在。当前默认禁用所有第三方 JavaScript，复杂的信息流广告（包括知乎某些内嵌广告）不能保证被过滤。

### 安装

1. GitHub Actions → **Build Shadowrocket AdBlock Module** → **Run workflow**，确认首次构建成功。
2. iPhone Shadowrocket → 配置 → 模块 → 添加远程模块，粘贴上方订阅地址。
3. 保留你原有的节点与分流配置，先关闭其他重复去广告模块，再启用该模块测试。
4. 在 Shadowrocket 内按需更新模块；GitHub 构建不代表手机自动即时刷新。

### 上游和安全

`sources.json` 包含 fmz200、blackmatrix7、semomanli、ddgksf2013、wmsxwd 的来源清单，部分默认停用以规避冲突、版权和误拦截。构建器默认不执行远程 JS，跳过支付、ChatGPT、Telegram、群晖等受保护域名，HTTPS 解密仅限选定服务域名。

来源属于其各自原作者；规则更新不保证实机效果。**勿提交证书私钥、节点订阅或认证信息。**

如果将仓库由 `-` 重命名为 `shadowrocket-adblock-auto`，应同步修改本 README 中的订阅地址。
