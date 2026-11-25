# OPPO Find N2 · Clash Meta

本目录维护 Find N2 的公开分流层。完整配置在本机用原始 ACL4SSR YAML 与这一层合成。节点、订阅链接、账户参数以及设备审计数据都由本机保管。

- 精确拒绝 `adx.ads.heytapmobi.com`。
- PikPak 走 `PikPak-Auto`，包含配置内节点和节点订阅，测速间隔 300 秒，切换容差 30 ms。该组在没有可用组成员时拒绝接入。
- 按设备原配置镜像 31 份 ACL4SSR 列表。对 PikPak 独立规则保留 `mypikpak` 和 `pikpak.me` 的匹配。
- GitHub Actions 每天北京时间约 09:23 检查上游提交，校验格式、数量和许可，再用一次提交发布。失败时 GitHub 上保留上一次成功的规则。定时运行可能延迟。
- Clash Meta 从固定的镜像地址刷新规则提供者，间隔为 24 小时。设备必须先导入本机生成的配置并运行。公开规则更新无需重新导入。配置组这类结构性变更需要重新生成和导入。

## 在本机生成完整配置

使用原始「ACL4SSR 整包」配置或其未经改动的导出。生成文件含自己的节点信息，请仅留在自己的设备。

```bash
node clash-meta/find-n2/apply.mjs ACL4SSR-original.yaml FindN2-ACL4SSR.yaml
```

将输出作为 Clash Meta 的本地配置导入。保留原配置可在配置列表随时切回。如果旧配置的 URL 已失效，使用此前的本地导出作原始输入。

## 上游

- [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR)，CC BY-SA 4.0。镜像保留源文件和许可。
- [blackmatrix7/ios_rule_script 的 PikPak 规则](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Clash/PikPak)，GPL-2.0，源文件标注作者为 tugepaopao。镜像转换为 Clash classical 文本、去重并补齐服务域名。生成脚本及修改在本目录可查。
- [自动更新记录](../../actions/workflows/find-n2-clash.yml)

## 可选共享域名规则

[同花顺直连](../shared/ths-direct.list) 和 [ChatGPT](../shared/chatgpt.list) 可按 [Mihomo 配置片段](../flclash/shared-rules.yaml) 加入已有配置。使用原配置的提供器名称。验证 ChatGPT 策略组已加载可用非香港节点，再启用相关分流。筛选依据是节点名称。
