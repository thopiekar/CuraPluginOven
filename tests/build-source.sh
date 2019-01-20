#!/bin/bash
# Test whether fetching and building packages works.

URL="https://thopiekar.eu:5443/cura-cad-integration/CuraBlenderPlugin.git"
SOURCE="./source"
git clone $URL -b cura-4.0.0-updates $SOURCE --recurse-submodules

python3 ../cpo.py --create=all --source=$SOURCE
