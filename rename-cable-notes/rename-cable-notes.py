import argparse
import time
import os
import zipfile
import json
import pathlib
import shutil
import numpy as np


def find_ap_name_from_coord(accessPoints, cable_note_point, floorPlanId):
    """Return the name of the AP which is located closest to the first point of the cable note."""
    ap_locations = []
    for accessPoint in accessPoints['accessPoints']:
        if accessPoint['location']['floorPlanId'] != floorPlanId:
            continue
        if accessPoint["status"] != "DELETED":
            ap_location = [accessPoint['location']['coord']['x'], accessPoint['location']['coord']['y']]
            ap_locations.append(ap_location)
        closest_ap_location = np.argmin(np.sum((np.array(ap_locations) - np.array(cable_note_point)) ** 2, axis=1))
    for accessPoint in accessPoints['accessPoints']:
            if accessPoint["status"] != "DELETED":
                if accessPoint['location']['coord']['x'] == ap_locations[closest_ap_location][0]:
                    if accessPoint['location']['coord']['y'] == ap_locations[closest_ap_location][1]:
                        return (accessPoint['name'])


def find_telco_room_name_from_coord(notes, pictureNotes, cable_note_point):
    """Return the name of the MDF/IDF room closest to the last point ot the cable note."""
    telco_room_locations = []
    for note in notes['notes']:
        if note['status'] != "DELETED":
            if note['text'].find('IDF') != -1 or note['text'].find('MDF') != -1 or note['text'].find('Rack') != -1:
                for pictureNote in pictureNotes['pictureNotes']:
                    if pictureNote['status'] != "DELETED":
                        if note['id'] == pictureNote['noteIds'][0]:
                            telco_room_locations.append(
                                [pictureNote['location']['coord']['x'], pictureNote['location']['coord']['y']])
    closest_telco_room_location = np.argmin(
        np.sum((np.array(telco_room_locations) - np.array(cable_note_point)) ** 2, axis=1))

    for pictureNote in pictureNotes['pictureNotes']:
        try:
            if pictureNote['location']['coord']['x'] == telco_room_locations[closest_telco_room_location][0]:
                if pictureNote['location']['coord']['y'] == telco_room_locations[closest_telco_room_location][1]:
                    for note in notes['notes']:
                        if note['id'] == pictureNote['noteIds'][0]:
                            return note['text']
        except KeyError:
            print(pictureNote)


def main():
    parser = argparse.ArgumentParser(
        description='This script rename cable notes with AP name and IDF/MDF names.')
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

        # Load the notes.json file into the notes dictionary
        with myzip.open('notes.json') as json_file:
            notes = json.load(json_file)

        # Load the cableNotes.json file into the cableNotes dictionary
        with myzip.open('cableNotes.json') as json_file:
            cableNotes = json.load(json_file)

        # Load the pictureNotes.json file into the pictureNotes dictionary
        with myzip.open('pictureNotes.json') as json_file:
            pictureNotes = json.load(json_file)

        # Loop through the AP and auto populate the tag values based on the AP properties
        for cableNote in cableNotes['cableNotes']:
            # Retreiving the coordinates of both ends of the cable notes
            if cableNote['points']:
                cable_note_first_point = [cableNote['points'][0]['x'], cableNote['points'][0]['y']]
                cable_note_last_point = [cableNote['points'][-1]['x'], cableNote['points'][-1]['y']]
            floorPlanId = cableNote['floorPlanId']
            # Search for AP Name coresponding to AP coordinates
            ap_name = find_ap_name_from_coord(accessPoints, cable_note_last_point, floorPlanId)

            # Search for the IDF/MDF room closer to the end of the cable note
            telco_room_name = find_telco_room_name_from_coord(notes, pictureNotes, cable_note_first_point)

            # Rename Cable Note with AP & MDF/IDF Informationa
            for note in notes['notes']:
                if cableNote['noteIds']:
                    if note['id'] == cableNote['noteIds'][0]:
                        new_name = f"From {telco_room_name} to {ap_name}"
                        note['text'] = new_name
                        print(f"Renamed Cable Note to: {new_name}")

    # Write the changes into the accessPoints.json File
    with open(working_directory + '/' + current_filename + '/notes.json', 'w') as file:
        json.dump(notes, file, indent=4)

    # Create a new version of the Ekahau Project
    new_filename = current_filename + '_modified'
    shutil.make_archive(new_filename, 'zip', current_filename)
    shutil.move(new_filename + '.zip', new_filename + '.esx')

    # Cleaning Up
    shutil.rmtree(current_filename)


if __name__ == "__main__":
    start_time = time.time()
    print('** RENAME CABLE NOTES..\n')
    main()
    run_time = time.time() - start_time
    print("\n** Time to run: %s sec" % round(run_time, 2))
