# Dirk Slawinski
# O&A CSIRO
# 2020 
# &
# Marine Gouezo
# SCU / O&A CSIRO
# 2023
# after:
#   Derek Young and Alex Mandel
#   University of California, Davis
#   2019

#### Import libraries

# import the fuctionality we need to make time stamps to measure performance
import time
import datetime
import platform
import os
import glob
import re
import yaml
import math # for future use

### import the Metashape functionality
import Metashape


#### Helper functions and globals

# Set the log file name-value separator
# Chose ; as : is in timestamps
# TODO: Consider moving log to json/yaml formatting using a dict
sep = "; "

def stamp_time():
    '''
    Format the timestamps as needed
    '''
    stamp = datetime.datetime.now().strftime('%Y%m%dT%H%M')
    return stamp

def diff_time(t2, t1):
    '''
    Give a end and start time, subtract, and round
    '''
    total = str(round(t2-t1, 1))
    return total

# Used by add_gcps function
def get_marker(chunk, label):
    for marker in chunk.markers:
        if marker.label == label:
            return marker
    return None

# Used by add_gcps function
def get_camera(chunk, label):
    for camera in chunk.cameras:
        if camera.label.lower() == label.lower():
            return camera
    return None



#### Functions for each major step in Metashape

def project_setup(cfg):
    '''
    Create output and project paths, if they don't exist
    Define a project ID based on photoset name and timestamp
    Define a project filename and a log filename
    Create the project
    Start a log file
    '''


    # Make project directories (necessary even if loading an existing project because this workflow saves a new project based on the old one, leaving the old one intact
    if not os.path.exists(cfg["output_path"]):
        os.makedirs(cfg["output_path"])
    if not os.path.exists(cfg["project_path"]):
        os.makedirs(cfg["project_path"])

    ### Set a filename template for project files and output files
    ## Get the first parts of the filename (the photoset ID and location string)

    run_name = cfg["run_name"]

    ## Project file example to make: "projectID_YYYYMMDDtHHMM-jobID.psx"
    timestamp = stamp_time()
    run_id = "_".join([run_name,timestamp])
    # TODO: If there is a slurm JobID, append to time (separated with "-", not "_"). This will keep jobs initiated in the same minute distinct

    project_file = os.path.join(cfg["project_path"], '.'.join([run_id, 'psx']) )
    log_file = os.path.join(cfg["output_path"], '.'.join([run_id+"_log",'txt']) )


    '''
    Create a doc and a chunk
    '''

    # create a handle to the Metashape object
    doc = Metashape.Document() #When running via Metashape, can use: doc = Metashape.app.document

    # If specified, open existing project
    if cfg["load_project"] != "":
        doc.open(cfg["load_project"])
    else:
        # Initialize a chunk, set its CRS as specified, here it is local coordinate system
        chunk = doc.addChunk()
        chunk.crs = Metashape.CoordinateSystem('LOCAL_CS["Local Coordinates (m)",LOCAL_DATUM["Local Datum",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]]]')
        #chunk.marker_crs = Metashape.CoordinateSystem(cfg["addGCPs"]["gcp_crs"])

    # Save doc doc as new project (even if we opened an existing project, save as a separate one so the existing project remains accessible in its original state)
    doc.save(project_file)


    '''
    Log specs except for GPU
    '''

    # log Metashape version, CPU specs, time, and project location to results file
    # open the results file
    # TODO: records the Slurm values for actual cpus and ram allocated
    # https://slurm.schedmd.com/sbatch.html#lbAI
    with open(log_file, 'a') as file:

        # write a line with the Metashape version
        file.write(sep.join(['Project', run_id])+'\n')
        file.write(sep.join(['Agisoft Metashape Professional Version', Metashape.app.version])+'\n')
        # write a line with the date and time
        file.write(sep.join(['Processing started', stamp_time()]) +'\n')
        # write a line with CPU info - if possible, improve the way the CPU info is found / recorded
        file.write(sep.join(['Node', platform.node()])+'\n')
        file.write(sep.join(['CPU', platform.processor()]) +'\n')
        # write two lines with GPU info: count and model names - this takes multiple steps to make it look clean in the end

    return doc, log_file, run_id



