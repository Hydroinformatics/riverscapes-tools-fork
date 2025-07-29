Evan Hackstadt
Dr. Meghna Babbar-Sebens
2025 July

# How to Use sqlBRAT Locally

## Introduction

Do be aware that Riverscapes’ priority is automating BRAT and their other tools to get outputs for much of the US, which they’ve achieved. See their publicly available data: [https://data.riverscapes.net/](https://data.riverscapes.net/). The tool is not intended to be run by individuals locally, though it is possible thanks to the code being open source.  
Although Riverscapes Consortium provides [Installation Instructions](https://tools.riverscapes.net/brat/Advanced/installation/) for getting sqlBRAT set up locally, they are out of date and simply didn’t work for me (as of June 2025). This document outlines alternative methods that worked for me after many hours of troubleshooting.  
	User “ecopony” on this GitHub [discussion thread](https://github.com/Riverscapes/riverscapes-tools/discussions/693#discussioncomment-6236482) documented their installation process from a few years ago. It is highly useful and helped inform these instructions. It will be referred to as Ed’s Notes. However, I still had to do things differently since the code has been changed since.

### Requirements:

* I made a few tweaks and bug fixes to the code. These are found here, on our [forked GitHub repo](https://github.com/Hydroinformatics/riverscapes-tools-fork). I recommend using the code from that repo, or reproducing the modifications yourself.  
* This was initially done on a Mac (M2 MBA on macOS Sequoia).  
* If on Windows, you will also need [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

## Installation

### Python & Conda

1. Install Python  
   1. Despite Riverscape’s instructions, you DO NOT need Python 3.7.4 \- in fact, this outdated version causes so many headaches with dependencies etc.  
   2. Per Ed’s Notes, I used Python 3.10.9. This version fits well with most package requirements.  
   3. I used conda on the command line to manage all Python envs and versions. I used Miniconda (though I also had the Anaconda distribution installed). If on Windows, make sure you’re in Anaconda PowerShell Prompt (miniconda3). Now,  per Ed’s Notes…  
      `conda create --name brat-3.10 -c anaconda python=3.10.9`  
      `conda activate brat-3.10`  
   4. Your conda might tell you to run  `conda init`  (or  `conda init zsh`  if using zsh) before activating. Follow instructions.  
2. Install Pip \- per Riverscapes  
   1. Conda should have already installed pip. Either way, you can run:  
      `conda install pip`  
      to verify the installation and update if needed.  
3. Text Editor \- per Riverscapes \- VSCode is good; you can select your conda env as the Python interpreter (however we run from the command line so it doesn’t matter).  
4. Desktop GIS \- per Riverscapes \- QGIS is good  
5. PATH Variables  
   1. Conda should handle this. Don’t make changes unless stuff seems broken.  
6. Virtual Environment  
   1. We already have our conda environment set up. I did not use virtualenv from pip, since geospatial packages are better managed all in conda.  
7. Python Site Packages  
   1. Ensure your conda environment is activated (should be from Step 1). 

### Packages

8. Packages \- here we deviate from Riverscapes steps  
   1. I found it easiest to go straight to installing Riverscapes modules after installing GDAL, rather than getting bogged down in installing all the requirements.txt.  
   2. This may be poor practice, but if it works, it works.  
9. Install GDAL & Dependencies w/ conda-forge  
   1. First prepare conda-forge:  
      `conda update -n base -c defaults conda`  
      `conda config --add channels conda-forge`  
      `conda config --set channel_priority strict`  
   2. GDAL tends to cause the most issues. I installed it plus some related packages up front. Using conda forge solved a bus error I was having.  
      `conda install -c conda-forge gdal`  
      `conda install -c conda-forge rasterio fiona geopandas`  
   3. To check the packages in your conda env at any time, run  `conda list`  
   4. Note conda can’t install the required shapely version (1.8.5.post1). It should install when we install the Riverscapes packages.  
10. Prepare to Install Riverscapes Packages  
    1. We want to install the relevant Riverscapes packages as editable. This will allow us to run them from the command line. It’s best to do this with pip, but within our conda env.  
    2. Ensure your conda env is activated (you should see (env name) at the front of your prompt). Ensure you’re in the root riverscapes-tools folder.  
    3. Ensure we are using the pip from our conda env \- run:  
       `which pip`  
    4. If the path contains something like /anaconda3/envs/\[name\]/bin/pip, you’re good  
11. Install lib/commons  
    1. Each time we install a Riverscapes package, it will run the setup file and install any additional required packages we need.  
    2. From the riverscapes root folder, run:  
       `pip install -e lib/commons`  
    3. It should install a number of packages. If you’re doing this in the future, there may be version issues — best of luck to you.  
    4. Note that pip throws a warning about geopandas and shapely being incompatible. To my knowledge this did not cause any issues.  
    5. To verify installation, run  `conda list`  and look for rs-commons  
12. Install Relevant Packages  
    1. We will repeat the process with the rest of the Riverscapes packages we want. The different tools feed into each other. If you want the full sqlBRAT stack, it (currently) requires outputs from RSContext, Hydro, Anthro, and VBET.  
    2. Install the packages you want. For example:  
       `pip install -e packages/rscontext/`  
       `pip install -e packages/anthro/`  
       `pip install -e packages/hydro/`  
       `pip install -e packages/vbet/`  
       `pip install -e packages/brat/`  
    3. Most of these have similar requirements, so they should be quick with no issues.  
    4. To verify installation, run  `conda list`  and look for each of these packages (note the brat package is actually called sqlbrat)  
    5. Note that I ran into additional package errors when trying to run VBET locally. However, if you’re focused on BRAT, it should still work.  
13. Get the BRAT Code \- per Riverscapes  
    1. Note that I have applied a few tiny changes to the code to get it to run on my machine. You can find my forked repo at [https://github.com/Hydroinformatics/riverscapes-tools-fork](https://github.com/Hydroinformatics/riverscapes-tools-fork).   
    2. If you want Riverscape’s repo, here is a working link. No guarantees that these instructions will work with future versions of the riverscape repo. [https://github.com/Riverscapes/riverscapes-tools/tree/master](https://github.com/Riverscapes/riverscapes-tools/tree/master).  
    3. They use a monorepo that contains multiple tools, of which BRAT is one. You’ll want to clone/fork/download the whole repo.

## Usage

### More Setup…

1. Now that we’ve installed the tools, we can get ready to run them from the command line\!  
2. Let’s say I want to run sqlBRAT. First, I need to build and install.  
   1. Move into the package folder:  
      `cd packages/brat/`  
   2. (with conda env still active) Run:  
      `python setup.py build`  
      `python setup.py install`  
3. Manually copy certain things  
   1. This sets up most of what we need, but for some reason we need to manually copy three things (layer descriptions, the database folder, and into the egg in the env. If you don’t do this, you’ll eventually hit errors that it can’t find these files when running the script.  
      `cp sqlbrat/layer_descriptions.json <user>/<conda_folder>/envs/<env_name>/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg/sqlbrat`  
      `cp sqlbrat/brat_report.css <user>/anaconda3/envs/<env_name>/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg/sqlbrat`  
      `cp -R database <user>/anaconda3/envs/<env_name>/lib/python3.10/site-packages/sqlbrat-5.1.5-py3.10.egg`  
      Note this last one goes in the egg, not /sqlbrat subfolder  
   2. If these paths aren’t valid, browse to it in the finder. Anaconda3 \> your env \> lib \> python3.10 folder \> site-packages \> sqlbrat egg. (On Windows, skip the python3.10 folder). CMD+OPT+C to copy pathname. You can also use Finder to verify that these files were copied.  
   3. You’ll need to run these commands again if you ever re-build and re-install the package (e.g. if you modify the code). It could be useful to store them somewhere or write a script.  
4. Test the command  
   1. The command is the name of the name of the tool (also the name of the main script, see brat/sqlbrat/brat.py)  
   2. To test if the command works, just run it with help:  
      `brat --help`  
   3. For me, I got an error that networkx wasn’t found, and then same for matplotlib. For anything like this, use conda to install the packages that we still need on a case-by-case (easier than requirements.txt…).  
      `conda install networkx`  
      `conda install matplotlib`  
   4. After conda takes care of that, the command should output the help dialogue (which is indeed very helpful):

`usage: brat [-h] [--reach_codes REACH_CODES] [--canal_codes CANAL_CODES]`  
            `[--peren_codes PEREN_CODES] [--flow_areas FLOW_AREAS]`  
            `[--waterbodies WATERBODIES] [--max_waterbody MAX_WATERBODY]`  
            `[--meta META] [--verbose] [--debug]`  
            `huc hillshade hydro_flowlines hydro_igos hydro_dgos anthro_flowlines`  
            `anthro_igos anthro_dgos existing_veg historical_veg valley_bottom`  
            `streamside_buffer riparian_buffer output_folder`

`Build the inputs for an eventual brat_run:`

`positional arguments:`  
  `huc                   huc input`  
  `hillshade             hillshade input`  
  `hydro_flowlines       hydro flowlines input`  
  `hydro_igos            hydro igos input`  
  `hydro_dgos            hydro dgos input`  
  `anthro_flowlines      anthro flowlines input`  
  `anthro_igos           anthro igos input`  
  `anthro_dgos           anthro dgos input`  
  `existing_veg          existing_veg input`  
  `historical_veg        historical_veg input`  
  `valley_bottom         Valley bottom shapeFile`  
  `streamside_buffer     streamside_buffer input`  
  `riparian_buffer       riparian_buffer input`  
  `output_folder         output_folder input`

`options:`  
  `-h, --help            show this help message and exit`  
  `--reach_codes REACH_CODES`  
                        `Comma delimited reach codes (FCode) to retain when`  
                        `filtering features. Omitting this option retains all`  
                        `features.`  
  `--canal_codes CANAL_CODES`  
                        `Comma delimited reach codes (FCode) representing canals.`  
                        `Omitting this option retains all features.`  
  `--peren_codes PEREN_CODES`  
                        `Comma delimited reach codes (FCode) representing perennial`  
                        `features`  
  `--flow_areas FLOW_AREAS`  
                        `(optional) path to the flow area polygon feature class`  
                        `containing artificial paths`  
  `--waterbodies WATERBODIES`  
                        `(optional) waterbodies input`  
  `--max_waterbody MAX_WATERBODY`  
                        `(optional) maximum size of small waterbody artificial flows`  
                        `to be retained`  
  `--meta META           riverscapes project metadata as comma separated key=value`  
                        `pairs`  
  `--verbose             (optional) a little extra logging`  
  `--debug               (optional) more output about things like memory usage.`  
                        `There is a performance cost`

### Waterfall Tools Diagram
[https://tools.riverscapes.net/] and scroll down

### Running BRAT

5. As you can see, the current version of BRAT takes in a number of inputs from the other Riverscapes tools \- namely RSContext, Hydro, Anthro, and VBET.  
6. If you just want to run BRAT on a region that these tools have already been run on, you can download their data outputs from the [Riverscapes Data Exchange](https://data.riverscapes.net/). If you want to run them yourself, gp off of the above instructions to build and install and run them.  
7. Make a folder somewhere logical to store these outputs (which will be inputs for BRAT).  
8. Make another folder somewhere logical to capture your local BRAT outputs.  
9. I suggest exporting some path variables to your terminal to simplify the command. Copy the path of each of the other tools’ output folders to export like so:  
   `export RS=<path to RS Context folder>`  
   `export HYDRO=<path to Hydro folder>`  
   `export ANTHRO=<path to Anthro folder>`  
   `export VBET=<path to VBET folder>`  
10. Now we can build our command.  
    1. HUC — be sure to use the 10-digit HUC, otherwise stuff will break with no explanation.  
    2. Hillshade — find this in  `$RS/topography/dem_hillshade.tif`  
    3. Hydro\_flowlines — find this in  `$HYDRO/outputs/hydro.gpkg/vwReaches`  
    4. Hydro\_igos — find this in  `$HYDRO/outputs/hydro.gpkg/IGOGeometry`  
    5. Hydro\_dgos — find this in  `$HYDRO/outputs/hydro.gpkg/vwDgos`  
    6. Anthro\_flowlines — find this in  `$ANTHRO/outputs/anthro.gpkg/vwReaches`  
    7. Anthro\_igos — find this in  `$ANTHRO/outputs/anthro.gpkg/IGOGeometry`  
    8. Anthro\_dgos — find this in  `$ANTHRO/outputs/anthro.gpkg/vwDgos`  
    9. Existing\_veg — find this in  `$RS/vegetation/existing_veg.tif`  
    10. Historic\_veg — find this in  `$RS/vegetation/historic_veg.tif`  
    11. Valley\_bottom — find this in  `$VBET/outputs/vbet.gpkg/vbet_full`  
    12. Streamside\_buffer — standard is 30 but you might be able to try others  
    13. Riparian\_buffer — standard is 100 but you might be able to try others  
    14. Output\_folder — give a path to the output folder you made  
    15. \--reach\_codes — I found these on the Data Exchange project metadata for my watershed.  
    16. \--canal\_codes — I found these on the Data Exchange project metadata for my watershed.  
    17. \--peren\_codes —  `46006`  seems to work generally (also see ReachCodes.csv)  
    18. \--flow\_areas — find this in  `$RS/hydrology/nhdplushr.gpkg/NHDArea`  
    19. --waterbodies — find this in  $RS/hydrology/nhdplushr.gpkg/NHDWaterbody
    20. --max_waterbody — I found this on the Data Exchange project metadata for my watershed


11. So for example, my command for a watershed with HUC 1710020407 looked like:
    `brat 1710020407 \`  
    `$RS/topography/dem_hillshade.tif \`  
    `$HYDRO/outputs/hydro.gpkg/vwReaches \`  
    `$HYDRO/outputs/hydro.gpkg/IGOGeometry \`  
    `$HYDRO/outputs/hydro.gpkg/vwDgos \`  
    `$ANTHRO/outputs/anthro.gpkg/vwReaches \`  
    `$ANTHRO/outputs/anthro.gpkg/IGOGeometry \`  
    `$ANTHRO/outputs/anthro.gpkg/vwDgos \`  
    `$RS/vegetation/existing_veg.tif \`  
    `$RS/vegetation/historic_veg.tif \`  
    `$VBET/outputs/vbet.gpkg/vbet_full \`  
    `30 \`  
    `100 \`  
    `/Users/evan/Code/OSU-EB3-REU/sqlBRAT/inputs-outputs/brat/output \`  
    `--reach_codes 33400,33600,33601,33603,46000,46003,46006,46007 \`  
    `--canal_codes 33600,33601,33603 \`  
    `--peren_codes 46006 \`  
    `--flow_areas $RS/hydrology/nhdplushr.gpkg/NHDArea \`  
    `--waterbodies $RS/hydrology/nhdplushr.gpkg/NHDWaterbody \`  
    `--verbose`

12. Once again it may be useful to copy-paste this command into another document for easy access and adjustment. You may run into additional issues not described here.  
13. IF you get a bus error on dem\_hillshade.tif right as vegetation summary begins, you may have an issue with GDAL and OSgeo installation. Troubleshooting:  
    1. Ensure everything is installed through conda (paths should be similar):  
       `which gdalinfo`  
       `python -c "from osgeo import gdal; print(gdal.__file__)”`  
    2. Ensure you followed Step 9 precisely, including using conda-forge and installing all of the dependencies (rasterio, fiona, geopandas, shapely). You can repeat any of the commands to make sure things are installed.
