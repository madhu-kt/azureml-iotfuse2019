import datetime
import pytz
import math
import requests
import json
import os
import collections
import pandas as pd
import itertools
from functools import reduce
import operator
import random
import urllib.request
import json
from azure.storage.blob import BlockBlobService, PublicAccess
from azure.storage.blob import ContentSettings

RUL_ANALYTICS_CONTAINER = 'ruldemo'

from azure.storage.blob import BlockBlobService, PublicAccess
from azure.storage.blob import ContentSettings

STORAGE_ACCOUNT_NAME = '[ENTER STORAGE ACCOUNT NAME HERE]'
ACCOUNT_KEY='[ENTER ACCOUNT KEY HERE]'

sensorCols =['FanInletTemp','LPCOutletTemp','HPCOutletTemp','LPTOutletTemp','FanInletPres','BypassDuctPres','TotalHPCOutletPres','PhysFanSpeed','PhysCoreSpeed','EnginePresRatio','StaticHPCOutletPres','FuelFlowRatio','CorrFanSpeed','CorrCoreSpeed','BypassRatio','BurnerFuelAirRatio','BleedEnthalpy','DemandFanSpeed','DemandCorrFanSpeed','HPTCoolantBleed','LPTCoolantBleed']
redundantCols = ['BurnerFuelAirRatio','EnginePresRatio','DemandFanSpeed','FanInletPres','DemandCorrFanSpeed','FanInletTemp']

def initializeBlobService():
    return BlockBlobService(account_name=STORAGE_ACCOUNT_NAME, account_key=ACCOUNT_KEY)

def containerExists(container_name,container_service):
    # List containers                                                                                                                                                                 
    generator = container_service.list_containers()
    if container_name in [container.name for container in generator]:
        return True
    return False

def loadTSDataFromBlobStorage(block_blob_service):
    container_name = RUL_ANALYTICS_CONTAINER
    generator = block_blob_service.list_blobs(container_name)
    full_path = 'RUL_test_FD001.csv'
    local_file_name = '/tmp/RUL_test_FD001.csv'
    if full_path not in [blob.name for blob in generator]:
        print("Blob not found in path %s!"%full_path)
        return None
    else:
        #Download CSV file from Azure cloud
        block_blob_service.get_blob_to_path(container_name,
                                            full_path,
                                            local_file_name)
        print("Blob downloaded to: %s. Reading file..."%local_file_name)
        return pd.read_csv(local_file_name)

def getTrainingStats(block_blob_service):
    container_name = RUL_ANALYTICS_CONTAINER
    generator = block_blob_service.list_blobs(container_name)
    full_path = 'pm_model_eval.csv'
    local_file_name = '/tmp/pm_model_eval.csv'
    if full_path not in [blob.name for blob in generator]:
        print("Blob not found in path %s!"%full_path)
        return None
    else:
        #Download CSV file from Azure cloud
        block_blob_service.get_blob_to_path(container_name,
                                            full_path,
                                            local_file_name)
        print("Blob downloaded to: %s. Reading file..."%local_file_name)
        return pd.read_csv(local_file_name)

def getUnitList(data):
    return list(np.unique(data['UnitNumber']))

def getUnitTS(data, unitNumber):
    return data[data['UnitNumber']==unitNumber]

def getLatestTS(data,unitNumber,nCycles=None):
    sensorTS = data[data['UnitNumber']==unitNumber].set_index('Cycle').sort_index()
    return sensorTS

def getPredictedAlert(data,unitNumber):
    nCycles = 5
    windowSize = 5
    sensorTS = getLatestTS(data,unitNumber,nCycles).reset_index()
    newSensorCols = [c for c in sensorCols if c not in redundantCols]
    FETestData = sensorTS[['UnitNumber']+newSensorCols]
    # apply rolling mean window
    MASensorCols = [c+'_MA' for c in newSensorCols]
    SDSensorCols = [c+'_SD' for c in newSensorCols]
    grouped = FETestData.groupby('UnitNumber')
    # this works for pandas version 0.18
    for col in newSensorCols:
        FETestData['%s_MA'%col] = grouped[col].apply(lambda g: g.rolling(window=windowSize, min_periods=0).mean())
        FETestData['%s_SD'%col] = grouped[col].apply(lambda g: g.rolling(window=windowSize, min_periods=0).mean())
        
    df = FETestData.tail(1).reset_index().drop(["index","UnitNumber"],axis=1).astype(float).astype(str)
    dataDict = df.to_dict(orient='index')[0]
    dataDict['label']='0'
    
    data = {
        "Inputs": {
            "input_data":
            [
                dataDict
            ],
        },
        "GlobalParameters":  {
        }
    }
    
    body = str.encode(json.dumps(data))
    url = 'https://ussouthcentral.services.azureml.net/workspaces/fe1a6222af3547dda7a03e12a0fbdde0/services/d3ffda6df41447b296634cf43a1d7976/execute?api-version=2.0&format=swagger'
    api_key = 'nSe7bGCM2qGYMuTWK1Soa0WQ5AZjsOnpM9Um4aaOiN8mT/WxFQpc/N0QLG6J/obUjSv+BlRDepZsxEtUWivjlQ==' # Replace this with the API key for the web service
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key)}
    
    req = urllib.request.Request(url, body, headers)
    
    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode(response.info().get_param('charset') or 'utf-8'))['Results']['prediction'][0]
        #return {key:float(val) for key,val in result.items()}
        return int(result['Scored Labels'])
    
    except urllib.error.HTTPError as error:
        print("The request failed with status code: " + str(error.code))
        
        # Print the headers - they include the request ID and the timestamp, which are useful for debugging the failure
        print(error.info())
        print(json.loads(error.read().decode("utf8", 'ignore')))   
