#!/usr/bin/env python3
"""morandi-gen.py —— 莫兰迪全局配色引擎（精简版）

上游: https://github.com/LanRhyme/dotfiles  dot_config/noctalia/morandi-gen.py
裁剪: 只保留本机已安装的四个目标 (niri / fcitx5 / alacritty / fastfetch)，
      删掉 starship / ghostty / zed / vscode / blender / krita / limine 等
      未安装应用的写入逻辑，以及写死作者机器路径的部分。

数据流:
  壁纸 ──noctalia theme --scheme muted──> ~/.config/noctalia/colors.json
       ──generate_palette()──> 压低饱和度的莫兰迪 palette
       ──write_xxx(palette)──> 四个目标的配置文件
       ──reload()──> niri / fcitx5 热重载

用法:
  ./morandi-gen.py              生成并应用
  ./morandi-gen.py --dry-run    只打印将要写入的内容，不落盘
  ./morandi-gen.py --palette    只打印调色板（含色块）
  ./morandi-gen.py --no-reload  落盘但不触发重载

扩展:
  新增一个应用 = 写一个 write_xxx(palette) 函数 + 在 TARGETS 列表里注册一行。
  配色逻辑不要再写死在应用配置里，全部由这里注入，才能随壁纸自动同步。
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ─────────────────────────── 路径 ───────────────────────────
HOME = Path.home()
CONFIG = HOME / ".config"

COLORS_JSON = CONFIG / "noctalia" / "colors.json"
BACKUP_ROOT = CONFIG / "noctalia" / "morandi-backup"

NIRI_DIR = CONFIG / "niri"
NIRI_CONFIG = NIRI_DIR / "config.kdl"
NIRI_COLORS = NIRI_DIR / "cfg" / "colors.kdl"

ALACRITTY_DIR = CONFIG / "alacritty"
ALACRITTY_TOML = ALACRITTY_DIR / "alacritty.toml"
ALACRITTY_THEME = ALACRITTY_DIR / "themes" / "noctalia.toml"

FCITX5_THEME_NAME = "morandi"
FCITX5_THEME_DIR = HOME / ".local/share/fcitx5/themes" / FCITX5_THEME_NAME
FCITX5_CLASSICUI = CONFIG / "fcitx5" / "conf" / "classicui.conf"

FASTFETCH_CONFIG = CONFIG / "fastfetch" / "config.jsonc"


# ─────────────────────────── 色彩数学 ───────────────────────────
def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, l * 100


def hsl_to_hex(h: float, s: float, l: float) -> str:
    h = h % 360
    s = max(0, min(100, s)) / 100
    l = max(0, min(100, l)) / 100
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def morandi(hex_color: str, sat_reduction: float = 0.3, light_adjust: float = 0,
            warm_shift: float = 0, sat_cap: float = 45) -> str:
    """把 Material You 的高饱和色压成低饱和、偏灰的莫兰迪调。"""
    h, s, l = hex_to_hsl(hex_color)
    s = s * (1 - sat_reduction)
    h = (h + warm_shift) % 360
    l = max(0, min(100, l + light_adjust))
    s = min(s, sat_cap)
    return hsl_to_hex(h, s, l)


def blend(c1: str, c2: str, ratio: float = 0.5) -> str:
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_palette(c: dict) -> dict:
    """Material You 角色色 -> 莫兰迪 palette（键名沿用上游 catppuccin 风格命名）。"""
    primary = c.get("mPrimary", c.get("primary"))
    secondary = c.get("mSecondary", c.get("secondary"))
    tertiary = c.get("mTertiary", c.get("tertiary"))
    error = c.get("mError", c.get("error"))
    surface = c.get("mSurface", c.get("surface"))
    on_surface = c.get("mOnSurface", c.get("on_surface"))
    surface_var = c.get("mSurfaceVariant", c.get("surface_variant"))
    outline = c.get("mOutline", c.get("outline"))

    missing = [name for name, val in (
        ("primary", primary), ("secondary", secondary), ("tertiary", tertiary),
        ("error", error), ("surface", surface), ("on_surface", on_surface),
        ("surface_variant", surface_var), ("outline", outline),
    ) if not val]
    if missing:
        sys.exit(f"colors.json 缺少字段: {', '.join(missing)}（noctalia 版本变化？）")

    p = {}
    # 背景与表面：同色系明暗阶梯
    p["base"] = morandi(surface, 0.5, -2)
    p["mantle"] = morandi(surface, 0.6, -5)
    p["surface0"] = morandi(surface_var, 0.4, 2)
    p["surface1"] = morandi(surface_var, 0.3, 5)
    p["surface2"] = morandi(surface_var, 0.2, 8)
    p["overlay0"] = morandi(outline, 0.3, -2)
    p["overlay1"] = morandi(outline, 0.2, 2)
    p["overlay2"] = morandi(outline, 0.1, 5)
    p["subtext0"] = morandi(on_surface, 0.4, -8)
    p["subtext1"] = morandi(on_surface, 0.3, -4)
    p["text"] = morandi(on_surface, 0.2, 0)
    # 点缀色
    p["love"] = morandi(error, 0.25, -15)
    p["rose"] = morandi(blend(primary, error, 0.6), 0.3, -15, 5)
    p["gold"] = morandi(blend(primary, "#d4a574", 0.3), 0.35, -10, 15)
    p["peach"] = morandi(blend(error, "#d4a574", 0.4), 0.3, -10, 10)
    p["pine"] = morandi(tertiary, 0.3, -18, -5)
    p["foam"] = morandi(secondary, 0.35, -18, -5)
    p["iris"] = morandi(primary, 0.25, -18)
    p["sky"] = morandi(tertiary, 0.35, -18, -10)

    # fcitx5 面板：比窗口底更暗，保证候选窗不刺眼
    h, s, l = hex_to_hsl(p["surface1"])
    p["fcitx5_bg"] = hsl_to_hex(h, s * 0.6, min(l, 20))
    p["fcitx5_bg_alt"] = hsl_to_hex(h, s * 0.5, min(l + 3, 22))
    ih, is_, il = hex_to_hsl(p["iris"])
    p["fcitx5_hl_bg"] = hsl_to_hex(ih, is_, min(il, 38))
    p["fcitx5_text"] = p["text"]
    p["fcitx5_hl_text"] = p["base"]

    # 终端 ANSI 16 色：和 primary 混色，避免纯红绿蓝跳出整体色调
    for name, ref, sr, la in (
        ("red", "#ff757f", 0.5, -15), ("green", "#c3e88d", 0.5, -15),
        ("yellow", "#ffc777", 0.5, -15), ("blue", "#82aaff", 0.5, -15),
        ("magenta", "#c099ff", 0.5, -15), ("cyan", "#86e1fc", 0.5, -15),
    ):
        p[f"term_{name}"] = morandi(blend(primary, ref, 0.4), sr, la)
        p[f"term_bright_{name}"] = morandi(blend(primary, ref, 0.4), sr - 0.05, la + 3)
        p[f"term_dim_{name}"] = morandi(blend(primary, ref, 0.4), sr + 0.05, la - 3)

    hp, sp, _ = hex_to_hsl(primary)
    hb, sb, lb = hex_to_hsl(p["base"])
    p["term_bg"] = hsl_to_hex(hp, min(sb + 4, 18), max(lb, 4))
    return p


# ─────────────────────────── 写入工具 ───────────────────────────
class Writer:
    """统一处理 dry-run / 备份 / 落盘。"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.backup_dir = BACKUP_ROOT / "original"
        self.changed: list[Path] = []

    @staticmethod
    def _engine_owned(path: Path) -> bool:
        """带 morandi-gen 标记的文件是引擎产物，没有备份价值。"""
        try:
            return "morandi-gen" in path.read_text(errors="ignore")[:400]
        except OSError:
            return False

    def backup(self, path: Path) -> None:
        """只在第一次见到某文件时备份，保留引擎接管前的原始版本。"""
        if not path.exists() or self.dry_run:
            return
        if self._engine_owned(path):
            return
        try:
            rel = path.relative_to(HOME)
        except ValueError:
            rel = Path(path.name)
        dest = self.backup_dir / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            print(f"  bak {dest}")

    def write(self, path: Path, text: str, label: str = "") -> None:
        self.changed.append(path)
        if self.dry_run:
            print(f"\n───── [dry-run] {path} {label} ─────")
            print(text.rstrip())
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        self.backup(path)
        path.write_text(text)
        print(f"  ok  {path}")


