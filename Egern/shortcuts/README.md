# Egern VPN 开关快捷指令

目标：绑定 iPhone Action Button，在 Egern VPN 连接与断开之间切换。

使用系统「设置 VPN」动作，操作为「切换」（Toggle）。不使用文件或变量猜测开关状态，也不依赖 Egern 的 URL Scheme。

## 在 iPhone 设置

1. 先在 Egern 中启动过一次 VPN，并允许添加 VPN 配置，使系统能够选择该配置。
2. 导入 `Egern-VPN-Toggle.shortcut`，设置目标 VPN 时选择 **Egern**。不同设备的 VPN 标识不同，因此这里必须在目标 iPhone 上选择一次。
3. 如果导入时未出现选择界面，打开「Egern VPN 开关」的编辑页面，点「VPN」参数并选择 Egern；确认操作显示为「切换」，不是仅「连接」。
4. 先在快捷指令中运行一次，允许系统提示的相关权限。
5. iPhone「设置 → 操作按钮（Action Button）→ 快捷指令 → 选取快捷指令」，选择「Egern VPN 开关」。

完成后长按 Action Button，可按当前实际连接状态连接或断开 Egern VPN。

## 手动建立同样的快捷指令

在「快捷指令」中新建，添加一个「设置 VPN」动作，将操作改为「切换」，VPN 选择 Egern，再按上述第 5 步绑定即可。系统的设置 VPN 动作自 iOS 16.4 起提供。

## 构建

```sh
python3 Egern/shortcuts/build_toggle.py
shortcuts sign --mode anyone \
  --input Egern/shortcuts/Egern-VPN-Toggle.unsigned.shortcut \
  --output Egern/shortcuts/Egern-VPN-Toggle.shortcut
```

结构校验与签名不等于在 iPhone 上验证 VPN 切换。VPN 参数需在你的 iPhone 上选择，Action Button 也需在该设备设置。

来源：[Apple 设置 VPN 动作](https://support.apple.com/en-us/101583)、[Apple 为操作按钮设置快捷指令](https://support.apple.com/guide/shortcuts/run-shortcuts-with-the-action-button-apdfea15680b/ios)。
