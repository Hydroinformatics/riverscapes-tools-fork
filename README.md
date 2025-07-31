# Riverscapes Tools - Fork

This is a monorepo housing the python open-source GIS tools for Riverscapes.  
It is a fork that includes some tweaks needed to run the tools locally.  
This fork is NOT intended to initiate pull requests or contribute to riverscapes development. It is an independent research project, forked for convenience and to give credit.   
See the [original repo](https://github.com/Riverscapes/riverscapes-tools) for the latest changes and fully original code.

## How to Use sqlBRAT
BRAT model code is [here](./packages/brat) in the repo, but you'll want to clone the entire repo if running locally.  
My personal experience setting up sqlBRAT locally as of June 2025 is documented here:  
[BRAT Installation & Setup Instructions 2025.md](https://github.com/Hydroinformatics/riverscapes-tools-fork/blob/master/BRAT%20Installation%20%26%20Setup%20Instructions%202025.md)

## Overview of Changes (last updated: 2025-07-10)
*See commit history for proper log of changes*

### Tweaks to fix bugs when running locally:

**filegdb.py**  
Line 59 caused an error attempting to edit a sealed object. New code is present in the filegdb.py in this repo (/lib/commons/rscommons).

**setup.py files**  
Added subfolders (e.g. ./utils) to the setup.py packages for BRAT, Anthro, Hydro, and VBET. New code is present in the repo.

**Change NHDPlusV2 Paths**  
Changed the manual paths to the NHDPlusV2 gpkg contents in rs_context.py to match the names of the 2022 Oregon snapshot.
If you're running RS Context for a different region, you'll need to change this.
If you're just running BRAT, this shouldn't matter.


### New Additions:

**packages/brat/analysis folder**  
Wrote a few scripts in this folder for additional analysis of BRAT outputs and FIS sensitivity analysis.
You can ignore these entirely and everything else should still work, or explore running them.
