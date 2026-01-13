import boto3
import json
import os
import urllib.parse

s3 = boto3.client('s3')
textract = boto3.client('textract')
bedrock = boto3.client('bedrock-runtime', region_name='ap-south-1') # Ensure region matches

def handler(event, context):
    print("Received event:", json.dumps(event))

    # Get bucket and key from the S3 event
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    file_key = urllib.parse.unquote_plus(record['s3']['object']['key'])

    # Avoid infinite loops: Don't process the summary files we just created!
    if file_key.endswith("_summary.txt"):
        print("Skipping summary file.")
        return

    try:
        # 1. Extract Text
        extracted_text = ""
        
        # Simple extraction for .txt files
        if file_key.lower().endswith('.txt'):
            response = s3.get_object(Bucket=bucket_name, Key=file_key)
            extracted_text = response['Body'].read().decode('utf-8')
            
        # Textract for .pdf, .png, .jpg
        elif file_key.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            # Note: For multi-page PDFs, use start_document_text_detection (Async)
            # This 'detect_document_text' is synchronous and works for images/single-page docs
            # or simple PDFs.
            response = textract.detect_document_text(
                Document={'S3Object': {'Bucket': bucket_name, 'Name': file_key}}
            )
            for item in response['Blocks']:
                if item['BlockType'] == 'LINE':
                    extracted_text += item['Text'] + "\n"
        
        else:
            print("Unsupported file type")
            return

        if not extracted_text:
            print("No text found.")
            return

        # 2. Generate Summary with Bedrock
        prompt = f"Please provide a concise summary of the following text:\n\n{extracted_text}"
        
        # Prepare request for Amazon Titan Model
        native_request = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 512,
                "temperature": 0.5,
                "topP": 0.9
            }
        }
        
        request_body = json.dumps(native_request)
        
        bedrock_response = bedrock.invoke_model(
            modelId=os.environ.get('BEDROCK_MODEL_ID', 'amazon.titan-text-express-v1'),
            body=request_body
        )
        
        response_body = json.loads(bedrock_response['body'].read())
        summary = response_body['results'][0]['outputText']

        # 3. Save Summary back to S3
        # We append "_summary.txt" to the original filename
        summary_key = f"{file_key}_summary.txt"
        
        s3.put_object(
            Bucket=bucket_name,
            Key=summary_key,
            Body=summary,
            ContentType='text/plain'
        )
        
        print(f"Summary saved to {summary_key}")

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise e