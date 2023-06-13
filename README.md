# metashape---macrophotogrammetry
Underwater macrophotogrammetry metashape workflow to run projects in batch on a High Performance Computing cluster (HPC). Codes adapted from ucdavis/metashape

# Short description / application

A tool to make it easy to run reproducible, automated, documented Metashape photogrammetry workflows in batch on a high performance computer cluster. This workflow was adapted from ucdavis/metashape for underwater macrophotogrammetry of small ~20cm diameter plots and is not GUI free. 
The full photogrammetry workflow is detailed in Gouezo et al. 2023. Underwater macrophotogrammetry to monitor in situ benthic communities at submillimetre scale. Methods in Ecology and Evolution. Accepted MS 13/06/2023. Once 3D models are made, manual steps are required to orientate the model and build DEM and orthomosaics as described in Gouezo et al. (2023)

## Setup (similar to as ucdavis/metashape)

**Python:** You need Python (3.7 or 3.8). We recommend the [Anaconda distribution](https://www.anaconda.com/distribution/) because it includes all the required libraries. When installing, if asked whether the installer should initialize Anaconda3, say "yes". Anaconda must be initialized upon install such that `python` can be called from the command line. A way to check is to simply enter `python` at your command prompt and see if the resulting header info includes Anaconda and Python 3. If it doesn't, you may still need to initialize your Conda install. **Alternative option:** If you want a minimal python installation (such as if you're installing on a computing cluster), you can install [miniconda](https://docs.conda.io/en/latest/miniconda.html) instead. After intalling miniconda, you will need to install additional packages required by our scripts (currently only `PyYAML`) using `pip install {package_name}`.

**Metashape:** You must install the Metashape Python 3 module (Metashape version 1.8). Download the [current .whl file](https://www.agisoft.com/downloads/installer/) and install it following [these instructions](https://agisoft.freshdesk.com/support/solutions/articles/31000148930-how-to-install-metashape-stand-alone-python-module) (using the name of the .whl file that you downloaded).

**Metashape license:** You need a license (and associated license file) for Metashape. The easiest way to get the license file (assuming you own a license) is by installing the [Metashape Professional Edition GUI software](https://www.agisoft.com/downloads/installer/) (distinct from the Python module) and registering it following the prompts in the software (note you need to purchase a license first). UC Davis users, inquire over the geospatial listserv or the #geosptial Slack channel for information on joining a floating license pool. Once you have a license file (whether a node-locked or floating license), you need to set the `agisoft_LICENSE` environment variable (search onilne for instructions for your OS; look for how to *permanently* set it) to the path to the folder containing the license file (`metashape.lic`).

**Reproducible workflow scripts:** Simply clone this repository to your machine!

## Usage

The general worflow has three components:
1. Organizing raw imagery into subfolders
2. Set up runs on HPC
3. 3D model processing

### 1. Organizing raw imagery for processing

images must be organized ideally in folders and subfolders as follow:

```
'ProjectName'
├───'StudySiteName'
├──────'PlotName_date'
      0001.TIFF
			0002.TIFF
			0003.TIFF
			...
```

Folders of images needs to be copied to the appropriate HPC location, where 3D model processing will be done

### 2. Set up runs on HPC

login to HPC

clone "etc" and "bin" folders into the `StudySiteName` folder
If needed modify parameters in `etc/Reefs3D_template.ylm` 

change the directory to the folder `StudySiteName`, e.g. run in command window `cd /{repo_path}/StudySiteName`

in the command window, run:
./bin/mkRunFile.bash `3D_PlotName_date` `{repo_path}/PlotName_date # this creates a new subfolder nammed 3D_PlotName_date

A new subfolder should be created named `3D_PlotName_date` with the following subfolders and codes files applied to the specified directory
1. a folder called `images` that links to the `PlotName_date` folder where the images are located 
2. Reefs3D_workflow.py
3. Reefs3D_workflow_functions.py
4. run.yml
5. runMetaShape.bash
6. sbatchMetaShape.bash

### 3. 3D model processing

in the command windows:
`cd {repo_path}/3D_PlotName_date`
execute `runMetaShape.bash` 
or 
`sbatch sbatchMetaShape.bash` where running workflows of different projects in batch (ie. series), set date and time at the start of each .bash files so they are queued through time. Allow few hours between models - depending on HPC specs

### workflow output

In the folder `3D_PlotName_date`, there will be the following outputs:
- **Photogrammetry outputs** (e.g., Metashape processing report, processing log)
- **A Metashape project file (.psx) and associated files folder** (for processing via Metashape GUI)
- **A processing log** (e.g. slurm-XX.out file that helps to solve problems when codes are not running properly)

