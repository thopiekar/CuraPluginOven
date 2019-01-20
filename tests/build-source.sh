#!/bin/bash
# Test whether fetching and building packages works.

URL="https://thopiekar.eu:5443/cura-cad-integration/CuraBlenderPlugin.git"
SOURCE="./source"
git clone $URL $SOURCE

python3 ../cpo.py --create=all --source=$SOURCE
