#!/bin/sh
# Fetch the vendor 3D models that KiCad's library doesn't ship, into the front board's
# 3dmodels folder. They are the makers' files, so they are downloaded rather than kept in git.
#
#   sh tools/get_3d_models.sh
set -e
cd "$(dirname "$0")/../kicad_withpcb/compressor_front/3dmodels"
# Alps RK09K, vertical, 20 mm knob shaft (RK09K1130A5R). All five pots share the body.
if [ ! -f RK09K1130-20.STEP ]; then
  curl -fsSL -A "Mozilla/5.0" -o rk09k.zip \
    "https://tech.alpsalpine.com/cms.media/product_3dcad_rk09k1130a5r_en_39c1a176ff.zip"
  unzip -o -q rk09k.zip RK09K1130-20.STEP
  rm rk09k.zip
fi
echo "3D models ready in $(pwd)"