def enable_and_log_gpu(log_file):
    '''
    Enables GPU and logs GPU specs
    '''

    gpustringraw = str(Metashape.app.enumGPUDevices())
    gpucount = gpustringraw.count("name': '")
    gpustring = ''
    currentgpu = 1
    while gpucount >= currentgpu:
        if gpustring != '': gpustring = gpustring+', '
        gpustring = gpustring+gpustringraw.split("name': '")[currentgpu].split("',")[0]
        currentgpu = currentgpu+1
    #gpustring = gpustringraw.split("name': '")[1].split("',")[0]
    gpu_mask = Metashape.app.gpu_mask

    with open(log_file, 'a') as file:
        file.write(sep.join(['Number of GPUs Found', str(gpucount)]) +'\n')
        file.write(sep.join(['GPU Model', gpustring])+'\n')
        file.write(sep.join(['GPU Mask', str(gpu_mask)])+'\n')

        # If a GPU exists but is not enabled, enable the 1st one
        if (gpucount > 0) and (gpu_mask == 0):
            Metashape.app.gpu_mask = 1
            gpu_mask = Metashape.app.gpu_mask
            file.write(sep.join(['GPU Mask Enabled', str(gpu_mask)])+'\n')

        # This writes down all the GPU devices available
        #file.write('GPU(s): '+str(Metashape.app.enumGPUDevices())+'\n')

    # set Metashape to *not* use the CPU during GPU steps (appears to be standard wisdom)
    Metashape.app.cpu_enable = False

    return True


def add_photos(doc, cfg):
    '''
    Add photos to project and change their labels to include their containing folder
    '''

    ## Get paths to all the project photos
    a = glob.iglob(os.path.join(cfg["photo_path"],"**","*.*"))   #(([jJ][pP][gG])|([tT][iI][fF]))
    b = [path for path in a]
    photo_files = [x for x in b if (re.search("(.tif$)|(.jpg$)|(.TIF$)|(.TIFF$)|(.tiff$)|(.JPG$)",x)) ]

    ## Add them
    doc.chunk.addPhotos(photo_files)

    ## Need to change the label on each camera so that it includes the containing folder
    for camera in doc.chunk.cameras:
        path = camera.photo.path
        path_parts = path.split("/")[-2:]
        newlabel = "/".join(path_parts)
        camera.label = newlabel

    #Estimate image quality
    for camera in doc.chunk.cameras:
        doc.chunk.analyzePhotos(doc.chunk.cameras)
        if float(camera.meta["Image/Quality"]) < 0.2:
            camera.enabled = False
            print ('DISABLE %s' %(camera))
            
    

    doc.save()

    return True


def align_photos(doc, log_file):
    '''
    Match photos, align cameras, optimize cameras
    '''

    #### Align photos

    # get a beginning time stamp
    timer1a = time.time()

    # Align cameras ## edited by MG - REVISE 
    doc.chunk.matchPhotos(downscale = 1, 
                          generic_preselection = True,
                          reference_preselection=False,
                          filter_mask = False,
                          keypoint_limit = 60000,
                          tiepoint_limit = 0,
                          filter_stationary_points = False,
                          subdivide_task = True)

    doc.chunk.alignCameras(adaptive_fitting = False,
                           reset_alignment = True,
                           subdivide_task = True)

    doc.save()

    # get an ending time stamp
    timer1b = time.time()

    # calculate difference between end and start time to 1 decimal place
    time1 = diff_time(timer1b, timer1a)

    # record results to file
    with open(log_file, 'a') as file:
        file.write(sep.join(['Align Photos', time1])+'\n')
        
    #if markers are there let them be detects
    doc.chunk.detectMarkers(target_type=Metashape.CircularTarget12bit,
                            tolerance=20)
    
    #change accuracy of markers and scale in reference settings - CHECK if WORKING    
    doc.chunk.marker_location_accuracy = Metashape.Vector([0.00005, 0.00005, 0.00005])
    doc.chunk.scalebar_accuracy = 0.00005
        
    # change tie point accuraccy to 0.5 pix in reference settings 
    doc.chunk.tiepoint_accuracy = 0.5
    
    return True



