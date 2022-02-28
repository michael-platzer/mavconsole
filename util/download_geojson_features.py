#!/usr/bin/env python3

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# get access token
token_url  = 'https://map.dronespace.at/oauth/token'
token_auth = ('AustroDroneWeb', 'AustroDroneWeb')
token_data = {'grant_type': 'client_credentials'}
req = requests.post(token_url, auth=token_auth, data=token_data, verify=False)
assert req.status_code == 200, f"token request status {req.status_code}"
token = req.json()['access_token']

def ows_request(url, token, typename, dt_start, dt_end):
    feature_req = ET.Element('GetFeature', {
        'xmlns':              "http://www.opengis.net/wfs",
        'service':            "WFS",
        'version':            "1.1.0",
        'outputFormat':       "application/json",
        'xsi:schemaLocation': "http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd",
        'xmlns:xsi':          "http://www.w3.org/2001/XMLSchema-instance",
        'viewParams':         f"window_start:{dt_start.strftime(time_format)};window_end:{dt_end.strftime(time_format)}"
    })
    #ET.SubElement(feature_req, 'Query', {'typeName': typename, 'srsName': "EPSG:3857"})
    ET.SubElement(feature_req, 'Query', {'typeName': typename, 'srsName': "EPSG:4326"})
    feature_req = ET.tostring(feature_req, encoding='utf8')
    req_headers = {
        'Content-Type':  'text/xml;charset=UTF-8',
        'Authorization': f"Bearer {token}"
    }
    req = requests.post(url, headers=req_headers, data=feature_req, verify=False)
    assert req.status_code == 200, f"feature request status {req.status_code}"
    return req.text

dt_start = datetime.now(timezone.utc)
dt_end   = datetime(
    dt_start.year, dt_start.month, dt_start.day, tzinfo=timezone.utc
) + timedelta(days=0, seconds=3600*24-1, milliseconds=999)
time_format = '%Y-%m-%dT%H:%M:%S.000Z'

ows_url  = 'https://map.dronespace.at/ows'
with open('airspace.geojson', 'w') as f:
    f.write(ows_request(ows_url, token, 'airspace', dt_start, dt_end))
with open('uaszone.geojson', 'w') as f:
    f.write(ows_request(ows_url, token, 'uaszone' , dt_start, dt_end))
