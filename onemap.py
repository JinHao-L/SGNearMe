import requests
import logging
import json
import math
import importlib

from geopy import distance
from datetime import datetime

import config

# theme name -> theme code
themesMap = {
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

def getAccessToken(email : str, password : str) -> str:
    dt = datetime.now()
    timestamp = dt.timestamp()
    if (config.expiry_timestamp < timestamp) :
        # refresh access token
        logging.info("Updating access token")
        loginCredentials = {"email": email, "password": password}

        response = requests.post("https://developers.onemap.sg/privateapi/auth/post/getToken", loginCredentials)
        result = response.json()

        if (response.status_code == 200) :
            logging.info("Token expiry on " + result["expiry_timestamp"])
            updateConfigFile(result["access_token"], int(result["expiry_timestamp"]))
            return result["access_token"]
        else :
            raise Exception(result["error"])


    return config.access_token

def updateConfigFile(token: str, timestamp: int) -> None :
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

def getNearbyPlaces(searchTerm: str, lat : float, lng: float) -> str:

    if (searchTerm not in themesMap) :
        return "This search theme is currently not available"

    theme = themesMap[searchTerm]

    token = getAccessToken(config.email, config.password)

    queryString = {"queryName": theme, "token" : token, "extents" : getBoundary(lat, lng)}

    url = "https://developers.onemap.sg/privateapi/themesvc/retrieveTheme"
    response = requests.get(url, params=queryString)
    result = json.loads(response.text)

    if (response.status_code == 200) :
        return parsePlaces(result, (lat, lng), searchTerm)
    else :
        logging.error(str(response.status) + ", " + response.text)
        return result["error"]


def getBoundary(lat: float, lng: float) -> str:
    # radius of 2.5 km
    offset = 2.5 / 100.0
    latMax = lat + offset
    latMin = lat - offset

    lngOffset = offset * math.cos(lat * math.pi / 180.0)
    lngMax = lng + lngOffset
    lngMin = lng - lngOffset

    result = str(latMin) + "," + str(lngMin) + "," + str(latMax) + "," + str(lngMax)
    return result

def getDistance(pos1: (float, float), pos2: (float, float)) -> float :
    return distance.distance(pos1, pos2).km

usefulDescriptions = {"Tourist Spot", "Parks", "Gyms", "CHAS Clinics", "Museums", "Monuments", "Historic Sites", "Fire Station"}
def parsePlaces(response : json, pos: (float, float), name : str) -> str:
    places = response["SrchResults"]
    if ("ErrorMessage" in places[0]) :
        return "Search term not available"

    logging.info("Found " + str(places[0]["FeatCount"]) + " results for " + name)
    if (places[0]["FeatCount"] == 0) :
        return "No " + name.lower() + " found in a ~2.5km radius"

    output = []
    for place in places[1:]:
        try :
            distance = getDistance(pos, place["LatLng"].split(","))

            resultString = ""
            resultString = "<b>{}</b> ({:.2f}km)\n".format(place["NAME"].title(), distance)

            if ("DESCRIPTION" in place and name in usefulDescriptions) :
                if (name == "CHAS Clinics") :
                    resultString += "<i>{}</i>\n---\n".format(place["DESCRIPTION"].replace(",", ", "))
                else :
                    resultString += "<i>{}</i>\n---\n".format(place["DESCRIPTION"])

            if ("ADDRESSBLOCKHOUSENUMBER" in place and place["ADDRESSBLOCKHOUSENUMBER"]) :
                resultString += "Blk " + place["ADDRESSBLOCKHOUSENUMBER"].strip().upper().replace("BLK", "").replace("BLOCK", "") + ", "

            if ("ADDRESSSTREETNAME" in place and place["ADDRESSSTREETNAME"]) :
                resultString += place["ADDRESSSTREETNAME"].strip().title() + ", "

            if ("ADDRESSUNITNUMBER" in place and place["ADDRESSUNITNUMBER"]) :
                resultString += place["ADDRESSUNITNUMBER"].strip() + ", "

            if ("ADDRESSBUILDINGNAME" in place and place["ADDRESSBUILDINGNAME"]) :
                resultString += place["ADDRESSBUILDINGNAME"].strip().title() + ", "

            if ("ADDRESSPOSTALCODE" in place and place["ADDRESSPOSTALCODE"]) :
                resultString += "S" + place["ADDRESSPOSTALCODE"]

            if (resultString.endswith(", ")) :
                resultString = resultString[:-2] + "\n"
            elif (not resultString.endswith("\n")) :
                resultString += "\n"

            if ("HYPERLINK" in place and place["HYPERLINK"]) :
                resultString += "[<a href=\"{}\">Link</a>] ".format(place["HYPERLINK"])

            resultString += "[<a href=\"http://www.google.com/maps/place/{}\">Map</a>] ".format(place["LatLng"])

            output.append((resultString + "\n", distance))
        except Exception as e:
            logging.warning(e)
            continue

    output = sorted(output, key = lambda place : place[1])

    resultString = ""
    # display only top 8 results
    for idx, place in enumerate(output[: 8]):
        resultString += str(idx + 1) + ". " + place[0] + "\n"

    return resultString

def getMapUrl(lat: float, lng: float) :
    url = 'https://developers.onemap.sg/commonapi/staticmap/getStaticImage?layerchosen={0}&lat={1}&lng={2}&zoom={3}&height={4}&width={5}'
    return url.format("night", lat, lng, 17, 512, 512);
