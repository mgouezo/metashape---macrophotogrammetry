#/bin/bash
# $1 = project name
# $2 = image dir
baseDir=$PWD
PREV_RUN=''

if [ $# -lt 2 ]
then
	echo 'no project name and/or images directory provided'
	echo 'USAGE: mkRunFile <project_name> <image_directory>'
else
	#echo $1
	PROJ_NAME=$1
	echo '   PROJ_NAME: '$PROJ_NAME
	IMG_SRC=$2
	if [ ! -d $IMG_SRC ]
	then
		echo 'ERROR: image directory does not exist'
		exit 1
	else
		echo '   IMG_SRC: '$IMG_SRC
	fi

	PROJ_PATH=''${baseDir//\//\\\/}\\\/$PROJ_NAME''
	#echo $PROJ_PATH

	echo ' '
	if [ ! -d $baseDir/$PROJ_NAME ]
	then
		echo '- creating project directory'
		mkdir $baseDir/$PROJ_NAME
		
		echo '- creating project run.yml file'
	else
		echo 'NOTE: project '$PROJ_NAME' exists, so just regenerating run.yml'
		if [ -h $baseDir/$PROJ_NAME/images ]
		then
			echo 'NOTE: images directory already linked, so remapping in case new'
			rm $baseDir/$PROJ_NAME/images
		fi
	fi # if [ ! -d $baseDir/$PROJ_NAME ]
	ln -s $IMG_SRC $baseDir/$PROJ_NAME/images

	cp $PWD/etc/Reefs3D_template.yml $baseDir/$PROJ_NAME/run.yml
	sed -i 's/#PROJ_NAME#/'$PROJ_NAME'/' $baseDir/$PROJ_NAME/run.yml
	sed -i 's/#PROJ_PATH#/'$PROJ_PATH'/' $baseDir/$PROJ_NAME/run.yml
	sed -i 's/#PREV_RUN#/'$PREV_RUN'/' $baseDir/$PROJ_NAME/run.yml

	cp $PWD/etc/Reefs3D_workflow* $baseDir/$PROJ_NAME

	echo ' '
	echo '- creating interactive session run script'
	echo '#!/bin/bash
module load metashape-workflow
time OMP_NUM_THREADS=16 CUDA_VISIBLE_DEVICES=1 ./Reefs3D_workflow.py run.yml' > $baseDir/$PROJ_NAME/runMetaShape.bash
	chmod +x $baseDir/$PROJ_NAME/runMetaShape.bash

	echo ' '
	echo '- creating batch session run script'
	echo '#!/bin/bash
#SBATCH --job-name='$PROJ_NAME'_MetaShape
#SBATCH --time=24:00:00
#SBATCH --ntasks-per-node=14
#SBATCH --gres=gpu:2
#SBATCH --mem=64g

# Application specific commands:
module load cuda metashape-workflow
cd '$baseDir/$PROJ_NAME'
time OMP_NUM_THREADS=16 CUDA_VISIBLE_DEVICES=1 ./Reefs3D_workflow.py run.yml' > $baseDir/$PROJ_NAME/sbatchMetaShape.bash


fi # if [ $# eq 0 ]

