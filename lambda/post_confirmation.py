import boto3
import os
import time

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['USER_TABLE_NAME']
table = dynamodb.Table(table_name)

def handler(event, context):
    """
    Triggered by Cognito PostConfirmation Event.
    """
    print(f"Received event: {event}")

    try:
        # 1. Extract details from the Cognito event
        request = event['request']
        user_attributes = request['userAttributes']
        
        # 'sub' is the unique User ID in Cognito
        user_id = user_attributes.get('sub')
        email = user_attributes.get('email')
        
        # 2. Check source (Google vs Email) to get correct name
        # Google often passes 'name', standard sign up might use 'given_name'
        name = user_attributes.get('name') or user_attributes.get('given_name') or "No Name"

        # 3. Prepare Item for DynamoDB
        item = {
            'userId': user_id,
            'email': email,
            'name': name,
            'authSource': event['userName'], # Helps distinguish Google vs User/Pass
            'createdAt': int(time.time()),
            'status': 'ACTIVE'
        }

        # 4. Write to DynamoDB
        # ConditionExpression prevents overwriting if it already exists (idempotency)
        table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(userId)'
        )
        print(f"Successfully stored user {user_id}")

    except Exception as e:
        # Log error but don't fail the flow, or the user won't be able to log in
        print(f"Error storing user details: {str(e)}")
    
    # Cognito expects the event to be returned
    return event