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

## 隐私

公开仓库。策略与 LanRhyme 的 dotfiles 一致：**身份可以公开，凭据绝不入库**。

### 凭据的防护

**1. 白名单制** —— 只有 `manifest` 列出的路径才会进仓库，新装软件、浏览器数据、缓存默认都不在范围内，要显式 `dotfiles add`。

**2. 文件名拦截** —— 同步时按名字挡掉凭据文件，命中即跳过：

```
*.pem  *.key  *.kdbx  *.p12  *.pfx
id_rsa*  id_ed25519*  id_ecdsa*
*credentials*  *token*  *secret*  cookies*  *_history
```

同一套模式也写进了 `exclude`，目录整体同步时有第二道兜底。

**3. 内容扫描** —— `dotfiles commit` 自动跑，`.githooks/pre-commit` 让直接 `git commit` 也走同一套：

```bash
dotfiles scan
```

规则：密钥前缀（`sk-`/`ghp_`/`AIza`/`xox`/`github_pat_`）、私钥头、`"token": "…"` 这类键值、内网地址（10./192.168./172.16-31.）。命中即拒绝提交，确认安全可用 `DOTFILES_ALLOW_KEYS=1` 放行。

**4. 身份公开** —— 提交用真实邮箱（`SakoroYou <you2899047197@163.com>`），与 LanRhyme 的做法相同：他的 `dot_gitconfig` 和全部提交都用真实 foxmail 地址。所以 `.gitconfig` 是受控文件，里面只有名字、邮箱和 gh 的 credential helper 命令，没有 token 本体。

### 永不入库

| 类别 | 例子 |
|------|------|
| 凭据本体 | API key、token、cookie、`.pem`、`id_*` 私钥 |
| 设备私钥 | KDE Connect 证书、`~/.ssh` |
| 服务配置 | `frpc.toml`、`dufs/config.yaml`、`cloudflared` 凭据 |
| 账号 token | `gh/hosts.yml`、插件里存 token 的 `settings.json` |
| 运行时状态 | 缓存、索引库、`colors.json`、`cached_layouts`、日志 |
| 大二进制 | 字体、`.blend`、模型、安装包 |

### 克隆后启用钩子

```bash
git config core.hooksPath .githooks
```

## 远端
