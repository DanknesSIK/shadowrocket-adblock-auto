# OPPO Find N2 · Clash Meta

本目录维护 Find N2 的公开分流层。完整配置在本机用现有 ACL4SSR YAML 与这一层合成。节点、订阅链接、账户参数以及设备审计数据都由本机保管。

- 精确拒绝 `adx.ads.heytapmobi.com`。
- PikPak 走 `PikPak-Auto`。策略组汇集配置内节点和各订阅的真实节点，探测 [PikPak 官方 FAQ](https://mypikpak.com/en-US/faq)，以 HTTP 200 判断探测成功，按实测延迟自动选节点，切换容差为 150 毫秒。
- 策略组的测速间隔设为 30 分钟。已有健康检查的订阅提供器沿用自身的检查周期及按需设置。延迟反映官网探测响应时间，下载和播放速度还取决于实际文件线路。策略组为空时使用 `REJECT`。
- ChatGPT 走 `ChatGPT-NonHK`，按节点名称排除香港线路，并自动测速选择其他可用节点。节点全被筛除时使用 `REJECT`。香港节点仍可用于 PikPak。
- 按设备原配置镜像 31 份 ACL4SSR 列表。对 PikPak 独立规则保留 `mypikpak` 和 `pikpak.me` 的匹配。
- GitHub Actions 每天北京时间约 09:23 检查上游提交，校验格式、数量和许可，再用一次提交发布。失败时 GitHub 上保留上一次成功的规则。定时运行可能延迟。
- Clash Meta 从固定的镜像地址刷新规则提供者，间隔为 24 小时。设备必须先导入本机生成的配置并运行。公开规则更新无需重新导入。配置组这类结构性变更需要重新生成和导入。

## 在本机生成完整配置

使用当前配置的 YAML 导出或原始「ACL4SSR 整包」配置。脚本生成一份新文件，补上缺少的策略组和规则，也保留同名策略组的自定义参数。生成文件含自己的节点信息，请仅留在自己的设备。

```bash
node clash-meta/find-n2/apply.mjs Current-ACL4SSR.yaml FindN2-ACL4SSR.yaml
```

将输出作为 Clash Meta 的本地配置导入。保留原配置可在配置列表随时切回。如果 `PikPak-Auto` 已存在，沿用该组的现有参数。想启用新版 PikPak 参数，可在输出文件里把该组的 `interval` 改为 `1800`、`tolerance` 改为 `150`。

## 上游

- [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR)，CC BY-SA 4.0。镜像保留源文件和许可。
- [blackmatrix7/ios_rule_script 的 PikPak 规则](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Clash/PikPak)，GPL-2.0，源文件标注作者为 tugepaopao。镜像转换为 Clash classical 文本、去重并补齐服务域名。生成脚本及修改在本目录可查。
- [自动更新记录](../../actions/workflows/find-n2-clash.yml)

## 可选共享域名规则

[同花顺直连](../shared/ths-direct.list) 可按 [Mihomo 配置片段](../flclash/shared-rules.yaml) 并入已有配置。
