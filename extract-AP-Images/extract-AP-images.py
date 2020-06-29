"""
Written by Francois Verges (@VergesFrancois)

This script will extract all image notes attached to an AP objects of an
Ekahau project file (.esx). It will place the pictures in a new directory.
Sub directories will be created for each floors.
This script will also work if you have multiple pictures per AP note

Currently working for Ekahau version 10.2, 10.1 & 10 project files
"""

import argparse
import time
import zipfile
import json
import shutil
import pathlib
import os

def main():
	"""
	This function will extract the images located into the AP notes and rename them using the AP Name
	"""
	parser = argparse.ArgumentParser(description='Extract images located in the AP notes and rename them using the AP name')
	parser.add_argument('file', metavar='esx_file', help='Ekahau project file')
	args = parser.parse_args()

	# Load & Unzip the Ekahau Project File
	current_filename = pathlib.PurePath(args.file).stem
	with zipfile.ZipFile(args.file,'r') as myzip:
		myzip.extractall(current_filename)

		# Load the notes.json file into the notes Dictionary
		with myzip.open('notes.json') as json_file:
			notes = json.load(json_file)

		# Load the accessPoints.json file into the accessPoints dictionary
		with myzip.open('accessPoints.json') as json_file:
			accessPoints = json.load(json_file)

		# Load the floorPlans.json file into the floorPlans dictionary
		with myzip.open('floorPlans.json') as json_file:
			floorPlans = json.load(json_file)

		# Create a new directory to place the new image in
		newpath = os.path.abspath(pathlib.PurePath()) + "/AP-Images"
		if not os.path.exists(newpath):
			os.makedirs(newpath)

		# Create one sub directory per floor under the /AP-Images directrory
		for floor in floorPlans['floorPlans']:
			sub = newpath + '/' + floor['name']
			if not os.path.exists(sub):
				os.makedirs(sub)

			# Move all the AP Images on this floor into the corresponding directory
			for ap in accessPoints['accessPoints']:
				if 'location' in ap.keys() and len(ap['noteIds']) > 0:
					if ap['location']['floorPlanId'] == floor['id']:
						if 'noteIds' in ap.keys():
							count = 0
							for noteId in ap['noteIds']:
								for note in notes['notes']:
									if note['id'] == noteId and len(note['imageIds']) > 0:
										image_count = count + 1
										for image in note['imageIds']:
											image_full_path = os.getcwd() + '/' + current_filename  + '/image-' + image
											if len(note['imageIds']) > 1 or len(ap['noteIds']) > 1:
												dst = newpath + '/' + floor['name'] + '/'+ ap['name'] + '-' + str(image_count) + '.png'
											else:
												dst = newpath + '/' + floor['name'] + '/'+ ap['name'] + '.png'
											shutil.copy(image_full_path, dst)
											image_count += 1
								count = image_count - 1

		# Clean Up
		shutil.rmtree(current_filename)

if __name__ == "__main__":
    start_time = time.time()
    print('** Extracting AP picture notes...')
    main()
    run_time = time.time() - start_time
    print("** Time to run: %s sec" % round(run_time,2))
