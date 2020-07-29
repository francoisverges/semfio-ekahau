"""
Written by Francois Verges (@VergesFrancois)

This script will update the AP model name based on the name of the
external antenna selected.

By default, the name of the AP model does not update when the external antenna
is changed.

This script only change the name of the model of APs used with external antennas.

Use at your own risk, it hasn't been tested at large scale.
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
        description='This script will update the name of model of AP based on the name of the external antenna')
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

        # Loop through the AP and auto populate the tag values based on the AP properties
        for ap in accessPoints['accessPoints']:
            for radio in simulatedRadios['simulatedRadios']:
                if ap['id'] == radio['accessPointId']:
                    for antenna in antennaTypes['antennaTypes']:
                        if radio['antennaTypeId'] == antenna['id']:
                            if antenna['frequencyBand'] == "FIVE" and '802i' not in ap['model']:
                                if antenna['apCoupling'] == "EXTERNAL_ANTENNA":
                                    ext_antenna_name = antenna['name'].split(' ')[1]
                                    ext_antenna_vendor = antenna['name'].split(' ')[0]
                                    ap_model = ap['model'].split(' +')[0]
                                    ap['model'] = ap_model + ' + ' + ext_antenna_vendor + ' ' + ext_antenna_name
                                    print(
                                        f"{ap['name']}: new model name set to '{ap['model']}'")

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
    print('** Updating AP Model Names...\n')
    main()
    run_time = time.time() - start_time
    print("\n** Time to run: %s sec" % round(run_time, 2))
