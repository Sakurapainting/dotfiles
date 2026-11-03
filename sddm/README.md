# SDDM

`morandi-dark/` 是本机使用的莫兰迪暗色 SDDM 登录主题源码、背景图和启用配置。它属于系统级配置，因此放在仓库根目录的 `sddm/`，不参与 `home/` 镜像和 `manifest` 同步。

在新机器上还原后，运行：

```bash
sudo ./sddm/morandi-dark/install-system.sh ./sddm/morandi-dark
```

脚本会安装主题到 `/usr/share/sddm/themes/morandi-dark/`，并将仓库里的 `99-morandi-dark.conf` 安装到 `/etc/sddm.conf.d/`。它不会重启当前 SDDM 会话，主题在下次进入登录界面时生效。

脚本默认拒绝覆盖已有主题或配置，避免误覆盖本机修改；需要更新时先备份并移除旧的系统副本，再重新运行脚本。
