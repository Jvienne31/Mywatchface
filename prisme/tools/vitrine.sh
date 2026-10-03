#!/usr/bin/env bash
# Vitrine de Prisme (docs, fiche de publication) : le cadran au poignet dans 4 palettes + l'AOD.
#   bash prisme/tools/vitrine.sh   ->  prisme/docs/vitrine.png
# Prérequis : Playwright (node_modules), ImageMagick, skin Watch8 Classic de race/emulator.
set -euo pipefail
cd "$(dirname "$0")/../.."
SKIN=race/emulator/skin-galaxy-watch8-classic/background.png
TMP=$(mktemp -d)
FONT=prisme/src/main/res/font/barlowcondensed_semibold.ttf
shots=()
for spec in "0:Lagune" "1:Volcan" "7:Cobalt" "10:Néon" "aod:Always On"; do
  idx=${spec%%:*}; name=${spec#*:}
  PRISME_PREVIEW_PALETTE=$([ "$idx" = aod ] && echo 0 || echo "$idx") python3 prisme/tools/generate.py
  node prisme/tools/render-preview.mjs > /dev/null
  face=prisme/src/main/res/drawable-nodpi/preview.png
  [ "$idx" = aod ] && face=prisme/tools/preview_ambient.png
  convert "$SKIN" "$face" -geometry +101+191 -composite -resize 50% \
    -gravity south -background '#EEF1F3' -splice 0x46 -font "$FONT" -pointsize 30 -fill '#16222B' \
    -annotate +0+8 "$name" "$TMP/$idx.png"
  shots+=("$TMP/$idx.png")
done
convert "${shots[@]}" -background '#EEF1F3' -splice 24x0 +append -chop 24x0 \
  +repage -bordercolor "#EEF1F3" -border 24 prisme/docs/vitrine.png
python3 prisme/tools/generate.py               # retour à la palette par défaut (Lagune)
node prisme/tools/render-preview.mjs > /dev/null
rm -rf "$TMP"
echo prisme/docs/vitrine.png
