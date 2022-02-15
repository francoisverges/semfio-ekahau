"""
Written by Francois Verges (@VergesFrancois)
Idea came from Haydn Andrews (@TheWLAN)

This script will create tags to document the following information for each AP:
 - antenna type (Internal or External)
 - antenna name (if external antenna is used)
 - antenna vendor (if external antenna is used)

This script leverage the new tag feature that got introduced with Ekahau Pro 10.2

In order for this script to work, you will need to create the following tags
and assign them to at least 1 AP in your project file:
 - 'antenna-name'
 - 'antenna-type'
 - 'antenna-vendor'

Currently working for Ekahau version 10.2 project files
"""

import argparse
import time
import os
import zipfile
import json
import pathlib
import shutil
from pprint import pprint


def main():
    parser = argparse.ArgumentParser(
        description='This scrip auto configure antenna tags based on AP properties')
    parser.add_argument('file', metavar='esx_file', help='Ekahau project file')
    args = parser.parse_args()

    current_filename = pathlib.PurePath(args.file).stem
    working_directory = os.getcwd()

    # Load & Unzip the Ekahau Project File
    with zipfile.ZipFile(args.file, 'r') as myzip:
        myzip.extractall(current_filename)

        # Load the accessPoints.json file into the accessPoints dictionary
        with myzip.open('accessPoints.json') as json_file:
            accessPoints = json.load(json_file)

        # Load the simulatedRadios.json file into the simulatedRadios dictionary
        with myzip.open('simulatedRadios.json') as json_file:
            simulatedRadios = json.load(json_file)

        # Load the antennaTypes.json file into the antennaTypes dictionary
        with myzip.open('antennaTypes.json') as json_file:
            antennaTypes = json.load(json_file)

        # Load the tagKeys.json file into the tagKeys dictionary
        with myzip.open('tagKeys.json') as json_file:
            tagKeys = json.load(json_file)

        # Retreive the ID corresponding to each antenna related tags
        for tag in tagKeys['tagKeys']:
            if tag['key'] == 'antenna-name':
                antenna_tag_id = tag['id']
            elif tag['key'] == 'antenna-type':
                antenna_type_tag_id = tag['id']
            elif tag['key'] == 'antenna-vendor':
                antenna_vendor_tag_id = tag['id']

        # Loop through the AP and auto populate the tag values based on the AP properties
        for ap in accessPoints['accessPoints']:
            for radio in simulatedRadios['simulatedRadios']:
                if radio['status'] != "DELETED":
                    if ap['id'] == radio['accessPointId']:
                        for antenna in antennaTypes['antennaTypes']:
                            if radio['antennaTypeId'] == antenna['id']:
                                if antenna['frequencyBand'] == "FIVE":
                                    if antenna['apCoupling'] == "EXTERNAL_ANTENNA" and '802i' not in ap['model']:
                                        ext_antenna_name = antenna['name'].split(' ')[1]
                                        ext_antenna_vendor = antenna['name'].split(' ')[0]
                                        ap['tags'].append(
                                            {"tagKeyId": antenna_tag_id, "value": ext_antenna_name})
                                        print(
                                            f"{ap['name']}: 'antenna-name' tag set to '{ext_antenna_name}'")
                                        ap['tags'].append(
                                            {"tagKeyId": antenna_type_tag_id, "value": "External"})
                                        print(
                                            f"{ap['name']}: 'antenna-type' tag set to 'External'")
                                        ap['tags'].append(
                                            {"tagKeyId": antenna_vendor_tag_id, "value": ext_antenna_vendor})
                                        print(
                                            f"{ap['name']}: 'antenna-vendor' tag set to '{ext_antenna_vendor}'\n")
                                    else:
                                        ap['tags'].append(
                                            {"tagKeyId": antenna_type_tag_id, "value": "Internal"})
                                        print(
                                            f"{ap['name']}: 'antenna-type' tag set to 'Internal'\n")

    # Write the changes into the accessPoints.json File
    with open(working_directory + '/' + current_filename + '/accessPoints.json', 'w') as file:
        json.dump(accessPoints, file, indent=4)

    # Create a new version of the Ekahau Project
    new_filename = current_filename + '_modified'
    shutil.make_archive(new_filename, 'zip', current_filename)
    shutil.move(new_filename + '.zip', new_filename + '.esx')

    # Cleaning Up
    shutil.rmtree(current_filename)


if __name__ == "__main__":
    start_time = time.time()
    print('** Creating Antenna Tags...\n')
    main()
    run_time = time.time() - start_time
    print("\n** Time to run: %s sec" % round(run_time, 2))
