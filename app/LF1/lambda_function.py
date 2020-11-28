def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps('Success from LF1')
    }