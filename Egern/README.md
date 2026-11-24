# Egern 配置迁移

本目录将仓库根目录的 `Loon_custom.lcf` 转为 Egern YAML。转换日期：2026-11-16（Asia/Taipei）。使用用户指定的通用设置和真实 IP 域名，启用 14 个模块，并从流量规则派生 DNS 分流。不兼容的远程规则由 GitHub Actions 每 24 小时转换成独立远程产物，主配置不再内嵌这些上游规则。原 Loon 插件的逐项等价迁移状态仍记录在 `plugin-status.md`。

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

## Action Button 切换 Egern VPN

已提供签名的 [Egern VPN 开关快捷指令](shortcuts/Egern-VPN-Toggle.shortcut)。导入后选择目标 iPhone 上的 Egern VPN，再将它绑定到「设置 → 操作按钮 → 快捷指令」。指令使用系统「设置 VPN → 切换」动作，完整说明见 [shortcuts/README.md](shortcuts/README.md)。尚未在 iPhone 上实测。

## 用户提供的通用设置与 DNS

`sources/user-settings.yaml` 保存用户提供的设置及后续授权的 ChinaMax DNS 补全。生成配置时直接保留该段的内容与注释。

- HTTP/SOCKS 端口为 3080/3090，`vif_only: true`、`block_quic: true`、`hijack_dns: ['*:53']`，保留用户指定的路由排除列表和 10.7.0.1 回环地址。
- GeoIP 覆盖为用户指定的 Loyalsoldier Country.mmdb。
- `real_ip_domains` 保留用户提供的 34 项。原 Loon 的 Host 映射和 `PHICOMM_5G` DNS 转发未合入。

### DNS 分流