def prune_backups(keep: int = 8) -> None:
    """清理历史遗留的时间戳快照（新版本只用 original/ 一份）。"""
    for old in BACKUP_ROOT.glob("*"):
        if old.is_dir() and old.name != "original":
            shutil.rmtree(old, ignore_errors=True)


# ─────────────────────────── 目标 1: niri ───────────────────────────
def write_niri(palette: dict, w: Writer) -> None:
    kdl = f"""// Auto-generated by morandi-gen.py — do not edit manually
layout {{
    focus-ring {{
        width 1
        active-gradient from="{palette['iris']}" to="{palette['pine']}" angle=45 relative-to="workspace-view"
        inactive-gradient from="{palette['surface0']}" to="{palette['surface1']}" angle=45 relative-to="workspace-view"
    }}
    border {{
        off
    }}
    shadow {{
        color "{palette['surface0']}70"
    }}
    tab-indicator {{
        active-color "{palette['iris']}"
        inactive-color "{palette['surface1']}"
        urgent-color "{palette['love']}"
    }}
    insert-hint {{
        color "{palette['iris']}80"
    }}
}}
recent-windows {{
    highlight {{
        active-color "{palette['iris']}"
        urgent-color "{palette['love']}"
    }}
}}
"""
    w.write(NIRI_COLORS, kdl)

    # 确保 config.kdl 引入 colors.kdl（只改一次）
    if NIRI_CONFIG.exists():
        text = NIRI_CONFIG.read_text()
        if "colors.kdl" not in text:
            if not text.endswith("\n"):
                text += "\n"
            text += '\ninclude "./cfg/colors.kdl"\n'
            w.write(NIRI_CONFIG, text, "(append include)")
            print("  note: 已在 config.kdl 末尾追加 include \"./cfg/colors.kdl\"")


