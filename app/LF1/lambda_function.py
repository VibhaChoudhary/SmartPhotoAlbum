import json
import boto3
import logging
import base64
from datetime import datetime
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import os.path
import requests
import re
import os

logger = logging.getLogger('index-photos')
logger.setLevel(logging.DEBUG)

def extend_slot_type(labels):
    """Update the Lex search labels slot type with new labels for training purpose.
     Args:
         labels (list): detected labels list.
    """
    client = boto3.client('lex-models')
    response = client.get_slot_type(
        version='$LATEST',
        name='SearchLabels',
    )
    logger.debug('response slot type %s', response)
    values = []
    new_labels = set()
    for value in response['enumerationValues']:
        new_labels.add(value['value'])
    for label in labels:
        new_labels.add(label)
    for label in new_labels:    
        value = {'value' : label}
        values.append(value)
    response = client.put_slot_type(
        name='SearchLabels',
        description='Search terms for photo album',
        enumerationValues=values,
        checksum=response['checksum'],
    )
    logger.debug('response slot type %s', response)

def get_labels(image_json):
    """Generates a list of labels using Amazon Rekognition for the input image.
     Args:
         image_json (object): image object.
     Returns:
         list: labels detected in the image
     """
    client = boto3.client('rekognition')
    labels = []
    try:
        response = client.detect_labels(
            Image=image_json,
            MaxLabels=10,
            MinConfidence=85
        )
        logger.debug('Response from detect labels: %s', json.dumps(response))
    except Exception as e:
        logger.error('Exception occurred while detecting labels %s', str(e))
    else:
        for label in response['Labels']:
            labels.append(label['Name'])
    return labels


def upload_to_es(json_doc):
    """Uploads image metadata to elastic search
    Args:
       json_obj (json): image metadata.
    """
    # ak = os.environ['AWS_ACCESS_KEY_ID']
    # sk = os.environ['AWS_SECRET_ACCESS_KEY']
    # st = os.environ['AWS_SESSION_TOKEN']
    # region = 'us-east-1'
    # service = 'es'
    # awsauth = AWS4Auth(ak, sk, region, service, session_token=st)

    host = u'search-photos-s4cwptwn6oydgvpt63ms6s6k6m.us-east-1.es.amazonaws.com'
    doc = json.loads(json_doc)
    key = doc['objectKey']
    es = Elasticsearch(
        hosts=[{u'host': host, u'port': 443}],
        # http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        request_timeout=30
    )
    logger.debug(json_doc)
    res = es.index(index='photo_metadata', doc_type='image', id = key, body=doc)
    logger.debug(res)

def lambda_handler(event, context):
    records = event['Records']
    for record in records:
        # Get s3 details from event record
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        s3 = boto3.resource('s3')
        object_acl = s3.ObjectAcl(bucket,key)
        response = object_acl.put(ACL='public-read')
        logger.debug(json.dumps(response))
        
        # Get labels from rekognition
        image_json = {
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        }
        labels = get_labels(image_json)
        
        # Store information in elastic search
        json_doc = {
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "labels": labels
        }
        json_doc = json.dumps(json_doc)
        upload_to_es(json_doc)
        
        # Extend slot type values
        extend_slot_type(labels)
        
    return {
        'statusCode': 200,
        'body': json.dumps('Success from LF1')
    }
