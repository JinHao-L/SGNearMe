import requests
import logging
import json
import math
import importlib

from geopy import distance
from datetime import datetime

import config

"""Map of theme names to theme codes (based on OneMap API)"""
themesmap = {
    "Preschools": "preschools_location",
    "Kindergartens": "kindergartens",
    "Private Education": "cpe_pei_premises",
    "CET Centres": "cetcentres",
    "Libraries": "libraries",

    "Tourist Spot": "tourism",
    "Hotels": "hotels",
    "Parks": "nationalparks",

    "Hawker Centres": "hawkercentre",
    "Childcare": "childcare",
    "Supermarkets": "supermarkets",
    "Money Changer": "moneychanger",
    "Gyms": "exercisefacilities",
    "RC": "residentscommittee",
    "CC": "communityclubs",

    "Hospitals": "moh_hospitals",
    "Pharmacy": "registered_pharmacy",
    "CHAS Clinics": "moh_chas_clinics",

    "AEDs": "aed_locations",
    "Police Station": "spf_establishments",
    "Fire Station": "firestation",

    "Museums" : "museum",
    "Monuments" : "monuments",
    "Historic Sites" : "historicsites",
}

"""Theme names that contains useful descriptions"""
usefuldescriptions = {
    "Tourist Spot",
    "Parks", "Gyms",
    "CHAS Clinics",
    "Museums",
    "Monuments",
    "Historic Sites",
    "Fire Station"
 }


def get_access_token(email : str, password : str) -> str:
    """Retrieve access token"""
    dt = datetime.now()
    timestamp = dt.timestamp()

    # refresh access token if expired
    if (config.expiry_timestamp < timestamp) :
        logging.info("Updating access token")
        loginCredentials = {"email": email, "password": password}
        url = "https://developers.onemap.sg/privateapi/auth/post/getToken"

        response = requests.post(url, loginCredentials)
        result = response.json()

        if (response.status_code == 200) :
            logging.info("New token expiry on " + result["expiry_timestamp"])
            # update config file with new token
            update_config_file(result["access_token"], int(result["expiry_timestamp"]))
            return result["access_token"]
        else :
            raise Exception(result["error"])

    return config.access_token

def update_config_file(token: str, timestamp: int) -> None :
    """Read config.py file and update it with new token"""
    lines = None
    with open("config.py", 'r') as cfgr:
        lines = cfgr.readlines()

    for i in range(len(lines)) :
        if ( lines[i][:15] == "access_token = " ) :
            lines[i] = "access_token = \"" + token + "\"\n"
        elif ( lines[i][:19] == "expiry_timestamp = " ) :
            lines[i] = "expiry_timestamp = " + str(timestamp) + "\n"

    with open("config.py", "w") as cfgw:
        cfgw.writelines(lines)

    logging.info("Config file successfully updated with new access token")
    importlib.reload(config)

def get_nearby_places(searchterm: str, lat : float, lng: float) -> str:
    """Get top 8 places near (lat, lng) as a String"""
    if (searchterm not in themesmap) :
        return "This search theme is currently not available"

    # Get theme code from theme name
    theme = themesmap[searchterm]

    token = get_access_token(config.email, config.password)

    queryString = {"queryName": theme, "token" : token, "extents" : get_bounding_box(lat, lng, 2.5)}

    url = "https://developers.onemap.sg/privateapi/themesvc/retrieveTheme"
    response = requests.get(url, params=queryString)
    result = json.loads(response.text)

    if (response.status_code == 200) :
        return parse_places(result, (lat, lng), searchterm)
    else :
        logging.error(str(response.status) + ", " + response.text)
        return result["error"]


def get_bounding_box(lat: float, lng: float, radius: float) -> str:
    """Get bounding box with length of radius * 2 and (lat, lng) as the centre"""
    offset = radius / 100.0
    latMax = lat + offset
    latMin = lat - offset

    lngOffset = offset * math.cos(lat * math.pi / 180.0)
    lngMax = lng + lngOffset
    lngMin = lng - lngOffset

    result = str(latMin) + "," + str(lngMin) + "," + str(latMax) + "," + str(lngMax)
    return result

def get_distance(pos1: (float, float), pos2: (float, float)) -> float :
    """Get distance between two position with format (lat, lng)"""
    return distance.distance(pos1, pos2).km

def parse_places(response : json, pos: (float, float), name : str) -> str:
    """Parse json response to output string of the top 8 places"""
    places = response["SrchResults"]

    if ("ErrorMessage" in places[0]) :
        logging.error("Invalid theme code for " + name)
        return "Search term not available"

    logging.info("Found " + str(places[0]["FeatCount"]) + " results for " + name)

    if (places[0]["FeatCount"] == 0) :
        # No result
        return "No " + name.lower() + " found in a ~2.5km radius"

    output = []
    for place in places[1:]:
        try :
            distance = get_distance(pos, place["LatLng"].split(","))

            resultstring = ""
            resultstring = "<b>{}</b> ({:.2f}km)\n".format(place["NAME"].title(), distance)

            if ("DESCRIPTION" in place and name in usefuldescriptions) :
                if (name == "CHAS Clinics") :
                    resultstring += "<i>{}</i>\n---\n".format(place["DESCRIPTION"].replace(",", ", "))
                else :
                    resultstring += "<i>{}</i>\n---\n".format(place["DESCRIPTION"])

            if ("ADDRESSBLOCKHOUSENUMBER" in place and place["ADDRESSBLOCKHOUSENUMBER"]) :
                resultstring += "Blk " + place["ADDRESSBLOCKHOUSENUMBER"].strip().upper().replace("BLK", "").replace("BLOCK", "") + ", "

            if ("ADDRESSSTREETNAME" in place and place["ADDRESSSTREETNAME"]) :
                resultstring += place["ADDRESSSTREETNAME"].strip().title() + ", "

            if ("ADDRESSUNITNUMBER" in place and place["ADDRESSUNITNUMBER"]) :
                resultstring += place["ADDRESSUNITNUMBER"].strip() + ", "

            if ("ADDRESSBUILDINGNAME" in place and place["ADDRESSBUILDINGNAME"]) :
                resultstring += place["ADDRESSBUILDINGNAME"].strip().title() + ", "

            if ("ADDRESSPOSTALCODE" in place and place["ADDRESSPOSTALCODE"]) :
                resultstring += "S" + place["ADDRESSPOSTALCODE"]

            if (resultstring.endswith(", ")) :
                resultstring = resultstring[:-2] + "\n"
            elif (not resultstring.endswith("\n")) :
                resultstring += "\n"

            if ("HYPERLINK" in place and place["HYPERLINK"]) :
                resultstring += "[<a href=\"{}\">Link</a>] ".format(place["HYPERLINK"])

            resultstring += "[<a href=\"http://www.google.com/maps/place/{}\">Map</a>] ".format(place["LatLng"])

            output.append((resultstring + "\n", distance))
        except Exception as e:
            logging.warning(e)
            continue

    # Sort results by distance from pos
    output = sorted(output, key = lambda place : place[1])

    # Get only top 8 results
    top8 = ""
    for idx, place in enumerate(output[: 8]):
        top8 += str(idx + 1) + ". " + place[0] + "\n"

    return top8

def getMapUrl(lat: float, lng: float) :
    """Get static map url based on position"""
    url = 'https://developers.onemap.sg/commonapi/staticmap/getStaticImage?layerchosen={0}&lat={1}&lng={2}&zoom={3}&height={4}&width={5}'
    # default of map type "night", zoom 17, size of (512, 512)
    return url.format("night", lat, lng, 17, 512, 512);