# ─────────────────────────── 目标 2: fcitx5 ───────────────────────────
def write_fcitx5(palette: dict, w: Writer) -> None:
    bg, hl = palette["fcitx5_bg"], palette["fcitx5_hl_bg"]
    pine = palette["pine"]
    bh, bs, bl = hex_to_hsl(bg)
    border = hsl_to_hex(bh, bs, min(bl + 5, 100))

    panel_svg = f'''<!-- generated by morandi-gen.py -->
<svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect width="40" height="40" rx="8" fill="{bg}" fill-opacity="0.85"/>
<rect x="0.5" y="0.5" width="39" height="39" rx="8" stroke="{border}" stroke-opacity="1.0"/>
</svg>'''

    highlight_svg = f'''<!-- generated by morandi-gen.py -->
<svg width="42" height="42" viewBox="0 0 42 42" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M41 1V5.51948H36.5293V10.1667H41V31.8333H36.5293V36.8333H41V41H36.5293V36.8333H32.2V41H9.8V36.8333H5.21655V41H1V36.8333H5.21655V31.8333H1V10.1667H5.21655V5.51948H1V1H5.21655V5.51948H9.8V1H20.2H32.2V5.51948H36.5293V1H41Z" fill="{pine}" fill-opacity="0.2"/>
<path d="M5.21655 5.51948H1V1H5.21655V10.1667H1V31.8333H5.21655V41H1V36.8333H9.8V41H32.2V36.8333H41V41H36.5293V31.8333H41V10.1667H36.5293V1H41V5.51948H32.2V1H20.2H9.8V5.51948H5.21655Z" stroke="{pine}" stroke-width="2"/>
</svg>'''

    theme = f"""[Metadata]
Name={FCITX5_THEME_NAME}
Version=1.0.0
Author=morandi-gen
Description=莫兰迪低饱和动态配色

[InputPanel]
NormalColor={palette['fcitx5_text']}
HighlightColor={palette['fcitx5_hl_text']}
HighlightBackgroundColor={pine}
HighlightCandidateColor={pine}
EnableBlur=True
FullWidthHighlight=True
PageButtonAlignment=Bottom

[InputPanel/BlurMargin]
Left=2
Right=2
Top=2
Bottom=2

[InputPanel/Background]
Image=panel.svg
Color={bg}
BorderColor={border}
BorderWidth=0

[InputPanel/Background/Margin]
Left=12
Right=12
Top=12
Bottom=12

[InputPanel/Highlight]
Image=highlight.svg
Color={bg}
BorderColor={border}00
BorderWidth=0
Gravity="Top Left"

[InputPanel/Highlight/Margin]
Left=12
Right=12
Top=1
Bottom=1

[InputPanel/ContentMargin]
Left=10
Right=10
Top=10
Bottom=10

[InputPanel/TextMargin]
Left=10
Right=10
Top=4
Bottom=4

[Menu]
NormalColor={palette['fcitx5_text']}
HighlightCandidateColor={palette['fcitx5_text']}
Spacing=0

[Menu/Background]
Image=panel.svg
Color={bg}
BorderColor={border}
BorderWidth=0

[Menu/Background/Margin]
Left=6
Right=6
Top=6
Bottom=6

[Menu/Highlight]
Image=highlight.svg
Color={bg}
BorderColor={border}00
BorderWidth=0

[Menu/Highlight/Margin]
Left=4
Right=4
Top=2
Bottom=2

[Menu/Separator]
Color={palette['fcitx5_bg_alt']}
BorderColor={palette['fcitx5_bg_alt']}00
BorderWidth=0
"""
    w.write(FCITX5_THEME_DIR / "panel.svg", panel_svg)
    w.write(FCITX5_THEME_DIR / "highlight.svg", highlight_svg)
    w.write(FCITX5_THEME_DIR / "theme.conf", theme)

    # 把经典 UI 指向新主题（注意本机 classicui.conf 是 "Key    = value" 对齐格式）
    if not FCITX5_CLASSICUI.exists():
        print("  skip: 没有 classicui.conf，跳过主题启用")
        return
    text = FCITX5_CLASSICUI.read_text()
    updates = {
        "Theme": FCITX5_THEME_NAME,
        "DarkTheme": FCITX5_THEME_NAME,
        "UseDarkTheme": "False",
        "Vertical Candidate List": "True",
        "TrayOutlineColor": palette["surface1"],
        "TrayTextColor": palette["text"],
    }
    for key, value in updates.items():
        pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(f"{key} = {value}", text)
        else:
            text = text.rstrip("\n") + f"\n{key} = {value}\n"
    w.write(FCITX5_CLASSICUI, text)


