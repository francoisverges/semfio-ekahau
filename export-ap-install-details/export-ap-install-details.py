import argparse
import math
import time
import os
import zipfile
import json
import pathlib
import shutil
import gspread
from string import ascii_uppercase
from PIL import Image, ImageDraw, ImageFont
from gspread_formatting import *
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


def calculate_cable_length(meterPerUnit: float, points: list) -> float:
    length = 0
    x = 0
    y = 0
    i = 0

    for coords in points:
        if i == 0:
            x = coords['x']
            y = coords['y']
            i = i+1
        else:
            if x != coords['x'] and y != coords['y']:
                if x > coords['x'] and y > coords['y']:
                    length = length + math.sqrt(((x - coords['x']) ** 2) + ((y - coords['y']) ** 2))
                elif x < coords['y'] and y > coords['y']:
                    length = length + math.sqrt(((coords['x'] - x) ** 2) + ((y - coords['y']) ** 2))
                elif x > coords['y'] and y < coords['y']:
                    length = length + math.sqrt(((x - coords['x']) ** 2) + ((coords['y'] - y) ** 2))
                elif x < coords['y'] and y < coords['y']:
                    length = length + math.sqrt(((coords['x'] - x) ** 2) + ((coords['y'] - y) ** 2))
            elif x != coords['x']:
                if x > coords['x']:
                    length = length + (x - coords['x'])
                else:
                    length = length + (coords['x'] - x)
            else:
                if y > coords['y']:
                    length = length + (y - coords['y'])
                else:
                    length = length + (coords['y'] - y)
            x = coords['x']
            y = coords['y']

    return (length * meterPerUnit)


def retreive_ap_information(survey_file: str):
    aps = []
    current_filename = pathlib.PurePath(survey_file).stem
    working_directory = os.getcwd()

    # Load & Unzip the Ekahau Project File
    with zipfile.ZipFile(survey_file, 'r') as myzip:
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

        # Load the floorplan.json file into the floorplan dictionary
        with myzip.open('floorPlans.json') as json_file:
            floorPlans = json.load(json_file)

        # Load the notes.json file into the notes dictionary
        with myzip.open('notes.json') as json_file:
            notes = json.load(json_file)

        # Load the cableNotes.json file into the cableNotes dictionary
        with myzip.open('cableNotes.json') as json_file:
            cableNotes = json.load(json_file)

        # Retreive the ID corresponding to each antenna related tags
        for tag in tagKeys['tagKeys']:
            if tag['key'] == 'antenna-name':
                antenna_tag_id = tag['id']
            elif tag['key'] == 'antenna-vendor':
                antenna_vendor_tag_id = tag['id']
            elif tag['key'] == 'installation-type':
                installation_type_id = tag['id']
            elif tag['key'] == 'bracket':
                bracket_id = tag['id']
            elif tag['key'] == 'service-loop':
                service_loop_id = tag['id']
            elif tag['key'] == 'IDF':
                IDF_id = tag['id']

        # Loop through the AP to retreive Data
        for ap in accessPoints['accessPoints']:
            ap_info = {}
            if ap['mine'] is True:
                # Get AP Name
                ap_info['name'] = ap['name']

                # Get AP location
                for floor in floorPlans['floorPlans']:
                    if floor['id'] == ap['location']['floorPlanId']:
                        ap_info['location'] = floor['name']
                        metersPerUnit = floor['metersPerUnit']

                # Get AP Vendor
                ap_info['vendor'] = ap['vendor']

                # Get AP model
                ap_info['model'] = ap['model'].split(" ")[0]

                # Get Antenna Name, Mounting, AP Height, Tilt
                ap_info['antennaModel'] = "N/A"
                ap_info['antennaVendor'] = "N/A"
                for radio in simulatedRadios['simulatedRadios']:
                    if ap['id'] == radio['accessPointId']:
                        ap_mounting = radio['antennaMounting']
                        ap_info['height'] = radio['antennaHeight']
                        ap_info['antennaTilt'] = str(round(radio['antennaTilt'])) + "°"
                        for antenna in antennaTypes['antennaTypes']:
                            if radio['antennaTypeId'] == antenna['id']:
                                if antenna['frequencyBand'] == "FIVE":
                                    if antenna['apCoupling'] == "EXTERNAL_ANTENNA" and '802i' not in ap['model']:
                                        ext_antenna_name = antenna['name'].split(' ')[1]
                                        ap_info['antennaModel'] = antenna['name'].split(' ')[1]
                                        ap_info['antennaVendor'] = antenna['name'].split(' ')[0]

                # Get Installation Type information
                ap_info['installationType'] = ap_mounting
                for tag in ap['tags']:
                    if installation_type_id in tag['tagKeyId']:
                        ap_info['installationType'] = tag['value']

                # Get AP bracket information
                ap_info['bracket'] = "Standard"
                for tag in ap['tags']:
                    if bracket_id in tag['tagKeyId']:
                        ap_info['bracket'] = tag['value']

                # Get Service Loop information
                ap_info['serviceLoop'] = "5m"
                for tag in ap['tags']:
                    if service_loop_id in tag['tagKeyId']:
                        ap_info['serviceLoop'] = tag['value']

                # Get MDF/IDF information
                ap_info['idf'] = ""
                for tag in ap['tags']:
                    if IDF_id in tag['tagKeyId']:
                        ap_info['idf'] = tag['value']

                # Get Distance from IDF
                ap_info['distanceToIDF'] = ""
                for note in notes['notes']:
                    if "IDF" in note['text']:
                        if note['text'].split(' to ')[0] in ap['name']:
                            for cable in cableNotes['cableNotes']:
                                for cable_note_id in cable['noteIds']:
                                    if cable_note_id == note['id']:
                                        length = round(calculate_cable_length(
                                            metersPerUnit, cable['points']))
                                        ap_info['distanceToIDF'] = str(length) + "m"

            aps.append(ap_info)

    return (sorted(aps, key=lambda i: i['name']))


