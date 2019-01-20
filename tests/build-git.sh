#!/bin/bash
# Test whether fetching and building packages works.

SOURCE="https://thopiekar.eu:5443/cura-cad-integration/CuraBlenderPlugin.git"

python3 ../cpo.py --create=all --source=$SOURCE --gitargs="-b cura-4.0.0-updates"