- `convert.py` 按流量规则顺序生成 DNS 域名规则，并复用远程规则集 URL 和更新间隔。明确走 `DIRECT` 的规则，以及默认选择 `DIRECT` 的 Apple 服务和漏网之鱼，使用 DNSPod。代理规则使用 Google 和 Cloudflare 的 HTTPS DNS。Apple TV 仍先于 Apple 服务匹配，两份 ChinaMax 规则继续覆盖 `static.mokahr.com` 和 `sns-v14.rednotecdn.com`。
- DNSPod 的 HTTPS 连接显式直连。Google 和 Cloudflare 的 DoH 主机名在 443 端口上使用「默认代理」，上游主机名由 Bootstrap 解析。家庭 Wi-Fi `ASUS_C8_5G` 命中 SSID 规则时使用系统 DNS。
- `lan` 和 `home.arpa` 使用系统 DNS。广告和保留域名继续按配置拒绝。Egern 强制内部 Proxy DNS 直连，因此 `proxy_nameservers` 显式使用 DNSPod；用户流量的 DNS 使用上述分流。
- DNS 查询阶段无法获知策略组选项的手动变更、目标 IP、协议或 User-Agent。Speedtest 在其他域名规则之后匹配，给国内规则优先权。依赖这些条件的流量和 DNS 命中结果可能不同。[Egern DNS 文档](https://egernapp.com/zh-CN/docs/configuration/dns/)

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
- 7 个地区场景的 SSID 匹配统一为 `ASUS_C8_5G`：连接该 Wi-Fi 时使用 DIRECT，其他 Wi-Fi 和蜂窝网络使用对应地区手动策略。生成器保存此覆盖设置；初始 Loon 输入快照保持原样。
- 原绕过列表及策略切换时断开旧连接的设置保留。DNS、端口、路由排除和真实 IP 域名以用户的新设置为准。
- STUN 通过协议拒绝规则处理。DNS 上游的调度、缓存和失败处理由 Egern 实现，不承诺与 Loon 的内部行为相同。
- 所有非 FINAL 本地规则在前，远程规则按原顺序放在其后，默认规则在最后。原远程 Apple 两个列表没有扩充，也没有新增单独的 YouTube 分组。

## 已批准的规则替换

原可莉 6 项分流资源在本次转换环境中均返回 HTTP 403，无法读取原内容。经用户确认后替换为 blackmatrix7 的同名或对应 Surge 规则，属于来源替换，不保证与原列表逐条一致。

| 原标签 | 替代服务 | 转换方式 |
| --- | --- | --- |
| TikTok | TikTok | 远程 `rules/TikTok.yaml` |
| Netflix | Netflix | 远程 `rules/Netflix.yaml` |
| Spotify | Spotify | 远程 `rules/Spotify.yaml` |
| LAN | Lan | 远程 `rules/LAN.yaml` |
| CN REGION | China | 远程 `rules/China.yaml`，保留原位置 |
| Speedtest Intl | Speedtest | 远程 `rules/Speedtest.yaml`，主配置保留 NOT China/ChinaMax/ChinaMax_Domain 条件 |

Speedtest 的国内排除只约束该服务规则，不提升整份配置中 China 规则的优先级。排除基于这三个列表当时能匹配的域名、UA 和已知 IP，并不代表能识别所有国内测速服务器。未收录的服务器仍可能命中 Speedtest 关键词规则。

45 个原规则资源继续通过原 URL 加载，每 8 小时更新。Anthropic、Category-Dev 和上述 6 项共 8 份资源改由每日工作流转换并发布，主配置只保留远程 URL。Speedtest 的服务匹配数据也在远程产物中，配置中仅保留组合匹配关系。

## 远程规则每天自动转换

- 工作流：[sync-egern-rules.yml](../.github/workflows/sync-egern-rules.yml)。每天台北时间 **04:23**（UTC 20:23）执行一次，同时支持手动运行及转换代码/源清单变更后的自动运行。
- 上游和产物映射：`sources/remote-rules.json`。产物为 `rules/Anthropic.yaml`、`rules/Category-Dev.yaml`、`rules/TikTok.yaml`、`rules/Netflix.yaml`、`rules/Spotify.yaml`、`rules/LAN.yaml`、`rules/China.yaml`、`rules/Speedtest.yaml`。
- 主配置使用 `https://raw.githubusercontent.com/hengruili2000/Loon_Rule/main/Egern/rules/<名称>.yaml` 引用这些产物，客户端每 86400 秒拉取一次。流量规则和 DNS 分流引用相同的远程产物。
- 转换先下载并验证全部 8 个上游，再更新产物。遇到下载失败、未知语法、无法等价转换的逻辑或混合 no-resolve 语义时，工作流失败，不发布新产物，保留仓库中最后一次有效版本。上游没有变化时不创建无意义提交。
- `rules/sync-report.json` 随每日工作流更新，记录每项上游 URL、内容哈希、转换条目数、排除项和逻辑转换信息。`conversion-report.json` 保存生成主配置时的记录。校验用同步报告核对当前产物的规则计数，允许上游排除项随同步变化。
- 原上游的署名及许可注释保留在转换产物中。仍不支持的 PROCESS-NAME 条目明确记录在同步报告里，不伪造等价规则。
- 复杂的域名 AND/OR/NOT 表达式由通用转换器解析并生成等价的锚定域名正则，不把特定上游的规则内容硬编码在主配置或脚本中。AWS ECR 的正反条件已做匹配回归测试。

## 兼容差异及未迁移项目

- Category-Dev 的 AWS ECR `AND/NOT/DOMAIN-WILDCARD` 条件由每日转换器转为等价域名正则，保存在独立远程产物中。
- 生成主配置时有 8 条 PROCESS-NAME 规则未迁移，Anthropic 中有 5 条，替代的 TikTok、Netflix、Spotify 中各有 1 条。Egern 当前文档的规则类型不包含进程匹配，相应服务的域名和 IP 规则仍保留。最新条目见 `rules/sync-report.json`。
- 初始 28 个可莉 Loon 插件没有根据其原文自动转换：原资源在初次迁移环境返回 403。后续用户指定的 14 个模块已单独启用，其中部分功能与原插件重叠，但未证明逐项等价。历史清单、原启用状态及绑定策略见 `plugin-status.md` 和报告。
- 原可莉 GeoIP/ASN 下载返回 403；现按用户指定覆盖为 Loyalsoldier GeoIP，ASN 未设置自定义下载地址。数据库内容可能与原 Loon 版本不同。
- `sni-sniffing`、`dns-reject-mode`、`domain-reject-mode`、`udp-fallback-mode`、`interface-mode`、全局 `test-timeout` 和 `resource-parser` 未找到直接对应的已文档化配置项，因此未伪造等价字段。STUN 拒绝规则也不能代替 Loon 对所有 UDP 失败连接的 REJECT 回退语义。
- 本地 CIDR 中带主机位的地址已规范化，例如 `28.0.0.1/8` → `28.0.0.0/8`，实际网络范围不变。
- 原文件无 MITM CA，本配置未嵌入证书。已添加的 HTTPS 重写模块仍需要在 Egern 中生成、安装并信任证书，并单独验证脚本。

## 维护与验证

需要 Python 3、Ruby（含标准库 Psych/YAML）及 curl，无第三方 Python 依赖。在仓库根目录运行：

```sh
python3 Egern/scripts/fetch_sources.py
python3 Egern/scripts/sync_remote_rules.py
python3 Egern/scripts/convert.py
python3 Egern/scripts/test_remote_rules.py
python3 Egern/scripts/validate.py
```

`sources/Loon_custom.lcf` 是初始 Loon 输入，原 Git blob 为 `a1a224ed582cb5b94ece3a420440f6ef8f533d2f`。更新 Loon 输入时也需更新脚本中的来源版本及相应验证。后续通用设置和模块分别以 `sources/user-settings.yaml`、`sources/user-modules.yaml` 为准，重新生成时不会丢失。`sources/resources.json` 记录初始规则下载地址和 SHA-256，下载缓存 `sources/resources/` 不进入 Git。

日常同步不需要重新生成主配置：工作流只执行 `sync_remote_rules.py` 和 `test_remote_rules.py`，更新 `Egern/rules/`。只有策略/配置结构发生变化时才需要运行主配置生成器。

校验脚本检查 YAML、策略引用和循环、53 项远程规则的迁移计数、SSID 场景、默认规则位置、过滤表达式、CIDR 和逻辑条件。DNS 检查覆盖规则生成顺序、DoH 连接策略、Apple TV 与 Apple 服务优先级、ChinaMax 和兜底。另有转换器回归检查验证规则等价性、计数、产物哈希和失败时保留旧产物。初次迁移时使用 Egern 官方网站的 WebAssembly 转换器检查了 45 个保留远程流量规则源，见 `official-converter-check.json`。客户端导入、DNS 上游连接和规则命中仍需设备实测。

原规则资源仍可能受未来更新、网络访问和客户端版本影响；导入后应检查规则下载状态和实际命中日志。

## 来源与署名

- [原 Loon 配置](https://github.com/hengruili2000/Loon_Rule/blob/main/Loon_custom.lcf)，保留原文件中的 iKeLee 署名。
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，替代规则来源；完整来源 URL 记录在报告和资源清单。
- [Egern 配置示例](https://egernapp.com/docs/configuration/example/)、[策略组](https://egernapp.com/docs/configuration/policy_groups/)、[规则](https://egernapp.com/docs/configuration/rules/)、[DNS](https://egernapp.com/docs/configuration/dns/)、[模块兼容说明](https://egernapp.com/docs/faq/)、[官方格式转换器](https://gen.egernapp.com/)。