def retreive_project_meta_data(survey_file: str, designerEmail: str) -> dict:
    project_meta_data = {}
    current_filename = pathlib.PurePath(survey_file).stem
    working_directory = os.getcwd()

    # Load & Unzip the Ekahau Project File
    with zipfile.ZipFile(survey_file, 'r') as myzip:
        myzip.extractall(current_filename)

        # Load the accessPoints.json file into the accessPoints dictionary
        with myzip.open('project.json') as json_file:
            project = json.load(json_file)

        project_meta_data['customerName'] = project['project']['customer']
        project_meta_data['projectName'] = project['project']['title']
        project_meta_data['location'] = project['project']['location']
        project_meta_data['designerName'] = project['project']['responsiblePerson']
        project_meta_data['designerEmail'] = designerEmail

    return project_meta_data


def connect_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gdrive-creds.json", scope)
    client = gspread.authorize(creds)
    print(f"Connected to Google Sheet")
    time.sleep(2)
    return client


def create_gsheet(gsheet_client, name: str, operators: list):
    new_sheet = gsheet_client.create(name)
    for operator in operators:
        new_sheet.share(operator, perm_type='user', role='writer')
    new_worksheet = new_sheet.add_worksheet(title="APs", rows="100", cols="50")
    new_sheet.del_worksheet(new_sheet.get_worksheet(0))
    print(
        f"New Google Sheet created:\t{new_sheet.url}")
    time.sleep(4)
    return new_worksheet


def open_gsheet(gsheet_client, name: str):
    sheet = gsheet_client.open(name)
    worksheet = sheet.get_worksheet(0)
    print(
        f"Google Sheet opened:\t{sheet.url}")
    return worksheet


def add_project_info(worksheet, project_meta_data: dict):
    print("Adding project information... ", end="", flush=True)
    # Adding the Project information
    worksheet.update_cell(1, 1, "Customer")
    worksheet.update_cell(1, 2, project_meta_data['customerName'])
    worksheet.update_cell(2, 1, "Project")
    worksheet.update_cell(2, 2, project_meta_data['projectName'])
    worksheet.update_cell(3, 1, "Site Address")
    worksheet.update_cell(3, 2, project_meta_data['location'])
    worksheet.update_cell(5, 1, "Wi-Fi Designer")
    worksheet.update_cell(5, 2, project_meta_data['designerName'])
    worksheet.update_cell(5, 3, "Email")
    worksheet.update_cell(5, 4, project_meta_data['designerEmail'])

    # Adding the Installer cells
    worksheet.update_cell(5, 15, "Installer Name")
    worksheet.update_cell(5, 17, "Email")
    worksheet.update_cell(5, 19, "Phone")

    # Formatting these cells
    worksheet.format("A1:A5", {"wrapStrategy": "OVERFLOW_CELL",
                               "textFormat": {"fontSize": 11, "bold": True}})
    worksheet.format("C5", {"wrapStrategy": "OVERFLOW_CELL",
                            "textFormat": {"fontSize": 11, "bold": True}})
    worksheet.format("N5", {"wrapStrategy": "OVERFLOW_CELL",
                            "textFormat": {"fontSize": 11, "bold": True}})
    worksheet.format("P5", {"wrapStrategy": "OVERFLOW_CELL",
                            "textFormat": {"fontSize": 11, "bold": True}})
    worksheet.format("R5", {"wrapStrategy": "OVERFLOW_CELL",
                            "textFormat": {"fontSize": 11, "bold": True}})

    # Resizing columns
    set_column_width(worksheet, 'A', 150)
    set_column_width(worksheet, 'B', 150)
    set_column_width(worksheet, 'O', 150)
    set_column_width(worksheet, 'P', 150)

    # Sleep to avoid Google API limit
    # time.sleep(21)
    print("Done", flush=True)


