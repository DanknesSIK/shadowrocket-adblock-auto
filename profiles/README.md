# FengGe.conf 使用说明

面向中国大陆日常网络、国内工作软件、境外 AI、视频与 NAS 的 Shadowrocket 完整主配置。节点继续由首页已有订阅管理。配置本身不提供代理服务器，不含订阅令牌、节点凭据、证书私钥或私人 tailnet 标识。

## 安装

配置文件直链：

```text
https://raw.githubusercontent.com/DanknesSIK/shadowrocket-adblock-auto/main/profiles/FengGe.conf
```

1. 保留当前能用的配置作为回退。在首页保留自己的节点订阅，选择一个可用节点。
2. 打开 **配置 → 右上角 + → 粘贴上述 URL → 下载**，然后点击下载的配置并选择 **使用配置**。这是完整 `.conf`，应从“配置”页面导入。
3. 停用旧的 GMO 分流模块、旧去广告模块和本仓库 `AllApps-Auto.sgmodule`，避免旧规则覆盖本配置。首次验证只启用这一份主配置。
4. 首页 **全局路由选择“配置”**，断开并重新连接。
5. 点击配置后的 ⓘ，在代理分组中设置业务出口。检查“规则集 URL”中的资源都下载成功；失败时先通过已有可用节点重新下载、编译。

主配置使用 Shadowrocket 的原生策略组和 `TAILSCALE` 策略。需要支持这些功能的客户端版本；本仓库无法替代设备上的导入、编译和联网验收。

## 默认分流

| 业务 | 默认行为 | 使用建议 |
|---|---|---|
| 节点选择 | `PROXY`，使用首页节点 | 可以换为手动、自动、故障转移或地区组 |
| AI服务、Telegram、TikTok | 各自选择 `PROXY` | 日常使用时分别固定到实测可用的具体节点，避免跨地区切换；改变首页节点也会改变 `PROXY` |
| YouTube、国际影视、Spotify、Google | 节点选择 | 可以独立选择速度或服务支持情况更合适的节点 |
| 海外开发 | 节点选择 | GitHub 等独立控制，不随微软服务直连 |
| 苹果服务、微软服务 | `DIRECT` | Copilot 等已在前面归入 AI服务；个别业务打不开时单独换出口 |
| 微信支付、银行、证券、国内 AI、飞书、钉钉 | 明确 `DIRECT` | 关键放行规则优先于广告表 |
| 国内服务 | `DIRECT` | 中国域名表与中国 IP 兜底；Steam 国内下载单独直连 |
| 广告拦截 | `REJECT` | 误拦截时可临时改为 `DIRECT`；这只改变匹配结果，不减少加载规则的内存 |
| Hermes内网 | `TAILSCALE`，仅匹配 `ts.net` 域名 | 需要已认证、已启用的内置 Tailscale |
| 漏网之鱼 | 节点选择 | 未识别的境外业务默认代理；可手动改成直连，但会降低境外覆盖率 |

六个地区组均为手动选择，按节点名称筛选；筛选不验证实际出口地区或流媒体解锁。空地区组不要选。自动选择、故障转移每 1800 秒测试；自动选择公差 150 ms，减少因微小延迟差反复切换。延迟测试不等于下载测速，也不等于应用解锁检测。

## 广告与规则规模

本配置加载 18 个远程文件，全部使用 blackmatrix7 的 Shadowrocket 格式，并锁定到同一通过检查的提交版本。没有把多个全量广告库叠加在一起，也没有加载第三方脚本、响应正文改写或 HTTPS 解密域名。

- 广告只加载 `AdvertisingLite_Domain.list`，覆盖域名匹配；主动省略同目录 `.list` 中的宽泛关键词、IP 与 URL-REGEX。
- 中国分流只加载 `China_Domain.list`，补充 `.cn` 后缀和 `GEOIP,CN`；省略宽泛的关键词和 User-Agent 分流。
- Apple 的 `.list` 与 `_Domain.list` **互补**，配套加载。不能把所有同名普通表和域名表都当作重复内容删除。上游目录 README 应逐项核对。
- OpenAI 改用主配置中的明确域名，移除原上游表里覆盖整个云服务商的 `IP-ASN,20473`，以及把公共监控、支付服务整体归入 AI 的规则。新增服务域名需要更新主配置模板，不能认为上游 OpenAI 表的所有变化都会自动合入。
- 广告域名拦截无法保证清除 YouTube 片内广告、App 信息流广告或与正文共用域名的开屏广告。
- `MITM` 默认关闭。单独打开解密开关不会凭空增加去广告能力；这份主配置没有配置解密目标或重写脚本。