def optimize_cameras(doc):
    '''
    Optimize cameras
    '''

    # Currently only optimizes the default parameters, which is not all possible parameters
    doc.chunk.optimizeCameras(adaptive_fitting = True)
    doc.save()

    return True



def filter_points_usgs_part1(doc, cfg): 
    # added by MG

    rec_thresh_percent = cfg["filterPointsUSGS_1"]["rec_thresh_percent"]
    rec_thresh_absolute = cfg["filterPointsUSGS_1"]["rec_thresh_absolute"]
    proj_thresh_percent = cfg["filterPointsUSGS_1"]["proj_thresh_percent"]
    proj_thresh_absolute = cfg["filterPointsUSGS_1"]["proj_thresh_absolute"]
    reproj_thresh_percent = cfg["filterPointsUSGS_1"]["reproj_thresh_percent"]
    reproj_thresh_absolute = cfg["filterPointsUSGS_1"]["reproj_thresh_absolute"]
    
    fltr = Metashape.PointCloud.Filter()
    fltr.init(doc.chunk, Metashape.PointCloud.Filter.ReprojectionError)
    values = fltr.values.copy()
    values.sort()
    thresh = values[int(len(values) * (1 - reproj_thresh_percent / 100))]
    if thresh < reproj_thresh_absolute:
        thresh = reproj_thresh_absolute  # don't throw away too many points if they're all good
    fltr.removePoints(thresh)

    doc.chunk.optimizeCameras(adaptive_fitting = True)
    
    fltr = Metashape.PointCloud.Filter()
    fltr.init(doc.chunk, Metashape.PointCloud.Filter.ProjectionAccuracy)
    values = fltr.values.copy()
    values.sort()
    thresh = values[int(len(values) * (1- proj_thresh_percent / 100))]
    if thresh < proj_thresh_absolute:
        thresh = proj_thresh_absolute  # don't throw away too many points if they're all good
    fltr.removePoints(thresh)

    doc.chunk.optimizeCameras(adaptive_fitting = True)

    fltr = Metashape.PointCloud.Filter()
    fltr.init(doc.chunk, Metashape.PointCloud.Filter.ReconstructionUncertainty)
    values = fltr.values.copy()
    values.sort()
    thresh = values[int(len(values) * (1 - rec_thresh_percent / 100))]
    if thresh < rec_thresh_absolute:
        thresh = rec_thresh_absolute  # don't throw away too many points if they're all good
    fltr.removePoints(thresh)

    doc.chunk.optimizeCameras(adaptive_fitting = True)

    doc.save()


def filter_points_usgs_part2(doc, cfg): 
    # added by MG

    rec_thresh_percent = cfg["filterPointsUSGS_2"]["rec_thresh_percent"]
    rec_thresh_absolute = cfg["filterPointsUSGS_2"]["rec_thresh_absolute"]
    proj_thresh_percent = cfg["filterPointsUSGS_2"]["proj_thresh_percent"]
    proj_thresh_absolute = cfg["filterPointsUSGS_2"]["proj_thresh_absolute"]
    reproj_thresh_percent = cfg["filterPointsUSGS_2"]["reproj_thresh_percent"]
    reproj_thresh_absolute = cfg["filterPointsUSGS_2"]["reproj_thresh_absolute"]
    
    fltr = Metashape.PointCloud.Filter()
    fltr.init(doc.chunk, Metashape.PointCloud.Filter.ReprojectionError)
    values = fltr.values.copy()
    values.sort()
    thresh = values[int(len(values) * (1 - reproj_thresh_percent / 100))]
    if thresh < reproj_thresh_absolute:
        thresh = reproj_thresh_absolute  # don't throw away too many points if they're all good
    fltr.removePoints(thresh)

    doc.chunk.optimizeCameras(adaptive_fitting = True)
    
    fltr = Metashape.PointCloud.Filter()
    fltr.init(doc.chunk, Metashape.PointCloud.Filter.ProjectionAccuracy)
    values = fltr.values.copy()
    values.sort()
    thresh = values[int(len(values) * (1- proj_thresh_percent / 100))]
    if thresh < proj_thresh_absolute:
        thresh = proj_thresh_absolute  # don't throw away too many points if they're all good
    fltr.removePoints(thresh)

    doc.chunk.optimizeCameras(adaptive_fitting = True)

    fltr = Metashape.PointCloud.Filter()
    fltr.init(doc.chunk, Metashape.PointCloud.Filter.ReconstructionUncertainty)
    values = fltr.values.copy()
    values.sort()
    thresh = values[int(len(values) * (1 - rec_thresh_percent / 100))]
    if thresh < rec_thresh_absolute:
        thresh = rec_thresh_absolute  # don't throw away too many points if they're all good
    fltr.removePoints(thresh)

    doc.chunk.optimizeCameras(adaptive_fitting = True)

    doc.save()
    
    

