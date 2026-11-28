# Windows FlClash 分流片段

用现有可连接配置的副本合并 [shared-rules.yaml](shared-rules.yaml)，在 FlClash 的「配置 → 添加 → 文件」导入。该片段需要合并到已有配置。

1. 将四个 PikPak 和 ChatGPT 策略组的 `use` 填为原配置 `proxy-providers` 中的全部订阅名称。只有内置节点时，可以删除这些组的 `use`。`include-all-proxies` 会纳入配置内节点。保留原来的节点订阅地址和运行设置。
2. 将所需策略组合并进原来的 `proxy-groups`，将对应提供器合并进 `rule-providers`。升级时把旧的 PikPak 和 ChatGPT 分流条目改为模板中的规则目标。
3. 将片段中的规则放在通用广告和兜底规则之前。同花顺已有的域名和 Windows 进程路径直连保留在前面。进程路径按你自己的安装目录添加。
4. 启用后查看 `PikPak-Auto` 是否显示真实节点。如果首次导入只显示 `REJECT` 或 `COMPATIBLE`，等节点订阅缓存建立后，切回原配置再切回来。仍为空时，检查 `use` 拼写和提供器的更新时间。
5. 通过 FlClash 的代理访问 `https://mypikpak.com/en-US/faq` 和 `https://pikpak.me/en-US/faq`，在「连接」确认命中 `PikPak-Select`。广告域名应命中 `REJECT`，普通 OPPO 域名可作为对照。验证 GitHub 镜像返回 HTTP 200。

在「代理」页打开 `PikPak-Select` 或 `ChatGPT-Select`，可以选择具体节点，也可以选择列表第一项恢复自动测速。ChatGPT 的手动列表同样按节点名称排除香港。

`PikPak-Auto` 探测 [PikPak 官方 FAQ](https://mypikpak.com/en-US/faq)，以 HTTP 200 判断探测成功。策略组的测速间隔设为 30 分钟，切换容差为 150 毫秒。已有健康检查的订阅提供器沿用自身的检查周期及按需设置。延迟反映官网探测响应时间，下载和播放速度还取决于实际文件线路。

PikPak 镜像由 [Find N2 同步流程](../find-n2/README.md) 刷新，Shadowrocket 构建时也读取同一份镜像。精确广告拒绝项由 [共享清单](../find-n2/sources.json) 定义。更新清单中的广告项时同步更新本片段的精确规则。[ChatGPT](../shared/chatgpt.list) 和 [同花顺](../shared/ths-direct.list) 规则也供 Shadowrocket 使用。ChatGPT 组按节点名称排除香港并自动测速。策略组无候选节点时使用 `REJECT`。