def create_headers(worksheet):
    print("Creating headers... ", end="", flush=True)
    # Create the header related to Wi-Fi Design information
    worksheet.update_cell(7, 1, "Wi-Fi Design Information")
    worksheet.update_cell(8, 1, "AP Name")
    worksheet.update_cell(8, 2, "AP Location")
    worksheet.update_cell(8, 3, "Location Image")
    worksheet.update_cell(8, 4, "AP Vendor")
    worksheet.update_cell(8, 5, "AP Model")
    worksheet.update_cell(8, 6, "Antenna Model")
    set_column_width(worksheet, 'F', 190)
    worksheet.update_cell(8, 7, "Antenna Vendor")
    worksheet.update_cell(8, 8, "Installation Type")
    set_column_width(worksheet, 'H', 150)
    worksheet.update_cell(8, 9, "Installation Height")
    worksheet.update_cell(8, 10, "Antenna Tilt")
    worksheet.update_cell(8, 11, "AP Bracket")
    worksheet.update_cell(8, 12, "Service Loop")
    worksheet.update_cell(8, 13, "MDF/IDF Name")
    worksheet.update_cell(8, 14, "Distance to MDF/IDF")

    # Create the header related to Installers information
    worksheet.update_cell(7, 15, "Installation Information")
    worksheet.update_cell(8, 15, "AP MAC Address")
    worksheet.update_cell(8, 16, "AP Serial Number")
    worksheet.update_cell(8, 17, "Rack Name")
    worksheet.update_cell(8, 18, "Patch Panel Number")
    worksheet.update_cell(8, 19, "Jack Number")
    worksheet.update_cell(8, 20, "Switch Name")
    worksheet.update_cell(8, 21, "Switch Port")
    worksheet.update_cell(8, 22, "Status")
    set_column_width(worksheet, 'V', 150)

    # Formatting first header row
    worksheet.format("A7:V7", {
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "WRAP",
        "borders": {
            "top": {"style": "SOLID"},
            "bottom": {"style": "SOLID"}
        },
        "textFormat": {
            "foregroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "fontSize": 11,
            "bold": True
        }
    })

    # Formatting second header row
    worksheet.format("A8:V8", {
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
        "wrapStrategy": "WRAP",
        "borders": {
            "top": {"style": "SOLID"},
            "bottom": {"style": "SOLID"}
        },
        "textFormat": {
            "foregroundColor": {
                "red": 0,
                "green": 0,
                "blue": 0
            },
            "fontSize": 11,
            "bold": True
        }
    })

    # Formatting borders
    worksheet.format("V7:V8", {"borders": {
        "left": {"style": "SOLID"},
        "right": {"style": "SOLID"},
        "bottom": {"style": "SOLID"},
        "top": {"style": "SOLID"}
    }})
    worksheet.format(
        "N7:N8", {"borders": {"right": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "top": {"style": "SOLID"}}})

    # Freeze the header
    set_frozen(worksheet, rows=8)

    print("Done", flush=True)


def upload_to_gsheet(worksheet, aps: list):
    i = 9
    for ap in aps:
        worksheet.update_cell(i, 1, ap['name'])
        worksheet.update_cell(i, 2, ap['location'])
        worksheet.update_cell(i, 3, ap['url']) if 'url' in ap.keys() else ""
        worksheet.update_cell(i, 4, ap['vendor'])
        worksheet.update_cell(i, 5, ap['model'])
        worksheet.update_cell(i, 6, ap['antennaModel'])
        worksheet.update_cell(i, 7, ap['antennaVendor'])
        worksheet.update_cell(i, 8, ap['installationType'])
        worksheet.update_cell(i, 9, str(ap['height']) + "m")
        worksheet.update_cell(i, 10, ap['antennaTilt'])
        worksheet.update_cell(i, 11, ap['bracket'])
        worksheet.update_cell(i, 12, ap['serviceLoop'])
        worksheet.update_cell(i, 13, ap['idf'])
        worksheet.update_cell(i, 14, ap['distanceToIDF'])
        worksheet.update_cell(i, 22, "To be installed")
        print(f"{ap['name']} details uploaded")
        time.sleep(14)
        i = i+1


