#!/bin/bash
# Regenerate the KegDisplay Bar case STLs from case_bar.scad. Requires
# OpenSCAD (brew install --cask openscad; if Gatekeeper blocks it, run:
#   xattr -dr com.apple.quarantine "/Applications/OpenSCAD-2021.01.app"
# ).
set -e
cd "$(dirname "$0")"

openscad -o case_bar_base.stl -D 'PART="base"' case_bar.scad
openscad -o case_bar_lid.stl -D 'PART="lid"' case_bar.scad

echo "wrote case_bar_base.stl, case_bar_lid.stl"
