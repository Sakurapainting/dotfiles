# dotfiles

CachyOS 桌面环境的个人配置集合，托管 niri、noctalia、fish、alacritty、fcitx5、fastfetch 等组件的配置与用户脚本。

仓库采用**白名单**方式管理：`home/` 目录镜像 `$HOME` 的相对路径，只有 `manifest` 中列出的路径会进入版本控制；通过 `dotfiles` 脚本在仓库与本机之间双向同步。

```
CachyOS · Wayland · niri · noctalia
46 个文件 · 216 KB · 18 条受管路径
```

## 特性

- **白名单托管** —— 新安装的软件、浏览器数据、缓存默认不进入仓库，需要显式登记
- **双向同步** —— `push` 抓取本机现状，`pull` 还原到本机，覆盖前自动备份
- **提交前扫描** —— 凭据文件名与文件内容双层拦截，命中即拒绝提交
- **零额外依赖** —— 同步器基于 bash + rsync + git，不引入框架或包管理器

## 目录结构

```text
dotfiles/
├── dotfiles          # 同步器：status / push / pull / add / scan / commit
├── manifest          # 受管路径清单，相对 $HOME，一行一条
├── exclude           # 同步排除模式：缓存、运行时产物、凭据
├── .githooks/        # pre-commit：调用 dotfiles scan
├── README.md
├── LICENSE
└── home/             # 镜像内容
    ├── .bashrc  .zshrc  .bash_profile  .xprofile  .gitconfig
    ├── .config/…
    └── .local/bin/…
```

## 受管范围

| 类别 | 路径 |
|------|------|
| Shell | `.bashrc` `.zshrc` `.bash_profile` `.xprofile` |
| Git | `.gitconfig` |
| 终端与编辑器 | `.config/alacritty` `.config/fish` `.config/micro/settings.json` |
| 桌面 | `.config/niri` `.config/noctalia` `.config/fastfetch` `.config/autostart` `.config/mimeapps.list` `.config/user-dirs.dirs` `.config/user-dirs.locale` |
| 输入法 | `.config/fcitx5` |
| 用户服务 | `.config/systemd/user` |
| 脚本 | `.local/bin` |

`~/.config` 总占用约 2.4 GB，其中绝大部分是浏览器缓存与索引数据库；实际纳入托管的配置约 216 KB。

## 使用

```bash
dotfiles status              # 本机与仓库的差异（= push 会抓取的内容）
dotfiles push                # 本机 → 仓库
dotfiles commit "说明"       # push + 扫描 + 本地提交
dotfiles pull                # 仓库 → 本机（覆盖前备份到 ~/.dotfiles-backup）
dotfiles pull --prune        # 同上，并删除本机多余的受管文件
dotfiles list                # 列出受管路径
dotfiles add .config/新目录  # 登记新路径
dotfiles scan                # 单独执行隐私扫描
dotfiles rollback [路径]     # 丢弃未提交改动，恢复到最近一次提交
dotfiles log                 # 最近提交
```

典型流程：修改配置 → 使其生效 → `dotfiles commit "…"` → `git push`。

`dotfiles` 通过 `~/.local/bin/dotfiles` 暴露，等价于直接执行 `~/dotfiles/dotfiles`。该脚本会随 `pull` 一起还原，因此新机器上无需额外安装。

## 工作机制

**同步方向。** 两条命令互为逆向操作，均以 `home/` 为镜像根：`push` 把本机内容写入仓库，`pull` 把仓库内容写回本机。目录使用 `rsync -a` 递归同步，单文件使用 `cp -p`，权限位保持原样。

**差异判定。** `status` 使用 `--checksum` 比较文件内容而非修改时间，避免 `git checkout` 造成的 mtime 变化被误报为改动。

**排除规则。** `exclude` 中的模式对每个受管根目录生效，用于挡掉运行时产物（`colors.json`、`cached_layouts`、日志）与凭据文件。被排除的文件不参与同步，也不会因 `--prune` 被删除。

