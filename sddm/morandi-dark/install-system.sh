#!/bin/sh
set -eu

source_dir=${1:?usage: install-system.sh STAGED_THEME_DIR}
theme_dir=/usr/share/sddm/themes/morandi-dark
config_dir=/etc/sddm.conf.d
dropin=$config_dir/99-morandi-dark.conf

if [ ! -f "$source_dir/Main.qml" ] || [ ! -f "$source_dir/background.jpg" ] || \
   [ ! -f "$source_dir/metadata.desktop" ] || [ ! -f "$source_dir/theme.conf" ] || \
   [ ! -f "$source_dir/99-morandi-dark.conf" ]; then
    echo "Staged theme is incomplete: $source_dir" >&2
    exit 1
fi
if [ -e "$theme_dir" ] || [ -e "$dropin" ]; then
    echo "Refusing to overwrite an existing theme or SDDM drop-in." >&2
    exit 1
fi

install -d -o root -g root -m 0755 "$theme_dir" "$config_dir"
install -o root -g root -m 0644 "$source_dir/Main.qml" "$theme_dir/Main.qml"
install -o root -g root -m 0644 "$source_dir/background.jpg" "$theme_dir/background.jpg"
install -o root -g root -m 0644 "$source_dir/metadata.desktop" "$theme_dir/metadata.desktop"
install -o root -g root -m 0644 "$source_dir/theme.conf" "$theme_dir/theme.conf"
install -o root -g root -m 0644 "$source_dir/99-morandi-dark.conf" "$dropin"
echo "Installed $theme_dir and enabled it in $dropin"
echo "The active SDDM session was left running; the theme will appear at the next login screen."
