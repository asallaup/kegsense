#!/bin/bash
# Regenerate the case STLs + preview renders from case.scad. Requires
# OpenSCAD (brew install --cask openscad).
set -e
cd "$(dirname "$0")"

openscad -o case_base.stl -D 'PART="base"' case.scad
openscad -o case_lid.stl -D 'PART="lid"' case.scad

openscad -o case_assembled_preview.png -D 'PART="preview"' \
  --imgsize=1200,1200 --autocenter --viewall --camera=0,0,0,60,0,35,400 \
  --colorscheme=Tomorrow case.scad
openscad -o case_full_back_preview.png -D 'PART="base"' \
  --imgsize=1200,1200 --camera=140,-110,-60,21,34,-5 \
  --colorscheme=Tomorrow case.scad

echo "wrote case_base.stl, case_lid.stl, case_assembled_preview.png, case_full_back_preview.png"
