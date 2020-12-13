import json
import boto3
import logging
import time
from datetime import datetime
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import os.path
import os
import requests

logger = logging.getLogger('index-photos')
logger.setLevel(logging.DEBUG)

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }
    
def query_es(labels):
    images = []
    # ak = os.environ['AWS_ACCESS_KEY_ID']
    # sk = os.environ['AWS_SECRET_ACCESS_KEY']
    # st = os.environ['AWS_SESSION_TOKEN']
    # region = 'us-east-1'
    # service = 'es'
    # awsauth = AWS4Auth(ak, sk, region, service, session_token=st)
    host = u'search-photos-s4cwptwn6oydgvpt63ms6s6k6m.us-east-1.es.amazonaws.com'
    es = Elasticsearch(
        hosts=[{u'host': host, u'port': 443}],
        # http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        request_timeout=30
    )
    query_body = {
        "query": {
            "terms": {
                "labels" : labels
            }
        }
    }
    try:
        response = es.search(index="photo_metadata", body=query_body)
        logger.debug("Response: %s", json.dumps(response))
        for image in response['hits']['hits']:
            image = json.dumps(image)
            image = json.loads(image)
            logger.debug("Response image: %s", image)
            url = "https://" + image['_source']['bucket'] + ".s3.amazonaws.com/" + image['_source']['objectKey']
            logger.debug('url: %s', url)
            photo = {
                'url' : url,
                'labels' : image['_source']['labels']
            }
            images.append(photo)
        logger.debug("Images found: %s", images)
    except Exception as e:
        logger.debug("Error while performing elastic search %s", e)
    return images


def get_response_from_lex(uid, text):
    client = boto3.client('lex-runtime')
    lex_response = client.post_text(
        botName ='SearchPhotos',
        botAlias = 'SPTest',
        userId = uid,
        inputText = text
    )
    return lex_response['message']

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }
    return response

def search_photos(intent_request):
    """
    Performs fulfillment for search photos.
    """
    # label = intent_request['currentIntent']['slots']['Label']
    source = intent_request['invocationSource']
    if source == 'DialogCodeHook':
        return delegate(intent_request['sessionAttributes'], intent_request['currentIntent']['slots'])
        
    slots = intent_request['currentIntent']['slots']
    slot_details = intent_request['currentIntent']['slotDetails']
    response = []
    labels = []
    if slots:
        if slots['Label_I']:
            labels.append(slots['Label_I'].lower())
            for resolution in slot_details['Label_I']['resolutions']:
                labels.append(resolution['value'].lower())
        if slots['Label_II']:
            labels.append(slots['Label_II'].lower())
            for resolution in slot_details['Label_II']['resolutions']:
                labels.append(resolution['value'].lower())    
    logger.debug('Labels extracted %s', labels)            
    response = query_es(labels)
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'CustomPayload',
                  'content': json.dumps(response)})


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """
    logger.debug("intent_request: %s", json.dumps(intent_request))
    intent_name = intent_request['currentIntent']['name']
    if intent_name == 'SearchIntent':
        logger.info("Search intent called")
        return search_photos(intent_request)


def lambda_handler(event, context):
    logger.debug("Event received: %s", json.dumps(event))
    if 'bot' in event:
        logger.info("Lex event received")
        os.environ['TZ'] = 'America/New_York'
        time.tzset()
        return dispatch(event)

    if 'queryStringParameters' in event:
        if event['queryStringParameters']:
            search_query = event['queryStringParameters']['q']
            res = get_response_from_lex('root', search_query)
            logger.debug("Response from lex %s", res)
            try:
                res = json.loads(res)
            except ValueError as e:
                value = json.dumps({'results':[]})  
            else:
                value = json.dumps({'results': res})
            return {
                'statusCode': 200,
                "headers":{ 'Access-Control-Allow-Origin' : '*', 'Access-Control-Allow-Headers' : 'Content-Type' },
                'body': value
            }
        
    return {
        'statusCode': 200,
        "headers":{ 'Access-Control-Allow-Origin' : '*', 'Access-Control-Allow-Headers' : 'Content-Type' },
        'body': json.dumps('Success from LF2')
    }