**备份。** `pull` 在覆盖前把受影响路径复制到 `~/.dotfiles-backup/<时间戳>/`，仅备份真正发生变化的路径，保留最近 20 次。

**回档。** `rollback` 先丢弃仓库内未提交的改动，再把最近一次提交还原到本机，全程仍会备份被覆盖的文件。支持单路径回退，例如 `dotfiles rollback .local/state/noctalia/settings.toml`。

**生效方式。** niri 配置改动后执行：

```bash
niri validate && niri msg action load-config-file
```

alacritty 支持热重载；fcitx5 主题变更后可执行 `fcitx5-remote -e` 重启输入法。

## 隐私与安全

仓库为公开仓库，凭据不进入版本控制。

**1. 白名单制** —— 仅 `manifest` 列出的路径参与同步，其余内容不会被读取或提交。

**2. 文件名拦截** —— 同步时跳过以下模式，`push` 与 `pull` 均生效：

```
*.pem  *.key  *.kdbx  *.p12  *.pfx
id_rsa*  id_ed25519*  id_ecdsa*
*credentials*  *token*  *secret*  cookies*  *_history
```

同一组模式同时写入 `exclude`，目录整体同步时作为第二道兜底。

**3. 内容扫描** —— `dotfiles commit` 自动执行，`.githooks/pre-commit` 使 `git commit` 走同一套检查：

| 规则 | 说明 |
|------|------|
| 密钥前缀 | `sk-`、`ghp_`/`gho_`/`ghu_`/`ghs_`、`github_pat_`、`AIza`、`xox*` |
| 私钥头 | `-----BEGIN … PRIVATE KEY-----` |
| 键值形态 | `"token": "…"`、`"secret": "…"`、`"password": "…"` |
| 内网地址 | `10.`、`192.168.`、`172.16-31.` 网段 |

命中时中止提交并列出命中行；确认无风险后可设置 `DOTFILES_ALLOW_KEYS=1` 放行。

**4. 永不入库**

| 类别 | 示例 |
|------|------|
| 凭据本体 | API key、token、cookie、`.pem`、`id_*` 私钥 |
| 设备私钥 | KDE Connect 证书、`~/.ssh` |
| 服务配置 | `frpc.toml`、`dufs/config.yaml`、`cloudflared` 凭据 |
| 账号数据 | `gh/hosts.yml`、插件中存放 token 的 `settings.json` |
| 运行时状态 | 缓存、索引库、生成的主题色、日志 |
| 大体积二进制 | 字体、`.blend`、模型、安装包 |

`.gitconfig` 受版本控制，内容为用户名、邮箱与 credential helper 命令，不含 token 本体；提交作者信息属于公开信息。

## 换机恢复

```bash
paru -S git rsync
git clone https://github.com/Sakurapainting/dotfiles ~/dotfiles
~/dotfiles/dotfiles pull
git -C ~/dotfiles config core.hooksPath .githooks

# 桌面环境依赖
paru -S niri noctalia fish alacritty fcitx5-rime fastfetch
```

`pull` 会还原 `~/.local/bin`，其中包括 `dotfiles` 本身；随后执行一次 `niri validate` 确认配置可用。硬件相关设置（显示器名称、刷新率、输入设备）需按目标机器调整 `.config/niri/cfg/display.kdl` 与 `input.kdl`。

## 扩展

登记新路径：

```bash
dotfiles add .config/btop
dotfiles push
dotfiles commit "chore: 纳入 btop 配置"
```

停止托管：从 `manifest` 删除对应行，本机文件不受影响，仓库副本在下次提交时移除。

## 环境要求

| 组件 | 用途 |
|------|------|
| `git`、`rsync` | 版本控制与同步 |
| `bash` | 同步器 |
| `niri`、`noctalia` | 受管配置对应的桌面环境 |
| `python3` | 辅助脚本（输入法主题、颜色生成等） |
| `gh`（可选） | 推送时提供 GitHub 凭据，可省略 |

## 许可证

[MIT](LICENSE)