# ─────────────────────────── 目标 3: alacritty ───────────────────────────
def write_alacritty(palette: dict, w: Writer) -> None:
    theme = f"""# Auto-generated by morandi-gen.py — do not edit manually
[colors.primary]
background = '{palette["term_bg"]}'
foreground = '{palette["text"]}'

[colors.cursor]
text = '{palette["base"]}'
cursor = '{palette["iris"]}'

[colors.vi_mode_cursor]
text = '{palette["base"]}'
cursor = '{palette["foam"]}'

[colors.search.matches]
foreground = '{palette["base"]}'
background = '{palette["term_yellow"]}'

[colors.search.focused_match]
foreground = '{palette["base"]}'
background = '{palette["term_blue"]}'

[colors.footer_bar]
foreground = '{palette["text"]}'
background = '{palette["mantle"]}'

[colors.hints.start]
foreground = '{palette["base"]}'
background = '{palette["term_yellow"]}'

[colors.hints.end]
foreground = '{palette["base"]}'
background = '{palette["term_magenta"]}'

[colors.selection]
text = '{palette["text"]}'
background = '{palette["surface2"]}'

[colors.normal]
black = '{palette["surface1"]}'
red = '{palette["term_red"]}'
green = '{palette["term_green"]}'
yellow = '{palette["term_yellow"]}'
blue = '{palette["term_blue"]}'
magenta = '{palette["term_magenta"]}'
cyan = '{palette["term_cyan"]}'
white = '{palette["text"]}'

[colors.bright]
black = '{palette["surface2"]}'
red = '{palette["term_bright_red"]}'
green = '{palette["term_bright_green"]}'
yellow = '{palette["term_bright_yellow"]}'
blue = '{palette["term_bright_blue"]}'
magenta = '{palette["term_bright_magenta"]}'
cyan = '{palette["term_bright_cyan"]}'
white = '{palette["text"]}'

[colors.dim]
black = '{palette["surface0"]}'
red = '{palette["term_dim_red"]}'
green = '{palette["term_dim_green"]}'
yellow = '{palette["term_dim_yellow"]}'
blue = '{palette["term_dim_blue"]}'
magenta = '{palette["term_dim_magenta"]}'
cyan = '{palette["term_dim_cyan"]}'
white = '{palette["subtext0"]}'
"""
    w.write(ALACRITTY_THEME, theme)

    if not ALACRITTY_TOML.exists():
        print("  skip: 没有 alacritty.toml")
        return
    text = ALACRITTY_TOML.read_text()
    original = text

    # 1) 引入主题文件（放在 [general] 段内）
    if "themes/noctalia.toml" not in text:
        if re.search(r"^import\s*=", text, re.MULTILINE):
            print("  warn: alacritty.toml 已有 import 键，请手动把 themes/noctalia.toml 加进去")
        else:
            text = re.sub(
                r"^\[general\]\s*$",
                f'[general]\nimport = ["{ALACRITTY_THEME}"]',
                text, count=1, flags=re.MULTILINE,
            )

    # 2) 删掉内联的 [colors.*] 段，否则会覆盖导入的主题
    text = re.sub(
        r"^\[colors\.(?:primary|normal|bright|cursor|selection|dim)\][\s\S]*?(?=\n\[|\Z)",
        "", text, flags=re.MULTILINE,
    )
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip("\n") + "\n"

    if text != original:
        w.write(ALACRITTY_TOML, text, "(import + strip inline colors)")


