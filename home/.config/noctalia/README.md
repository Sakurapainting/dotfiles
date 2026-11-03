# 莫兰迪全局配色引擎（本机精简版）

跟随壁纸自动生成低饱和「莫兰迪」配色，并分发到 niri / fcitx5 / alacritty / fastfetch 四个目标

上游来源：<https://github.com/LanRhyme/dotfiles> 的 `dot_config/noctalia/morandi-gen.py`（2695 行，28 个目标）
本机版本按已安装软件裁剪为 4 个目标，去掉了 starship / ghostty / zed / vscode / blender / krita / limine 等未安装或未使用的写入逻辑，并把写死的作者路径全部改为 `Path.home()` 派生

## 数据流

```text
换壁纸
  └─ noctalia 触发 hooks.wallpaper_changed
       └─ apply-morandi.sh
            ├─ noctalia theme <壁纸> --scheme muted -o colors.json   # Material You 取色
            └─ morandi-gen.py
                 ├─ generate_palette()   # 饱和度打三折 + 封顶 45，得到莫兰迪调
                 ├─ write_niri()         # ~/.config/niri/cfg/colors.kdl
                 ├─ write_fcitx5()       # ~/.local/share/fcitx5/themes/morandi/
                 ├─ write_alacritty()    # ~/.config/alacritty/themes/noctalia.toml
                 ├─ write_fastfetch()    # ~/.config/fastfetch/config.jsonc
                 └─ reload_all()         # niri validate + 重载、fcitx5 重载
```

## 文件清单

| 文件 | 作用 |
|------|------|
| `~/.config/noctalia/apply-morandi.sh` | 入口：取当前壁纸 → 生成 colors.json → 调用引擎，日志写 `~/.local/state/noctalia/morandi.log` |
| `~/.config/noctalia/morandi-gen.py` | 引擎：palette 生成 + 四个目标写入 + 热重载 |
| `~/.config/noctalia/colors.json` | noctalia 产出的原始 Material You 色，每次换壁纸覆盖 |
| `~/.config/noctalia/morandi-backup/original/` | 引擎接管前的原始配置（只在首次写入时保存） |
| `~/.config/niri/cfg/colors.kdl` | 焦点环渐变、标签指示器、插入提示、最近窗口高亮 |
| `~/.local/share/fcitx5/themes/morandi/` | 输入法面板主题（panel.svg / highlight.svg / theme.conf） |
| `~/.config/alacritty/themes/noctalia.toml` | 终端 16 色 + 光标 + 选区 + 搜索高亮 |
| `~/.config/fastfetch/config.jsonc` | fastfetch 的键名/标题/分隔线配色 |

## 用法

```bash
# 换壁纸后自动运行，无需手动干预
# 手动同步一次（例如换了配色方案但没换壁纸）
~/.config/noctalia/apply-morandi.sh

# 只看调色板，不写文件
~/.config/noctalia/morandi-gen.py --palette

# 预览将要写入的内容（不落盘）
~/.config/noctalia/morandi-gen.py --dry-run

# 写文件但不重载 niri/fcitx5
~/.config/noctalia/morandi-gen.py --no-reload
```

hook 本身由 noctalia 的 settings 保存，可用这些命令查看/改写：

```bash
noctalia msg config-get hooks.wallpaper_changed
noctalia msg config-set hooks.wallpaper_changed '["bash ~/.config/noctalia/apply-morandi.sh"]'
```

## 各目标改了什么

- **niri**：`layout` 段只写 `focus-ring` / `border` / `shadow` / `tab-indicator` / `insert-hint`，focus-ring 用 `active-gradient ... relative-to="workspace-view"`，所以拖动窗口时边框会随工作区移动而流动变色
  - niri 允许多个 `layout {}` 节点按字段合并（`merge_with`），因此 `colors.kdl` 不会覆盖 `layout.kdl` 里的 `gaps` / `preset-column-widths`
- **fcitx5**：生成独立主题目录，并把 `classicui.conf` 的 `Theme` / `DarkTheme` 指向它，同时开启竖排候选（`Vertical Candidate List`）
- **alacritty**：主题写在独立文件里，通过 `[general] import` 引入；引擎会清掉 `alacritty.toml` 里内联的 `[colors.*]` 段，否则内联值优先级更高会让主题失效
- **fastfetch**：整份 `config.jsonc` 由引擎生成（含 CachyOS 内置 logo），每次启动 fastfetch 读取

## 新增一个应用

在 `morandi-gen.py` 里加一个函数，然后注册到 `TARGETS` 即可，不要在应用配置里手写死颜色

```python
def write_btop(palette: dict, w: Writer) -> None:
    conf = CONFIG / "btop" / "btop.conf"
    if not conf.exists():
        return
    text = conf.read_text()
    text = re.sub(r'^theme\[.*\]$', f'theme[main_bg]="{palette["base"]}"', text, flags=re.M)
    w.write(conf, text)

TARGETS = (write_niri, write_fcitx5, write_alacritty, write_fastfetch, write_btop)
```

`w.write(path, text)` 已经处理了目录创建、dry-run、首次备份和日志输出

## 回滚与卸载

```bash
# 恢复引擎接管前的原始配置
cp -r ~/.config/noctalia/morandi-backup/original/.config ~/
cp -r ~/.config/noctalia/morandi-backup/original/.local  ~/   # 如存在

# 只停用自动触发
noctalia msg config-set hooks.wallpaper_changed '[]'
```

## 已知边界

- 只处理深色：`noctalia theme` 默认输出 dark 角色色，浅色模式没有做反向映射
- `--scheme muted` 是取的基调；想更灰可调 `morandi()` 的 `sat_reduction`（默认 0.3）与 `sat_cap`（默认 45）
- alacritty 内联 `[colors.*]` 会被删除，想保留自带配色就别让引擎管 alacritty（从 `TARGETS` 中移除 `write_alacritty`）
- fcitx5 主题如果没立刻变化，`fcitx5-remote -e` 重启一次输入法
- 引擎生成的文件都带 `morandi-gen` 标记，带标记的文件不会被备份（避免备份里堆积生成物）
