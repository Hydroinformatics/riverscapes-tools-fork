# PREREQUISITES:
# Python 3.10.x
# The brat package and its dependencies are installed in the environment
# Script executed from: /packages/brat

# We need these environment variables to be set
# input sources (paths to directories):
(: "${RS?}")
(: "${HYDRO?}")
(: "${ANTHRO?}")
(: "${VBET?}")
# other:
(: "${HUC10?}")
(: "${ENV_EGG_DIR?}")
(: "${OUTPUT_DIR?}")

echo "———Input Sources:———"
echo "RS: $RS"
echo "HYDRO: $HYDRO"
echo "ANTHRO: $ANTHRO"
echo "VBET: $VBET"
echo "———Other:———"
echo "HUC10: $HUC10"
echo "ENV_EGG_DIR: $ENV_EGG_DIR"
echo "OUTPUT_DIR: $OUTPUT_DIR"

# build and install
python setup.py build
python setup.py install

# manual copying for some reason
cp sqlbrat/layer_descriptions.json $ENV_EGG_DIR/sqlbrat
cp sqlbrat/brat_report.css $ENV_EGG_DIR/sqlbrat
cp -R database $ENV_EGG_DIR

echo "Copied layer_descriptions, css, and database into $ENV_EGG_DIR"

# Run the tool for Lower Siletz

echo "Running BRAT for HUC $HUC10"

brat $HUC10 \
    $RS/topography/dem_hillshade.tif \
    $HYDRO/outputs/hydro.gpkg/vwReaches \
    $HYDRO/outputs/hydro.gpkg/IGOGeometry \
    $HYDRO/outputs/hydro.gpkg/vwDgos \
    $ANTHRO/outputs/anthro.gpkg/vwReaches \
    $ANTHRO/outputs/anthro.gpkg/IGOGeometry \
    $ANTHRO/outputs/anthro.gpkg/vwDgos \
    $RS/vegetation/existing_veg.tif \
    $RS/vegetation/historic_veg.tif \
    $VBET/outputs/vbet.gpkg/vbet_full \
    30 \
    100 \
    $OUTPUT_DIR \
    --reach_codes 33400,33600,33601,33603,46000,46003,46006,46007 \
    --canal_codes 33600,33601,33603 \
    --peren_codes 46006,55800,33400 \
    --flow_areas $RS/hydrology/nhdplushr.gpkg/NHDArea \
    --waterbodies $RS/hydrology/nhdplushr.gpkg/NHDWaterbody \
    --verbose