#!/bin/bash
# Test whether fetching and building packages works.

SOURCE="https://thopiekar.eu:5443/cura-cad-integration/CuraOpenSCADPlugin.git"

python3 ../cpo.py --create=all --source=$SOURCE