def add_ap_table_borders(worksheet, nb_aps: int):
    design_cells = "N9:N"
    install_cells = "V9:V"
    row = 9

    for i in range(nb_aps):
        row = row+1
        i = i+1

    design_cells = design_cells + str(row)
    install_cells = install_cells + str(row)
    worksheet.format(design_cells, {"borders": {"right": {"style": "SOLID"}}})
    worksheet.format(install_cells, {"borders": {
                     "right": {"style": "SOLID"}, "left": {"style": "SOLID"}}})
    time.sleep(2)


def format_status_cell_validation(worksheet, nb_aps: int):
    cells = "V9:V" + str(nb_aps + 9)
    validation_rule = DataValidationRule(
        BooleanCondition('ONE_OF_LIST', ['To be installed', 'AP installed', 'AP provisionned']),
        showCustomUi=True)
    set_data_validation_for_cell_range(worksheet, cells, validation_rule)
    time.sleep(2)


def draw_ap_circle(image, ap_coord_x, ap_coord_y, ap_size):
    draw = ImageDraw.Draw(image)
    ulx = ap_coord_x - ap_size
    uly = ap_coord_y - ap_size
    lrx = ap_coord_x + ap_size
    lry = ap_coord_y + ap_size
    draw.ellipse((ulx, uly, lrx, lry), fill=(255, 0, 0), outline=(255, 0, 0))
    return (image)


def draw_coordinates(image: Image, img_height: int, cell_size_y: int, img_width: int, cell_size_x: int) -> Image:
    i = 0
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/Library/Fonts/Arial Black.ttf', 50)

    # Draw X Coordinate Names
    for i in range(int(img_width / cell_size_x + 1)):
        w_coord_x = cell_size_x * i + (cell_size_x / 2)
        draw.text((w_coord_x, 15), ascii_uppercase[i], (255, 0, 0), font=font)

    # Draw Y Coordinate Names
    for i in range(int(img_height / cell_size_y + 1)):
        h_coord_y = cell_size_y * i + (cell_size_y / 2)
        draw.text((10, h_coord_y), str(i), (255, 0, 0), font=font)

    return image


def calculate_height_cell_size(img_height: int, cell_size_x: int) -> int:
    x = img_height / cell_size_x
    mod = img_height % cell_size_x

    if mod > (cell_size_x / 2):
        adj = round((cell_size_x - mod) / round(x))
        cell_size_y = cell_size_x - adj
    else:
        adj = mod / round(x)
        cell_size_y = cell_size_x + adj

    return cell_size_y


def draw_map_coordinates(survey_file: str):
    """
    This function creates a copy of the floor plans.
    On this copy, it adds a grid of coordinates and label them.
    """
    print("Creating Floor Plan Grid Coordinates...")
    current_filename = pathlib.PurePath(survey_file).stem
    working_directory = os.getcwd()
    floorPlansImages = []
    resolution = 15

    # Load & Unzip the Ekahau Project File
    with zipfile.ZipFile(survey_file, 'r') as myzip:
        myzip.extractall(current_filename)

        # Load the floorPlans.json file into the floorPlans dictionary
        with myzip.open('floorPlans.json') as json_file:
            floorPlans = json.load(json_file)

        for floor in floorPlans['floorPlans']:
            floor_plan_image_path = os.getcwd() + '/' + current_filename + \
                '/image-' + floor['imageId']
            floorPlansImages.append({'path': floor_plan_image_path,
                                     'width': floor['width'], 'height': floor['height']})

    for floor in floorPlansImages:

        cell_size_x = round(floor['width'] / resolution)
        cell_size_y = calculate_height_cell_size(floor['height'], cell_size_x)

        nb_cell_x = round(floor['width'] / cell_size_x)
        nb_cell_y = round(floor['width'] / cell_size_y)

        image = Image.open(floor['path'])

        # Draw horizontal grid
        for i in range(nb_cell_x + 1):
            line = ImageDraw.Draw(image)
            line.line([((cell_size_x * i), 0), ((cell_size_x * i), floor['height'])],
                      fill='red', width=3)

            i = i + (floor['width'] / int(floor['width'] / cell_size_x))

        # Draw vertical grid
        for i in range(nb_cell_y + 1):

            line = ImageDraw.Draw(image)
            line.line([(0, (cell_size_y * i)), (floor['width'],
                                                (cell_size_y * i))], fill='red', width=3)

            i = i + (floor['height'] / int(floor['height'] / cell_size_y))

        # Draw last horizontal & vertical line
        line = ImageDraw.Draw(image)
        line.line([(floor['width']-1, 0), (floor['width']-1, floor['height']-1)], fill='red', width=3)
        line.line([(0, floor['height']-1), (floor['width']-1, floor['height']-1)], fill='red', width=3)

        # Draw Map Coordinates
        image = draw_coordinates(image, floor['height'], cell_size_y, floor['width'], cell_size_x)

        image.save(f"{floor['path']}-grid.png")


