# Egern 配置迁移

本目录将仓库根目录的 `Loon_custom.lcf` 转为 Egern YAML。转换日期：2026-11-16（Asia/Taipei）。通用设置、DNS 和真实 IP 域名已按用户后续提供的文本完整覆盖，并启用用户指定的 14 个模块。原 Loon 插件的逐项等价迁移状态仍记录在 `plugin-status.md`。

## 导入

配置地址：

```text
https://raw.githubusercontent.com/hengruili2000/Loon_Rule/main/Egern/Egern_custom.yaml
```

1. 在 Egern 中新建配置，通过上面的 URL 导入。
2. 在「节点订阅」组的 `urls` 中添加自己的订阅，或导入节点到该组。原 Loon 模板没有任何订阅或节点凭据，本配置也没有。
3. 更新订阅后，在各地区「手动策略」中选择节点，再检查「默认代理」及各服务分组。「节点订阅」内的 REJECT 是空订阅占位策略，地区组过滤器会排除它；未添加订阅前，代理分组没有可用节点。
4. 使用支持 `conditional` 和 `flatten` 的当前 Egern 版本。若订阅无法解析，需要让订阅源输出 Egern 支持的节点格式。已启用 Sub-Store 模块，但仍需自行配置订阅或合集地址；仅安装模块不会自动向「节点订阅」填入节点。
5. HTTPS 重写/去广告模块需要在 Egern 中生成、安装并信任证书。模块链接可下载不代表对应 App 的脚本功能已通过测试。

## 用户提供的通用设置与 DNS

`sources/user-settings.yaml` 保存用户提供的设置及后续授权的 ChinaMax DNS 补全。生成配置时直接保留该段的内容与注释。

