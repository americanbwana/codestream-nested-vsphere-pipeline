import requests
import logging
import os 
import json 
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time 

logging.basicConfig(level=logging.INFO)

# retry strategy to tolerate API errors.  Will retry if the status_forcelist matches.
retry_strategy = Retry (
    total=5,
    status_forcelist=[429, 500, 502, 503, 504],
    method_whitelist=["PATCH", "GET", "POST", "DELETE"],
    backoff_factor=2,
    raise_on_status=True,
)


adapter = HTTPAdapter(max_retries=retry_strategy)
https = requests.Session()
https.mount("https://", adapter)

vRacUrl = "https://api.mgmt.cloud.vmware.com"

def PostBearerToken_session(refreshToken):
    '''
    Function to return the bearer token and other required headers

    Param: refreshToken.  vRAC refresh token

    Returns:
        headers: JSON containing the headers, including the bearer token

    '''

    pl = {}
    pl['refreshToken'] = refreshToken.replace('\n', '')
    # logging.info('payload is ' + json.dumps(pl))
    loginURL = vRacUrl + "/iaas/api/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
        }
    r = https.post(loginURL, json=pl, headers=headers)
    responseJson = r.json()
    token = "Bearer " + responseJson["token"]
    headers['Authorization']=token
    return headers 

def PostvRac_sessions(requestUrl, headers, requestPayload):
    '''
    Function to POST data to the vRAC API.

    Params:
        requestUrl: URL to post to.
        headers: Headers including the bearer token.
        requestPayload: Payload to post, if any.

    Returns:
        responseJson: Json returned from the request.
    '''

    requestUrl=vRacUrl + requestUrl  
    logging.info('PostRequestUrl: ' + requestUrl)
    logging.info('requestPayload ' + str(requestPayload))
    adapter = HTTPAdapter(max_retries=retry_strategy)
    https = requests.Session()
    https.mount("https://", adapter)
    r = requests.post(requestUrl,headers=headers, json=requestPayload)
    responseCode=r.status_code
    logging.info('Post response code ' + str(responseCode))
   
    responseJson = r.json()
    return responseJson

   
def GetFilteredVrac_sessions(requestUrl, headers, requestFilter):
    '''
    Function to GET data from vRAC using a filter

    Params:
        requestUrl: URL to post to.
        headers: Headers including the bearer token.
        requestFilter: Filter to append to the request

    Returns:
        responseJson: Json returned from the request.


    '''
    # Get a thing using a filter
    requestUrl=vRacUrl + requestUrl + requestFilter
    print(requestUrl)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    https = requests.Session()
    https.mount("https://", adapter)
    r = https.get(requestUrl, headers=headers)
    responseJson = r.json()
    return responseJson

def GetVrac_sessions(requestUrl, headers):
    '''
    Function to go a generic vRAC request. 

    Params:
        requestUrl: URL to post to.
        headers: Headers including the bearer token.
        requestPayload: Payload to post, if any.

    Returns:
        responseJson: Json returned from the request.

    '''
    # Bulk get without filters
    requestUrl=vRacUrl + requestUrl
    print(requestUrl)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    https = requests.Session()
    https.mount("https://", adapter)
    r = https.get(requestUrl, headers=headers)
    responseJson = r.json()
    return responseJson

def PatchVrac_sessions(requestUrl, headers, requestPayload):
    '''
    Function to patch a vRAC entity (i.e., Image Profiles)

    Params:
        requestUrl: URL to post to.
        headers: Headers including the bearer token.
        requestPayload: Payload to post, if any.

    Returns:
        responseJson: Json returned from the request.

    '''
    # Patch a thing
    requestUrl=vRacUrl + requestUrl
    print(requestUrl)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    https = requests.Session()
    https.mount("https://", adapter)
    r = https.patch(requestUrl, headers=headers, json=requestPayload)
    responseJson = r.json()
    return responseJson

def DeleteVrac_sessions(requestUrl, headers, requestPayload):
    '''
    Function to DELETE a vRAC entity

    Params:
        requestUrl: URL to post to.
        headers: Headers including the bearer token.
        requestPayload: Payload to post, if any.

    Returns:
        responseCod: Response code

    '''
    # Delete a thing
    requestUrl=vRacUrl + requestUrl
    print(requestUrl)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    https = requests.Session()
    https.mount("https://", adapter)
    r = https.patch(requestUrl, headers=headers, json=requestPayload)
    responseCode = r.status_code
    return responseCode

