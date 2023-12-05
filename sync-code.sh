#!/bin/bash

# Syncs code from the main dev branch to HACS repo.
cd ~/projects/homeassistant/equation-hacs/custom_components/equation
rsync -av --prune-empty-dirs --include '*/' --include='*.py'  --include='*.json' --exclude='*'   ~/projects/homeassistant/core/homeassistant/components/equation/* .

echo "Code synchronized."

