#!/bin/bash
# Regenerate the case STLs from case.scad. Requires OpenSCAD
# (brew install --cask openscad; if Gatekeeper blocks it, run:
#   xattr -dr com.apple.quarantine "/Applications/OpenSCAD-2021.01.app"
# ).
set -e
cd "$(dirname "$0")"

openscad -o case_base.stl -D 'PART="base"' case.scad
openscad -o case_lid.stl -D 'PART="lid"' case.scad

echo "wrote case_base.stl, case_lid.stl"