# ─────────────────────────── 目标 4: fastfetch ───────────────────────────
def write_fastfetch(palette: dict, w: Writer) -> None:
    def module(kind: str, key: str) -> dict:
        return {"type": kind, "key": f"  {key}"}

    sep = palette["overlay0"]
    config = {
        "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
        "logo": {
            "type": "small",
            "source": "CachyOS_small",
            "padding": {"top": 1, "left": 2, "right": 3},
        },
        "display": {
            "separator": "  ",
            "color": {"keys": palette["iris"], "title": palette["text"]},
        },
        "modules": [
            {"type": "title", "color": {
                "user": palette["text"], "at": palette["iris"], "host": palette["pine"]}},
            {"type": "separator", "string": "─", "times": 36, "outputColor": sep},
            module("os", "OS"),
            module("kernel", "Kernel"),
            module("uptime", "Uptime"),
            module("packages", "Packages"),
            module("shell", "Shell"),
            module("wm", "WM"),
            module("cpu", "CPU"),
            module("gpu", "GPU"),
            module("memory", "Memory"),
            module("disk", "Disk"),
            {"type": "separator", "string": "─", "times": 36, "outputColor": sep},
            {"type": "colors", "symbol": "circle", "paddingLeft": 2},
        ],
    }
    w.write(FASTFETCH_CONFIG,
            "// Auto-generated by morandi-gen.py — do not edit manually\n"
            + json.dumps(config, ensure_ascii=False, indent=2) + "\n")


TARGETS = (write_niri, write_fcitx5, write_alacritty, write_fastfetch)


# ─────────────────────────── 热重载 ───────────────────────────
def reload_all() -> None:
    # niri：先校验语法，坏了就别 reload，保住当前会话
    check = subprocess.run(["niri", "validate"], capture_output=True, text=True)
    if check.returncode == 0:
        subprocess.run(["niri", "msg", "action", "load-config-file"],
                       capture_output=True)
        print("  ok  niri 已重载")
    else:
        print("  fail niri 配置校验失败，未重载：", file=sys.stderr)
        print((check.stderr or check.stdout).strip(), file=sys.stderr)

    # fcitx5：轻量重载，不打断当前输入状态
    if shutil.which("fcitx5-remote"):
        subprocess.run(["fcitx5-remote", "-r"], capture_output=True)
        print("  ok  fcitx5 已重载（若主题未生效，执行 fcitx5-remote -e 重启）")


def print_palette(palette: dict) -> None:
    groups = [
        ("背景", ["base", "mantle", "surface0", "surface1", "surface2"]),
        ("前景", ["overlay0", "overlay1", "overlay2", "subtext0", "subtext1", "text"]),
        ("点缀", ["iris", "pine", "foam", "sky", "love", "rose", "gold", "peach"]),
        ("终端", ["term_bg", "term_red", "term_green", "term_yellow",
                  "term_blue", "term_magenta", "term_cyan"]),
        ("fcitx5", ["fcitx5_bg", "fcitx5_bg_alt", "fcitx5_hl_bg"]),
    ]
    for title, keys in groups:
        print(f"\n{title}:")
        for k in keys:
            v = palette[k]
            r = int(v[1:3], 16); g = int(v[3:5], 16); b = int(v[5:7], 16)
            print(f"  \033[48;2;{r};{g};{b}m      \033[0m  {k:16s} {v}")


def main() -> None:
    ap = argparse.ArgumentParser(description="莫兰迪全局配色引擎")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不落盘")
    ap.add_argument("--palette", action="store_true", help="只打印调色板")
    ap.add_argument("--no-reload", action="store_true", help="不触发重载")
    ap.add_argument("--colors", default=str(COLORS_JSON), help="colors.json 路径")
    args = ap.parse_args()

    colors_path = Path(args.colors).expanduser()
    if not colors_path.exists():
        sys.exit(
            f"找不到 {colors_path}\n"
            "先运行 ~/.config/noctalia/apply-morandi.sh（它会用当前壁纸生成 colors.json）"
        )

    with colors_path.open() as f:
        colors = json.load(f)

    palette = generate_palette(colors)

    if args.palette:
        print_palette(palette)
        return

    print(f"colors.json : {colors_path}")
    print(f"source_color: {colors.get('source_color', '?')}")
    print(f"模式        : {'dry-run' if args.dry_run else 'apply'}")

    w = Writer(dry_run=args.dry_run)
    for target in TARGETS:
        target(palette, w)

    if not args.dry_run and not args.no_reload:
        reload_all()


if __name__ == "__main__":
    main()