- HTTP/SOCKS 端口为 3080/3090，`vif_only: true`、`block_quic: true`、`hijack_dns: ['*:53']`，保留用户指定的路由排除列表和 10.7.0.1 回环地址。
- GeoIP 覆盖为用户指定的 Loyalsoldier Country.mmdb。
- DNS 使用用户的 6 组上游、阻断 IP 列表及其他参数；后续增加 2 条 ChinaMax DNS 补全规则，现共 66 条。原 Loon 的 Host 映射与 `PHICOMM_5G` DNS 转发不再合入；策略组中的 SSID 直连条件仍保留。
- `real_ip_domains` 完整替换为用户提供的 34 项。
- 用户明确选择保留 `proxy_nameservers: [ProxyDNS]` 和 Clash `reject.txt` 链接，因此没有将组名展开为服务器地址，也没有转换广告规则格式。这两处与当前官方 DNS 文档列举的写法/资源格式存在差异，未验证客户端能否按预期处理。[官方 DNS 文档](https://egernapp.com/docs/configuration/dns/)
- `vif_hairpin_addresses` 和用户给出的其他原值均保留；本次 YAML 校验不等于 Egern 完整 schema 校验。
- 原文中关于 DNS 强制走代理、代理服务器域名解析及 AdBlock.yaml 的说明也按要求保留。Egern 官方文档描述的上游连接路径取决于 DNS 类型及路由规则，配置中的注释不会单独建立代理路由；也没有因注释自动新增 AdBlock.yaml 分流规则。

### 国内域名落入境外 DNS 的修正

用户反馈 `static.mokahr.com` 和 `sns-v14.rednotecdn.com` 在 Egern 开启后解析到偏海外的地址。两者分别命中 ChinaMax 的 `.mokahr.com` 和 `.rednotecdn.com`，流量走 DIRECT；此前的 DNS 国内名单却没有覆盖它们，因而落入 Google/Cloudflare 的 Default 上游。

本次直接复用现有流量分流的 `ChinaMax.list`、`ChinaMax_Domain.list` 两个远程源，通过 DNS `proxy_rule_set` 指向 DNSPod。客户端每 28800 秒（8 小时）更新，与流量规则使用同源数据，无需单独维护国内域名快照。混合规则源中的域名条件用于 DNS 匹配；这不意味着 IP/ASN/UA 条件能将未知域名判定为国内域名。

两条规则放在现有明确服务分流、本地保留域名处理和 Google DNS 规则之后，在 `.cn` 和 `* → Default` 之前。已有 64 条规则的相对顺序未改，保留先命中的服务例外；这次没有把所有 DIRECT 服务一概改用国内 DNS。

更新客户端配置后，确认两份 ChinaMax DNS 规则下载成功，再清理 DNS 缓存并重连 Egern。对反馈的两个域名，预期 DNS 日志命中新增 ChinaMax DNS 规则、上游为 DNSPod。实际 CDN 地址和地域仍由 DNS 服务与站点决定，本次未进行设备实测。

## 用户指定的 14 个模块

`sources/user-modules.yaml` 保存去除粘贴转义后的标准 YAML；模块 URL、顺序、启用状态、更新间隔、env 均按用户提供的值写入。

| 模块 | 更新间隔（秒） |
| --- | --- |
| 常用小组件 | 86400 |
| Sub-Store | 259200 |
| BoxJs | 259200 |
| Script Hub | 259200 |
| WeatherKit | 259200 |
| skip-proxy-lists.sgmodule（原文未指定 name） | 未指定，使用客户端默认值 |
| 雪球去广告 | 86400 |
| 综合电商去广告 | 86400 |
| 地图三合一去广告 | 86400 |
| 差旅出行去广告 | 86400 |
| 音乐流媒体去广告 | 604800 |
| 视频流媒体去广告 | 86400 |
| 京东比价 | 86400 |
| App开屏广告跳过 | 86400 |

小组件参数为 `TEACHING_WEEK_START: 2026/08/31`、`EXCLUSIVE_NAME_2: 寒假`、`EXCLUSIVE_DATE_2: 01/23`。模块自身合并的规则、MITM 域名、绕过列表或 real-IP 域名可能影响实际运行配置；模块文件内容没有在本仓库重新改写。链接检查记录见 `user-resource-checks.json`。

## 保留的行为

- 原有 27 个策略组保留名称、选项顺序和图标；新增「节点订阅」统一承接订阅和本地节点。
- 服务分流、TruthSocial/自定义美国规则的美国策略、Apple 服务默认 DIRECT、漏网之鱼默认 DIRECT 均保留。
- 7 个地区场景在 `PHICOMM_5G` 下使用 DIRECT，其他 Wi-Fi 和蜂窝网络使用对应地区手动策略。此条件仅作用于原场景组，没有将整机流量改成 SSID 直连。
- 原绕过列表及策略切换时断开旧连接的设置保留。DNS、端口、路由排除和真实 IP 域名以用户的新设置为准。
- STUN 通过协议拒绝规则处理。DNS 上游的调度、缓存和失败处理由 Egern 实现，不承诺与 Loon 的内部行为相同。
- 所有非 FINAL 本地规则在前，远程规则按原顺序放在其后，默认规则在最后。原远程 Apple 两个列表没有扩充，也没有新增单独的 YouTube 分组。

## 已批准的规则替换

原可莉 6 项分流资源在本次转换环境中均返回 HTTP 403，无法读取原内容。经用户确认后替换为 blackmatrix7 的同名或对应 Surge 规则，属于来源替换，不保证与原列表逐条一致。

| 原标签 | 替代服务 | 转换方式 |
| --- | --- | --- |
| TikTok | TikTok | 内嵌 Egern 规则 |
| Netflix | Netflix | 内嵌 Egern 规则 |
| Spotify | Spotify | 内嵌 Egern 规则 |
| LAN | Lan | 内嵌 Egern 规则 |
| CN REGION | China | 内嵌 Egern 规则，保留原位置 |
| Speedtest Intl | Speedtest | 逻辑条件：命中 Speedtest 且不命中 China、ChinaMax、ChinaMax_Domain |

Speedtest 的国内排除只约束该服务规则，不提升整份配置中 China 规则的优先级。排除基于这三个列表当时能匹配的域名、UA 和已知 IP，并不代表能识别所有国内测速服务器。未收录的服务器仍可能命中 Speedtest 关键词规则。

45 个原规则资源继续通过原 URL 加载，每 8 小时更新。Anthropic、Category-Dev 以及批准替换的 6 项使用下载快照生成本地 YAML 条目；这些内嵌条目需要重新运行转换脚本才会更新，本次未设置自动更新任务。Speedtest 的 China 排除列表仍远程更新。

## 兼容差异及未迁移项目

- Category-Dev 的 AWS ECR `AND/NOT/DOMAIN-WILDCARD` 条件已显式转换，避免旧转换器静默丢弃该条件。
- 8 条 PROCESS-NAME 规则没有迁移：Anthropic 中 5 条，替代的 TikTok、Netflix、Spotify 中各 1 条。Egern 当前文档的规则类型不包含进程匹配；相应服务的域名/IP 规则仍保留。具体条目见 `conversion-report.json`。
- 初始 28 个可莉 Loon 插件没有根据其原文自动转换：原资源在初次迁移环境返回 403。后续用户指定的 14 个模块已单独启用，其中部分功能与原插件重叠，但未证明逐项等价。历史清单、原启用状态及绑定策略见 `plugin-status.md` 和报告。
- 原可莉 GeoIP/ASN 下载返回 403；现按用户指定覆盖为 Loyalsoldier GeoIP，ASN 未设置自定义下载地址。数据库内容可能与原 Loon 版本不同。
- `sni-sniffing`、`dns-reject-mode`、`domain-reject-mode`、`udp-fallback-mode`、`interface-mode`、全局 `test-timeout` 和 `resource-parser` 未找到直接对应的已文档化配置项，因此未伪造等价字段。STUN 拒绝规则也不能代替 Loon 对所有 UDP 失败连接的 REJECT 回退语义。
- 本地 CIDR 中带主机位的地址已规范化，例如 `28.0.0.1/8` → `28.0.0.0/8`，实际网络范围不变。
- 原文件无 MITM CA，本配置未嵌入证书。已添加的 HTTPS 重写模块仍需要在 Egern 中生成、安装并信任证书，并单独验证脚本。

## 维护与验证

需要 Python 3、Ruby（含标准库 Psych/YAML）及 curl，无第三方 Python 依赖。在仓库根目录运行：

```sh
python3 Egern/scripts/fetch_sources.py
python3 Egern/scripts/convert.py
python3 Egern/scripts/validate.py
```

`sources/Loon_custom.lcf` 是初始 Loon 输入，原 Git blob 为 `a1a224ed582cb5b94ece3a420440f6ef8f533d2f`。更新 Loon 输入时也需更新脚本中的来源版本及相应验证。后续通用设置和模块分别以 `sources/user-settings.yaml`、`sources/user-modules.yaml` 为准，重新生成时不会丢失。`sources/resources.json` 记录初始规则下载地址和 SHA-256，下载缓存 `sources/resources/` 不进入 Git。

已通过 YAML 解析、策略引用与循环检查、53 项原远程规则迁移计数、SSID 场景、默认规则位置、过滤表达式、CIDR 规范化和逻辑条件结构检查；16 个顶层设置与当前设置源一致，66 条 DNS 规则及 14 项模块匹配。新增校验覆盖两份 DNS 源与 DIRECT 源一致、补全规则优先级、两个反馈域名匹配及域名后缀边界。原服务分组、分流规则与默认策略保持不变。初次迁移时另使用 Egern 官方网站的 WebAssembly 转换器检查了 45 个保留远程分流源，见 `official-converter-check.json`。这不是 Egern 完整配置 schema 验证，也没有在实际 Egern 客户端进行导入、连接或脚本功能测试。

原规则资源仍可能受未来更新、网络访问和客户端版本影响；导入后应检查规则下载状态和实际命中日志。

## 来源与署名

- [原 Loon 配置](https://github.com/hengruili2000/Loon_Rule/blob/main/Loon_custom.lcf)，保留原文件中的 iKeLee 署名。
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，替代规则来源；完整来源 URL 记录在报告和资源清单。
- [Egern 配置示例](https://egernapp.com/docs/configuration/example/)、[策略组](https://egernapp.com/docs/configuration/policy_groups/)、[规则](https://egernapp.com/docs/configuration/rules/)、[DNS](https://egernapp.com/docs/configuration/dns/)、[模块兼容说明](https://egernapp.com/docs/faq/)、[官方格式转换器](https://gen.egernapp.com/)。