def build_dense_cloud(doc, log_file, run_id, cfg):
    '''
    Build depth maps and dense cloud
    '''

    ### Build depth maps

    # get a beginning time stamp for the next step
    timer2a = time.time()

    # build depth maps only instead of also building the dense cloud ##?? what does
    doc.chunk.buildDepthMaps(downscale = cfg["buildDenseCloud"]["downscale"],
                             filter_mode = cfg["buildDenseCloud"]["filter_mode"],
                             reuse_depth = cfg["buildDenseCloud"]["reuse_depth"],
                             max_neighbors = cfg["buildDenseCloud"]["max_neighbors"],
                             subdivide_task = True)
    doc.save()

    # get an ending time stamp for the previous step
    timer2b = time.time()

    # calculate difference between end and start time to 1 decimal place
    time2 = diff_time(timer2b, timer2a)

    # record results to file
    with open(log_file, 'a') as file:
        file.write(sep.join(['Build Depth Maps', time2]) + '\n')

    ### Build dense cloud

    # get a beginning time stamp for the next step
    timer3a = time.time()

    # build dense cloud
    doc.chunk.buildDenseCloud(max_neighbors = cfg["buildDenseCloud"]["max_neighbors"],
                              keep_depth = cfg["buildDenseCloud"]["keep_depth"],
                              subdivide_task = True,
                              point_colors = True,
                              point_confidence = True)
    doc.save()
    
    # delete point with low confidence 
    doc.chunk.dense_cloud.setConfidenceFilter(0,1)
    doc.chunk.dense_cloud.removePoints(list(range(128))) #removes all "visible" points of the dense cloud
    doc.chunk.dense_cloud.resetFilters()

    # get an ending time stamp for the previous step
    timer3b = time.time()

    # calculate difference between end and start time to 1 decimal place
    time3 = diff_time(timer3b, timer3a)

    # record results to file
    with open(log_file, 'a') as file:
        file.write(sep.join(['Build Dense Cloud', time3])+'\n')
        


    ### Classify ground points


    #if cfg["buildDenseCloud"]["classify"]:

        # get a beginning time stamp for the next step
        #timer_a = time.time()

        #doc.chunk.dense_cloud.classifyGroundPoints(max_angle = cfg["buildDenseCloud"]["max_angle"],
                                                   #max_distance = cfg["buildDenseCloud"]["max_distance"],
                                                   #cell_size = cfg["buildDenseCloud"]["cell_size"])
        #doc.save()

        # get an ending time stamp for the previous step
        #timer_b = time.time()

        # calculate difference between end and start time to 1 decimal place
        #time_tot = diff_time(timer_b, timer_a)

        # record results to file
        #with open(log_file, 'a') as file:
            #file.write(sep.join(['Classify Ground Points', time_tot]) + '\n')



    ### Export points

    #if cfg["buildDenseCloud"]["export"]:

        # output_file = os.path.join(cfg["output_path"], run_id + '_points.las')

        # if cfg["buildDenseCloud"]["classes"] == "ALL":
            # # call without classes argument (Metashape then defaults to all classes)
            # doc.chunk.exportPoints(path = output_file,
                                   # source_data = Metashape.DenseCloudData,
                                   # format = Metashape.PointsFormatLAS,
                                   # subdivide_task = True)
        # else:
            # # call with classes argument
            # doc.chunk.exportPoints(path = output_file,
                                   # source_data = Metashape.DenseCloudData,
                                   # format = Metashape.PointsFormatLAS,
                                   # classes = cfg["buildDenseCloud"]["classes"],
                                   # subdivide_task = True)

    return True