def getImageDataByExternalRegionId(externalRegionId, newImages):
    '''
    Return the new image json for the region
    Params:
        externalRegionId (string) : The externalRegionId
        newImages(JSON/Array) : The image data for the recently built fabric images

    Returns: 
        result (JSON/Array) : The name, Id, and imageName for each image.

    '''
    # Get the new image 
    result = []   
    for item in newImages['content']:
        logging.info("region Ids " + item['externalRegionId'] + " input " + externalRegionId)
        if item['externalRegionId'] == externalRegionId:
            logging.info('Found match by externalRegionId')
            # logging.info("Item " + str(item))
            name = item['name']
            nameSplit = name.split("-")
            # imageName should match the profile to update
            imageName = nameSplit[0] + "-" + nameSplit[1]
            result.append({'id': item['id'],'name': item['name'], 'imageName': imageName})
    return result


def patchImageProfiles(imageProfilesJson, newImages, addTestMappings, updateProdMappings):
    '''
    Function to update the image profiles for regions based on the externalRegionId

    Params:
        imagesProfilesJson (JSON/Array) : The image profiles for all the regions with matching image mapping names
        newImages (JSON/Array)  : The newly created and discovered fabric images
        addTestMappings (boolean) : Add test mappings
        updateProdMappings (boolean) : Update the production image mappings matching Packer-Build-Images.
                                        This must be set as a pipeline variable. 

    Returns:
        None
    '''

    for profile in imageProfilesJson:
        logging.info('The profile name is ' + profile['name'])
        logging.info('The externalRegionId ' + profile['externalRegionId'])
        # logging.info('The profileJson: ' + json.dumps(profile))
        # get the image data for the matching externalRegionId
        imagesResult = getImageDataByExternalRegionId(profile['externalRegionId'],newImages)
        logging.info("imageResult " + json.dumps(imagesResult))
        # 
        requestUrl = '/iaas/api/image-profiles/' + profile['id']
        logging.info('requestUrl: ' + requestUrl)
        profilePayload = {}    
        # get the region id
        regionHref=profile['_links']['region']['href']
        regionId=regionHref.split('/')[4]      
    
        newMapping = {}
        # add imageMapping
        profilePayload['imageMapping']=newMapping
        # copy original mappings over
        for mappings in profile['imageMappings']['mapping']:
            # logging.info('Current mapping: ' + json.dumps(mappings))
            # currentMapping is the mapping name 
            currentMapping = json.dumps(mappings)
            mapping={}
            
            profilePayload['imageMapping'][mappings]=mapping
            # copy over the common values 
            profilePayload['name']=profile['name']
            profilePayload['description']=profile['name'] + "--CS-Generated-Image-Profile"
            profilePayload['regionId']=regionId
            profilePayload['imageMapping'][mappings]['name']=profile['imageMappings']['mapping'][mappings]['name']
            # update the description
            profilePayload['imageMapping'][mappings]['description']=profile['imageMappings']['mapping'][mappings]['name']
            # Keep the original image Id
            profilePayload['imageMapping'][mappings]['id']=profile['imageMappings']['mapping'][mappings]['id']
            # Log the original image mapping for a region.  Just in case the update breaks some thing
            logging.info("**************************************")
            logging.info("The original image mapping payload for " + profile['externalRegionId'])
            logging.info(json.dumps(profilePayload))
            logging.info("**************************************")
            if updateProdMappings:
                # Update the production image mappings if set to true
                # Now update the prod mappings by imageName. 
                for item in imagesResult:
                    if '"' + item['imageName'] + '"' == currentMapping:
                        logging.info("Updating imageMapping - " + currentMapping)
                        profilePayload['imageMapping'][mappings]['name']=item['name']
                        # update the description
                        profilePayload['imageMapping'][mappings]['description']=item['name']
                        # Keep the original image Id
                        profilePayload['imageMapping'][mappings]['id']=item['id']
            elif addTestMappings:
                # Add test image mappings if set to true
                # add new test mappings by externalRegionId
                for image in newImages['content']:
                    # print(image['externalRegionId'])
                    if image['externalRegionId'] == profile['imageMappings']['mapping'][mappings]['externalRegionId']:
                        # print('They match')
                        # add the test mappings
                        # new mapping name
                        newMapping = {}
                        newMappingName =image['name']
                        profilePayload['imageMapping'][newMappingName]=newMapping
                
                        profilePayload['imageMapping'][newMappingName]['name']=image['name']
                        profilePayload['imageMapping'][newMappingName]['description']=image['name']
                        profilePayload['imageMapping'][newMappingName]['id']=image['id']
                
        # mappings is existing mapping
        logging.info('The new profile payload for ' + profile['externalRegionId'] + " is :: " + json.dumps(profilePayload))
        # Patch the Profile
        # authHeaders will have all of the required headers, including the bearerToken
        authHeaders=vRAC.PostBearerToken_session(refreshToken)
        # Now to patch the imageProfile
        requestResponse = vRAC.PatchVrac_sessions(requestUrl, authHeaders, profilePayload)
        # responseId=requestResponse['id']
    return None