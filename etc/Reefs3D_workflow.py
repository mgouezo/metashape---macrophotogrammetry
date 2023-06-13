#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File for running a metashape workflow

# Dirk Slawinski
# O&A CSIRO
# 2020 
# after:
# 	Derek Young and Alex Mandel
# 	University of California, Davis
# 	2019

import Metashape
import sys
#sys.path.append('/apps/metashape-workflow/20200810/python')
sys.path.append('/apps/metashape-workflow/20210429/python')

import Reefs3D_workflow_functions as meta
import read_yaml
config_file = sys.argv[1]

## Parse the config file
cfg = read_yaml.read_yaml(config_file)

### Run the Metashape workflow

doc, log, run_id = meta.project_setup(cfg)

meta.enable_and_log_gpu(log)

if cfg["load_project"] == "":  # only add photos if this is a brand new project, not based off an existing project
    meta.add_photos(doc, cfg)

if cfg["alignPhotos"]["enabled"]: # added details by MG
    meta.align_photos(doc, log)
    
if cfg["optimizeCameras"]["enabled"]:
    meta.optimize_cameras(doc)
    
if cfg["filterPointsUSGS_1"]["enabled"]:
    meta.filter_points_usgs_part1(doc, cfg)
    
if cfg["filterPointsUSGS_2"]["enabled"]:
    meta.filter_points_usgs_part2(doc, cfg)

if cfg["buildDenseCloud"]["enabled"]:
    meta.build_dense_cloud(doc, log, run_id, cfg)

if cfg["buildModel"]["enabled"]:
    meta.build_model(doc, log, run_id, cfg)

if cfg["buildDem"]["enabled"]:
    meta.build_dem(doc, log, run_id, cfg)

if cfg["buildOrthomosaic"]["enabled"]:
    meta.build_orthomosaics(doc, log, run_id, cfg)

meta.export_report(doc, run_id, cfg)

meta.finish_run(log, config_file)
