# Egern 配置迁移

本目录将仓库根目录的 `Loon_custom.lcf` 转为 Egern YAML。转换日期：2026-11-16（Asia/Taipei）。这是分流、策略组和 DNS 的迁移版本；原有 28 个 Loon 插件尚未迁移，不能视为插件功能完全等价的配置。

## 导入

配置地址：

```text
https://raw.githubusercontent.com/hengruili2000/Loon_Rule/main/Egern/Egern_custom.yaml
```

1. 在 Egern 中新建配置，通过上面的 URL 导入。
2. 在「节点订阅」组的 `urls` 中添加自己的订阅，或导入节点到该组。原 Loon 模板没有任何订阅或节点凭据，本配置也没有。
3. 更新订阅后，在各地区「手动策略」中选择节点，再检查「默认代理」及各服务分组。「节点订阅」内的 REJECT 是空订阅占位策略，地区组过滤器会排除它；未添加订阅前，代理分组没有可用节点。
4. 使用支持 `conditional`、`flatten` 和 DNS `ssid` 条件的当前 Egern 版本。若订阅无法解析，需要让订阅源输出 Egern 支持的节点格式；原 Loon 的 Sub-Store resource-parser 不会在 Egern 执行。

## 保留的行为

- 原有 27 个策略组保留名称、选项顺序和图标；新增「节点订阅」统一承接订阅和本地节点。
- 服务分流、TruthSocial/自定义美国规则的美国策略、Apple 服务默认 DIRECT、漏网之鱼默认 DIRECT 均保留。
- 7 个地区场景在 `PHICOMM_5G` 下使用 DIRECT，其他 Wi-Fi 和蜂窝网络使用对应地区手动策略。此条件仅作用于原场景组，没有将整机流量改成 SSID 直连。
- 保留原来的 DNS/DoH、按域名指定 DNS、Host IP/别名、real-IP 域名、绕过列表、端口和策略切换时断开旧连接的设置。SSID DNS 条件按原顺序优先使用 10.0.0.1。
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
- 28 个可莉 Loon 插件未启用、未改写成 Egern 模块：原资源在本次环境返回 403，无法验证内容与脚本 API 兼容性。`modules: []` 表示尚未迁移，不表示功能已由 Egern 接管。完整清单、原启用状态及原绑定策略见 `plugin-status.md` 和报告。
- 原自定义 GeoIP/ASN 下载也返回 403，本配置没有覆盖 Egern 的数据库设置。数据库内容可能与 Loon 使用的版本不同。
- `sni-sniffing`、`dns-reject-mode`、`domain-reject-mode`、`udp-fallback-mode`、`interface-mode`、全局 `test-timeout` 和 `resource-parser` 未找到直接对应的已文档化配置项，因此未伪造等价字段。STUN 拒绝规则也不能代替 Loon 对所有 UDP 失败连接的 REJECT 回退语义。
- 本地 CIDR 中带主机位的地址已规范化，例如 `28.0.0.1/8` → `28.0.0.0/8`，实际网络范围不变。
- 原文件无 MITM CA，本配置未嵌入证书。以后添加 HTTPS 重写模块时，需要在 Egern 中生成、安装并信任证书，并单独验证脚本。

## 维护与验证

需要 Python 3、Ruby（含标准库 Psych/YAML）及 curl，无第三方 Python 依赖。在仓库根目录运行：

```sh
python3 Egern/scripts/fetch_sources.py
python3 Egern/scripts/convert.py
python3 Egern/scripts/validate.py
```

`sources/Loon_custom.lcf` 是本次转换的精确输入，原 Git blob 为 `a1a224ed582cb5b94ece3a420440f6ef8f533d2f`。更新 Loon 输入时也需更新脚本中的来源版本及相应验证。`sources/resources.json` 记录下载地址和 SHA-256，下载缓存 `sources/resources/` 不进入 Git。

已通过 YAML 解析、策略引用与循环检查、53 项远程规则迁移计数、SSID 场景、DNS 优先级、默认规则位置、过滤表达式、CIDR 规范化和逻辑条件结构检查。另使用 Egern 官方网站的 WebAssembly 转换器确认了 45 个保留远程源的格式可解析，结果见 `official-converter-check.json`。这不是 Egern 完整配置 schema 验证，也没有在实际 Egern 客户端进行导入、连接或脚本功能测试。

原规则资源仍可能受未来更新、网络访问和客户端版本影响；导入后应检查规则下载状态和实际命中日志。

## 来源与署名

- [原 Loon 配置](https://github.com/hengruili2000/Loon_Rule/blob/main/Loon_custom.lcf)，保留原文件中的 iKeLee 署名。
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，替代规则来源；完整来源 URL 记录在报告和资源清单。
- [Egern 配置示例](https://egernapp.com/docs/configuration/example/)、[策略组](https://egernapp.com/docs/configuration/policy_groups/)、[规则](https://egernapp.com/docs/configuration/rules/)、[DNS](https://egernapp.com/docs/configuration/dns/)、[模块兼容说明](https://egernapp.com/docs/faq/)、[官方格式转换器](https://gen.egernapp.com/)。