def create_ap_location_images(survey_file: str, aps: list) -> list:
    print("Creating AP Location Images...")

    current_filename = pathlib.PurePath(survey_file).stem
    working_directory = os.getcwd()

    # Load & Unzip the Ekahau Project File
    with zipfile.ZipFile(survey_file, 'r') as myzip:
        myzip.extractall(current_filename)

        # Load the accessPoints.json file into the accessPoints dictionary
        with myzip.open('accessPoints.json') as json_file:
            accessPoints = json.load(json_file)

        # Load the floorPlans.json file into the floorPlans dictionary
        with myzip.open('floorPlans.json') as json_file:
            floorPlans = json.load(json_file)

            # Create a new directory to place the new image in
            newpath = os.path.abspath(pathlib.PurePath()) + "/AP-Location-Images"
            if not os.path.exists(newpath):
                os.makedirs(newpath)

        for ap in accessPoints['accessPoints']:
            if 'location' in ap.keys():
                for floor in floorPlans['floorPlans']:
                    if ap['location']['floorPlanId'] == floor['id']:
                        image_full_path = os.getcwd() + '/' + current_filename + \
                            '/image-' + floor['imageId'] + '-grid.png'
                        dest = newpath + '/' + ap['name'] + '-location.png'
                        shutil.copy(image_full_path, dest)
                        image = Image.open(dest)
                        image = draw_ap_circle(
                            image, ap['location']['coord']['x'], ap['location']['coord']['y'], 20)
                        image.save(dest, quality=50)
                        for my_ap in aps:
                            if my_ap['name'] == ap['name']:
                                my_ap['locationImage'] = dest
                        print(f"{ap['name']} location image created")
            #         break
            # break

    return aps


def upload_images_to_gdrive(aps: list) -> list:
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    # Creating a folder to place all the AP Images in
    folder = drive.CreateFile(
        {'title': 'AP Location Images', 'mimeType': 'application/vnd.google-apps.folder'})
    folder.Upload()
    folder_id = folder['id']

    # Uploading all AP location images into that folder
    for ap in aps:
        if 'locationImage' in ap.keys():
            print(f"Uploading {ap['name']} location image to Google Drive... ", end="", flush=True)
            filename = ap['locationImage'].split('/')[-1]
            file_drive = drive.CreateFile({'title': filename, 'parents': [{'id': folder_id}]})
            file_drive.SetContentFile(ap['locationImage'])
            file_drive.Upload()
            ap['url'] = file_drive['embedLink']
            print("Done", flush=True)

    return aps


def main():
    parser = argparse.ArgumentParser(
        description='This script creates a Google Sheet with information required for AP installations')
    parser.add_argument('file', metavar='esx_file', help='Ekahau project file')
    args = parser.parse_args()

    client = connect_gsheet()
    worksheet = create_gsheet(
        client, "Wi-Fi AP Installation Details", ["fverges@semfionetworks.com"])
    # worksheet = open_gsheet(client, "Wi-Fi AP Installation Details")
    project_meta_data = retreive_project_meta_data(args.file, "fverges@semfionetworks.com")
    add_project_info(worksheet, project_meta_data)

    create_headers(worksheet)

    aps = retreive_ap_information(args.file)
    draw_map_coordinates(args.file)
    aps = create_ap_location_images(args.file, aps)
    aps = upload_images_to_gdrive(aps)

    # pprint(aps)
    format_status_cell_validation(worksheet, len(aps))
    add_ap_table_borders(worksheet, len(aps))
    upload_to_gsheet(worksheet, aps)


if __name__ == "__main__":
    start_time = time.time()
    print('** Creating Wi-Fi APs Installation Details Sheet...\n')
    main()
    run_time = time.time() - start_time
    print("\n** Time to run: %s sec" % round(run_time, 2))
