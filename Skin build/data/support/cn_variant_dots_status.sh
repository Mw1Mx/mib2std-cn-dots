#!/bin/ksh
ACTION=status
ENGINE=""
for drive in /media/mp00*; do
    candidate="$drive/toolbox/custom/skins/cn_variant_dots/engine.sh"
    if [ -f "$candidate" ]; then
        if [ -n "$ENGINE" ]; then echo "ERROR: Multiple CN Variant dots drives"; exit 1; fi
        ENGINE="$candidate"
    fi
done
if [ -z "$ENGINE" ]; then echo "ERROR: CN Variant dots package missing"; exit 1; fi
. "$ENGINE"
