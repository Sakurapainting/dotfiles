# dotfiles

本机（CachyOS + niri + noctalia）的个人配置仓库。白名单式托管，`home/` 镜像 `$HOME` 的相对路径。

## 结构

```
dotfiles/
├── dotfiles          # 同步器（status / push / pull / add / commit）
├── manifest          # 受管路径清单，一行一个，相对 $HOME
├── exclude           # rsync 排除模式（缓存、生成物、日志）
└── home/             # 镜像内容
    ├── .bashrc .zshrc .bash_profile .xprofile
    ├── .config/{niri,noctalia,alacritty,fish,fcitx5,fastfetch,systemd/user,…}
    └── .local/bin/
```

仓库只有 ~200 KB / 40 来个文件，因为只收手写的配置和脚本；浏览器缓存、索引数据库、密钥都在外面。

## 日常用法

```bash
dotfiles status              # 本机改了什么（= push 会抓到什么）
dotfiles push                # 本机 → 仓库
dotfiles commit "改了什么"   # push + 密钥扫描 + git 提交
dotfiles pull                # 仓库 → 本机（覆盖前备份到 ~/.dotfiles-backup/<时间>/）
dotfiles pull --prune        # 同上，并删除本机多余的受管文件
dotfiles list                # 列出受管路径
dotfiles add .config/新应用  # 纳入新路径
dotfiles log                 # 最近提交
```

典型循环：改配置 → 生效 → `dotfiles commit "..."`。

`dotfiles` 命令来自 `~/.local/bin/dotfiles`（薄封装，指向本仓库），所以任意目录可用。直接跑 `~/dotfiles/dotfiles` 等价。

## 加一个新的配置

```bash
dotfiles add .config/btop   # 追加进 manifest
dotfiles push
dotfiles commit "chore: 纳入 btop 配置"
```

想停止托管：从 `manifest` 删掉那一行即可，本机文件不受影响（仓库里的副本下次提交会消失）。

## 换机恢复

```bash
git clone <远端> ~/dotfiles
~/dotfiles/dotfiles pull
# 依赖另装：paru -S niri noctalia fish alacritty fcitx5-rime fastfetch …
```

`pull` 会先备份被覆盖的文件，误操作可以从 `~/.dotfiles-backup/` 取回。

## 设计取舍

- **白名单而非整目录**：`~/.config` 实际 2.4 GB，九成是缓存；按路径收，新装软件不会自动污染仓库
- **拷贝而非符号链接**：避免应用把运行时状态写进仓库，也不受"仓库移动就全断"影响
- **双向都有命令**：`push` 抓现场，`pull` 还现场；没有"仓库是唯一真相"的教条，谁新就听谁的
- **提交前扫密钥**：`sk-`、`ghp_`、`AIza`、私钥头、`"token": "…"` 命中即拒绝提交（`DOTFILES_ALLOW_KEYS=1` 可强制）
- **不纳入**：浏览器数据、`~/.cache`、密钥与私钥、字体与二进制、显示器名/绝对路径这类机器相关项

## 提交前隐私检查

仓库是公开的，所以提交链路上有两道闸：

1. `dotfiles commit` 会自动跑扫描
2. `.githooks/pre-commit` 拦截直接 `git commit`

扫描规则：常见密钥前缀（`sk-`/`ghp_`/`AIza`/`xox`）、私钥头、`"token": "…"`、个人邮箱域（163/126/qq/gmail/outlook/foxmail）、私网地址（10./192.168./172.16-31.）。

克隆到新机器后启用自己的 hook：

```bash
git config core.hooksPath .githooks
```

手动检查：

```bash
dotfiles scan
```

## 远端

目前只有本地历史，没有 remote。要推到 GitHub：

```bash
gh repo create dotfiles --private --source ~/dotfiles --remote origin --push
```

建议私有仓库——配置里难免出现家用路径、内网地址、代理端口。