def build_model(doc, log_file, run_id, cfg): 
    ## edited by MG
    '''
    Build and export 3d Model
    '''
    # get a beginning time stamp for the next step
    timer4a = time.time()
    # edited here - MG ; further edit if model based on depth map is better than dense cloud

    doc.chunk.buildModel(surface_type = Metashape.Arbitrary,
                         interpolation = Metashape.EnabledInterpolation, 
                         face_count_custom = 0,
                         source_data = Metashape.DepthMapsData,
                         vertex_colors = True,
                         keep_depth = True)

    doc.chunk.buildUV(mapping_mode = Metashape.GenericMapping)

    doc.chunk.buildTexture(blending_mode = Metashape.MosaicBlending,
                           texture_size = 8192,
                           fill_holes = False,
                           ghosting_filter = True)

    doc.chunk.buildTiledModel(source_data = Metashape.ModelData,
			      tile_size = 256,
                              face_count = 500000,
                              ghosting_filter=False,
                              transfer_texture=True,
                              subdivide_task = True)

    # output_file = os.path.join(cfg["output_path"], run_id + '_model.obj')

    # doc.chunk.exportModel(path=output_file,
                          # texture_format = Metashape.ImageFormatJPEG, 
                          # save_texture = True,
                          # save_normals = True,
                          # save_uv = True,
                          # format = Metashape.ModelFormatOBJ)

    doc.save()

    # get an ending time stamp for the previous step
    timer4b = time.time()

    # calculate difference between end and start time to 1 decimal place
    time4 = diff_time(timer4b, timer4a)

    # record results to file
    with open(log_file, 'a') as file:
        file.write(sep.join(['Build Model', time4])+'\n')

    return True



def build_dem(doc, log_file, run_id, cfg):
    '''
    Build and export DEM
    '''
    # get a beginning time stamp for the next step
    timer5a = time.time()

    #prepping params for buildDem
    projection = Metashape.OrthoProjection()
    # DS: leave crs unset as we are working in local coordinates only ## MG changed that - see if working
    projection.crs = Metashape.CoordinateSystem(PhotoScan.CoordinateSystem('LOCAL_CS["Local Coordinates",LOCAL_DATUM["Local Datum",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]]]'))

    #prepping params for export
    compression = Metashape.ImageCompression()
    compression.tiff_big = cfg["buildDem"]["tiff_big"]
    compression.tiff_tiled = cfg["buildDem"]["tiff_tiled"]
    compression.tiff_overviews = cfg["buildDem"]["tiff_overviews"]

    if (cfg["buildDem"]["type"] == "DSM") | (cfg["buildDem"]["type"] == "both"):
        # call without classes argument (Metashape then defaults to all classes)
        doc.chunk.buildDem(source_data = Metashape.DenseCloudData,
                           subdivide_task = True,
                           projection = projection)
        output_file = os.path.join(cfg["output_path"], run_id + '_dsm.tif')
        if cfg["buildDem"]["export"]:
            doc.chunk.exportRaster(path=output_file,
                                   projection=projection,
                                   nodata_value=cfg["buildDem"]["nodata"],
                                   source_data=Metashape.ElevationData,
                                   image_compression=compression)
    if (cfg["buildDem"]["type"] == "DTM") | (cfg["buildDem"]["type"] == "both"):
        # call with classes argument
        doc.chunk.buildDem(source_data = Metashape.DenseCloudData,
                           #classes = Metashape.PointClass.Ground,
                           subdivide_task = True,
                           projection = projection)
        output_file = os.path.join(cfg["output_path"], run_id + '_dtm.tif')
        if cfg["buildDem"]["export"]:
            doc.chunk.exportRaster(path=output_file,
                                   projection=projection,
                                   nodata_value=cfg["buildDem"]["nodata"],
                                   source_data=Metashape.ElevationData,
                                   image_compression=compression,
                                   image_format=Metashape.ImageFormatTIFF
                                   ) #resolution=10)
    if (cfg["buildDem"]["type"] != "DTM") & (cfg["buildDem"]["type"] == "both") & (cfg["buildDem"]["type"] == "DSM"):
        raise ValueError("DEM type must be either 'DSM' or 'DTM' or 'both'")

    # get an ending time stamp for the previous step
    timer5b = time.time()

    # calculate difference between end and start time to 1 decimal place
    time5 = diff_time(timer5b, timer5a)

    # record results to file
    with open(log_file, 'a') as file:
        file.write(sep.join(['Build DEM', time5])+'\n')

    return True