实测下载字节数、展开规则条目数和各文件 SHA-256 见 [validation-report.json](validation-report.json)。文件体积和条目数都不等于 PacketTunnel 内存占用；无法通过这份配置承诺“低于 50 MB”或“永不重启”。

## NAS、Hermes 与 Tailscale

局域网 IP、`.local`、`.lan`、`.home.arpa`、群晖和 QuickConnect 域名直连。`ts.net` 域名交给 `Hermes内网`；公开文件没有写入个人主机名。

这条分流规则不会自动开启、认证或修复 Tailscale。需要访问 tailnet 时，在 Shadowrocket 的内置 Tailscale 设置中完成认证并确认连接；通常无需设置 Tailscale 出口节点。不要依靠同时开启两个独立 VPN 来实现这条规则。

如果使用目标的 `100.x.x.x` 地址而非域名，或访问 Tailscale 子网路由，请在本地的 Rule 顶部添加**实际目标 /32 或实际子网**的 `TAILSCALE` 分流，并按需要启用客户端的 Tailscale 子网选项。不要把整个运营商 CGNAT 地址范围都交给 Tailscale。本配置没有旁路 `100.64.0.0/10`，也没有把该范围全部转发至 Tailscale。

如需定位重启问题，可在不需要远程内网时关闭内置 Tailscale，并用相同网络、节点和应用对比；此时远程 Hermes 不可用。配置规则无法消除客户端或系统组件本身的故障。

## DNS、IPv6 与视频

- 使用一个国内 DoH，并以系统 DNS 回退；局域网名称使用系统 DNS。
- 禁止直连 DNS 失败后自动改走代理，保留国内业务的明确路由。
- 默认关闭 IPv6，沿用保守的 IPv4 设置。特定 IPv6 网络需要另外验证，不能据此声称所有 IPv6 流量均被封锁或不会绕行。
- 默认 `block-quic = all-proxy`：让代理侧 QUIC 回退 TCP，国内直连 QUIC 保留。若已确认节点的 UDP 转发稳定，且 YouTube 存在性能问题，可在本地改成 `always-allow` 后对比。节点带宽、丢包和拥塞仍会影响速度。
- 不伪造 STUN 响应，不使用全端口 UDP 封锁，不关闭 TLS 证书校验。

## 更新、回退与排查

主配置包含 `update-url`。手机必须开启 **设置 → 自动更新 → 配置 → 自动后台更新**，并允许系统后台 App 刷新。也可以手动对主配置执行“更新配置”。后台调度可能延迟，不保证准点。

**v1.1 的更新流程：**

1. [主配置工作流](../../actions/workflows/profile.yml) 每天北京时间 **08:47 左右**，以及模板/检查程序修改后，读取上游 `master` 的一个精确提交。
2. 下载这一提交中的全部所需规则，检查格式、策略关系、来源哈希、关键业务样例和规则规模。
3. 全部通过后，在一次 Git 提交中发布主配置、应急配置与验证报告。主配置内的规则链接固定到这个上游提交。
4. 下载失败、样例失败或规模异常时停止发布，手机继续使用上一份已发布版本。无关上游提交未改变实际规则内容时不重复发布。
5. 手机更新**整份主配置**后才能取得下一份固定规则版本。只点“编译配置”或只刷新规则集，会继续拉取当前固定版本。

发布限制：展开条目上限 65,000、远程文本总量上限 1,500,000 字节；大规则文件单次增长超过约 35% 或减少超过约 25% 会被拦下，小文件另有绝对变化容差。这些检查能发现部分异常，不能保证无误拦截，也不代表设备内存上限。

