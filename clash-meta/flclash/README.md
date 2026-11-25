# Windows FlClash 分流片段

用现有可连接配置的副本合并 [shared-rules.yaml](shared-rules.yaml)，在 FlClash 的「配置 → 添加 → 文件」导入。该片段需要合并到已有配置。

1. 将 `use` 的 `subscription` 改成原配置 `proxy-providers` 中的名称。有多个提供器时按需要列出。保留原来的节点订阅地址、原策略组和运行设置。
2. 将 `PikPak-Auto` 项合并进原来的 `proxy-groups`，将 `shared-pikpak` 合并进后台刷新规则的 `rule-providers`。
3. 将片段中的两条规则放在通用广告和兜底规则之前。同花顺已有的域名和 Windows 进程路径直连保留在前面。进程路径按你自己的安装目录添加。
4. 启用后查看 `PikPak-Auto` 是否显示真实节点。如果首次导入只显示 `COMPATIBLE`，等节点订阅缓存建立后，切回原配置再切回来。仍为空时，检查 `use` 拼写和提供器的更新时间。
5. 通过 FlClash 的代理访问 `https://mypikpak.com/en-US/faq` 和 `https://pikpak.me/en-US/faq`，在「连接」确认命中 `PikPak-Auto`。广告域名应命中 `REJECT`，普通 OPPO 域名可作为对照。验证 GitHub 镜像返回 HTTP 200。

FlClash 的 Windows 实测配置使用显式 `use` 引用现有订阅，测速间隔 300 秒、切换容差 30 ms。两条 PikPak 测试链接和 GitHub 规则镜像返回 200。测速只反映探测延迟。

PikPak 镜像由 [Find N2 同步流程](../find-n2/README.md) 刷新，Shadowrocket 构建时也读取同一份镜像。精确广告拒绝项由 [共享清单](../find-n2/sources.json) 定义。更新清单中的广告项时同步更新本片段的精确规则。ChatGPT 的香港节点排除规则与同花顺的域名直连可按 [Shadowrocket 配置模板](../../templates/FengGe.conf) 移植到自己的客户端策略组。