# This is just a helper function called by build_orthomosaic
def export_orthomosaic(doc, log_file, run_id, cfg):
    '''
    Export orthomosaic
    '''



    return True


def build_export_orthomosaic(doc, log_file, run_id, cfg, file_ending):
    '''
    Helper function called by build_orthomosaics. build_export_orthomosaic builds and exports an ortho based on the current elevation data.
    build_orthomosaics sets the current elevation data and calls build_export_orthomosaic (one or more times depending on how many orthomosaics requested)
    '''

    # get a beginning time stamp for the next step
    timer6a = time.time()

    #prepping params for buildDem
    projection = Metashape.OrthoProjection()
    #projection.crs = Metashape.CoordinateSystem(cfg["project_crs"])

    doc.chunk.buildOrthomosaic(surface_data = Metashape.ModelData, #ElevationData,
                               blending_mode = Metashape.MosaicBlending,
                               fill_holes = True,
                               refine_seamlines = True,
                               subdivide_task = True,
                               projection = projection)

    doc.save()

    ## Export orthomosaic
    output_file = os.path.join(cfg["output_path"], run_id + '_ortho_dtm.tif')

    compression = Metashape.ImageCompression()
    compression.tiff_big = True
    compression.tiff_tiled = False
    compression.tiff_overviews = True

    projection = Metashape.OrthoProjection()
    
    doc.chunk.exportRaster(path = output_file,
                           projection = projection,
                           nodata_value =-32767,
                           source_data = Metashape.OrthomosaicData,
                           image_compression = compression)

    # get an ending time stamp for the previous step
    timer6b = time.time()

    # calculate difference between end and start time to 1 decimal place
    time6 = diff_time(timer6b, timer6a)

    # record results to file
    with open(log_file, 'a') as file:
        file.write(sep.join(['Build Orthomosaic', time6]) + '\n')

    return True


def build_orthomosaics(doc, log_file, run_id, cfg):
    '''
    Build orthomosaic. This function just calculates the needed elevation data(s) and then calls build_export_orthomosaic to do the actual building and exporting. It does this multiple times if orthos based on multiple surfaces were requsted
    '''

    # prep projection for export step below (in case export is enabled)
    projection = Metashape.OrthoProjection()
    #projection.crs = Metashape.CoordinateSystem(cfg["project_crs"])

    # get a beginning time stamp for the next step
    timer6a = time.time()

    # what should the orthomosaic filename end in? e.g., DSM, DTM, USGS to indicate the surface it was built on
    file_ending = "DTM"

    doc.chunk.buildDem(source_data = Metashape.DenseCloudData,
                       subdivide_task = True,
                       projection = projection)
    build_export_orthomosaic(doc, log_file, run_id, cfg, file_ending = "dtm")
 
    return True





def export_report(doc, run_id, cfg):
    '''
    Export report
    '''

    output_file = os.path.join(cfg["output_path"], run_id+'_report.pdf')

    doc.chunk.exportReport(path = output_file)

    return True



def finish_run(log_file,config_file):
    '''
    Finish run (i.e., write completed time to log)
    '''

    # finish local results log and close it for the last time
    with open(log_file, 'a') as file:
        file.write(sep.join(['Run Completed', stamp_time()])+'\n')

    # open run configuration again. We can't just use the existing cfg file because its objects had already been converted to Metashape objects (they don't write well)
    with open(config_file) as file:
        config_full = yaml.load(file)

    # write the run configuration to the log file
    with open(log_file, 'a') as file:
        file.write("\n\n### CONFIGURATION ###\n")
        documents = yaml.dump(config_full,file, default_flow_style=False)
        file.write("### END CONFIGURATION ###\n")


    return True