自动更新整份主配置可能覆盖本地文本修改及分组设置。需要长期保留私有 /32 分流、DNS 或固定节点设置时，使用客户端的 **扩展配置**：从远程主配置扩展出一个本地配置，将个性设置保存在本地扩展中；在 ⓘ → 通用 → 包含配置 中核对继承关系。主配置仍负责远程更新，本地扩展拥有更高优先级。不要把私人内网信息上传到公开仓库。扩展关系与更新后的分组选择仍需在客户端确认。

如果选择删除/注释 `update-url` 并仅保存独立本地副本，该副本会保持当前固定规则版本，需要以后手动导入新版。

本仓库原有 `build.yml` 继续只更新独立去广告模块；新增 `profile.yml` 更新主配置。两者共享发布锁以避免同时推送。任何构建通过都不等于 iPhone 实机验证。

### 应急配置

提前下载 [FengGe-Emergency.conf](https://raw.githubusercontent.com/DanknesSIK/shadowrocket-adblock-auto/main/profiles/FengGe-Emergency.conf)，需要时在本地切换：

- 使用已有首页节点，保留常用国内直连与基础 AI/内网域名规则。
- 不加载远程规则、不运行自动测速、脚本或解密，也不自动更新自身。
- 不提供广告过滤；未收录的国内域名依赖中国 IP 兜底，覆盖少于主配置。
- 局域网 NAS 仍可访问；远程 `ts.net` 请求明确拒绝，避免经公共代理发送。排查内置 Tailscale 负载时，仍需要在客户端手动关闭它的全局开关；切换配置不会关闭该全局功能。
- 在断网或远程资源加载失败时，已提前下载的文件可用于排查，但节点失效、运营商断网等问题仍可能影响连接。

恢复后切回 `FengGe.conf`。历史完整版本也保留在 Git 提交记录中。

| 现象 | 首先检查 |
|---|---|
| 导入提示格式错误 | 地址末尾为 `.conf`，下载内容是文本而非 GitHub 网页；通过配置页导入，不能把 Base64 节点订阅或 Clash YAML 当成主配置 |
| 地区组为空 | 当前订阅是否有匹配名称的节点；先回到 `PROXY` 或“手动选择” |
| 某 App 加载异常 | 临时将广告拦截改为 `DIRECT` 对比；检查是否还有旧模块启用 |
| AI 提示地区不支持 | 切换实测支持该服务的固定出口；配置不能改变节点实际出口或服务资格 |
| Tailscale 不通 | 内置 Tailscale 是否在线、目标 ACL、MagicDNS 或精确 IP/子网路由是否正确 |
| 仍然重启 | 回退已验证配置，并保留新一轮断开时刻的系统/隧道日志；规则行数不能直接证明根因 |

## 验证范围

运行：

```bash
python3 scripts/validate_profile.py
python3 -m unittest discover -s profile_tests -v
```

检查 UTF-8/LF、配置段、策略引用、默认选择、环路、节点名筛选、远程资源状态与格式、来源哈希，以及关键业务的离线匹配样例。该工具是自定义静态检查器，**不是 Shadowrocket 原生编译器**；它不验证设备内存、DNS/ASN/GeoIP 实际查询、节点协议兼容性、吞吐、稳定性或服务解锁。

维护者修改 `templates/FengGe.conf` 后运行 `python3 scripts/update_profile.py`，由程序验证并生成发布文件。不要直接修改已发布的 `profiles/FengGe.conf`；它的哈希必须与发布报告一致，否则自动更新会停止。

## 参考来源

- [LOWERTOP/Shadowrocket](https://github.com/LOWERTOP/Shadowrocket)：社区维护的使用手册、策略组参数和内置 Tailscale 用法；并非软件官方仓库。
- [Johnshall 懒人分组配置](https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever/blob/release/lazy_group.conf)：原生完整主配置和应用分组结构的参考。此处重新组织规则与默认值，没有直接照搬所有选项。
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)：远程分流与广告域名数据，版权及许可归原作者。
- [AdvertisingLite 文件说明](https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Shadowrocket/AdvertisingLite/README.md)：普通表和域名表的互补关系、误拦截说明及来源。
- [OpenAI ASN 误匹配反馈](https://github.com/blackmatrix7/ios_rule_script/issues/1384)：上游对非 AI 云服务器流量被归入 OpenAI 的问题记录。

这是一份按明确使用场景取舍的日常配置，不作“最强”“零误杀”“零重启”或固定内存保证。
