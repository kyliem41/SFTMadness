import json
import os
import psycopg2
from datetime import datetime, date
import boto3
import base64
import jwt
from botocore.exceptions import ClientError
from psycopg2.extras import RealDictCursor
import requests
from jwt import algorithms
import uuid
import re

def cors_response(status_code, body, content_type="application/json"):
    headers = {
        'Content-Type': content_type,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE',
    }

    if content_type == "application/json":
        body = json.dumps(body, default=str)

    return {
        'statusCode': status_code,
        'body': body,
        'headers': headers,
    }

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return cors_response(200, "ok")
    
    http_method = event['httpMethod']
    resource_path = event['resource']
    
    try:
        #verify token
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return cors_response(401, "Unauthorized")
        
        token = auth_header.split(' ')[-1]
        verify_token(token)

    except Exception as e:
        return cors_response(401, "Authentication failed")
        
    #routes with authentication
    try:
        if resource_path == '/scrapedFiles' and http_method == 'POST':
            return uploadFile(event, context)
        elif resource_path == '/scrapedFiles/{fileId}' and http_method == 'GET':
            return getFile(event, context)
        elif resource_path == '/scrapedFiles/{fileId}' and http_method == 'DELETE':
            return deleteFile(event, context)
        else:
            return cors_response(404, "Not Found")
        
    except Exception as e:
        return cors_response(500, str(e))
    
###################
#helper functions

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def get_db_connection():
    return psycopg2.connect(
        dbname=os.environ['DB_NAME'],
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ['DB_PORT'],

        connect_timeout=5)
    
#AUTH
def is_token_invalidated(token_payload):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            jti = token_payload.get('jti')
            
            if not jti:
                raise Exception("Token missing jti claim")
            
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 
                    FROM invalidated_tokens 
                    WHERE jti = %s
                )
            """, (jti,))
            
            return cur.fetchone()[0]
        
def verify_token(token):
    # Get the JWT token from the Authorization header
    if not token:
        raise Exception('No token provided')

    region = boto3.session.Session().region_name
    
    # Get the JWT kid (key ID)
    headers = jwt.get_unverified_header(token)
    kid = headers['kid']

    # Get the public keys from Cognito
    url = f'https://cognito-idp.{region}.amazonaws.com/{os.environ["COGNITO_USER_POOL_ID"]}/.well-known/jwks.json'
    response = requests.get(url)
    keys = response.json()['keys']

    # Find the correct public key
    public_key = None
    for key in keys:
        if key['kid'] == kid:
            public_key = algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            break

    if not public_key:
        raise Exception('Public key not found')

    # Verify the token
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=os.environ['COGNITO_CLIENT_ID'],
            options={"verify_exp": True}
        )

        if is_token_invalidated(payload):
            raise Exception('Token has been invalidated')
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')

####################
#scrapedFiles functions

def uploadFile(event, context):
    conn = None
    try:
        auth_header = event.get('headers', {}).get('Authorization')
        token = auth_header.split(' ')[-1]
        token_payload = verify_token(token)
        cognito_user_id = token_payload.get('sub')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id FROM users WHERE cognito_id = %s", (cognito_user_id,))
        db_user = cur.fetchone()
        if not db_user:
            return cors_response(404, "User not found")
        user_id = db_user['id']

        try:
            content_type = event['headers'].get('Content-Type', '')

            if not content_type:
                for header_key in event['headers']:
                    if header_key.lower() == 'content-type':
                        content_type = event['headers'][header_key]
                        break

            print(f"Detected Content-Type: {content_type}")

            if 'multipart/form-data' not in content_type.lower():
                return cors_response(400, "Content-Type must be multipart/form-data")
                
            boundary = None
            if 'boundary=' in content_type:
                boundary = content_type.split('boundary=')[1].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]
                elif boundary.startswith("'") and boundary.endswith("'"):
                    boundary = boundary[1:-1]
            else:
                parts = content_type.split(';')
                for part in parts:
                    if 'boundary' in part.lower():
                        boundary = part.split('=')[1].strip()
                        if boundary.startswith('"') and boundary.endswith('"'):
                            boundary = boundary[1:-1]
                        elif boundary.startswith("'") and boundary.endswith("'"):
                            boundary = boundary[1:-1]
                        break
            
            if not boundary:
                body = event.get('body', '')
                if event.get('isBase64Encoded', False):
                    body = base64.b64decode(body)
                
                if isinstance(body, bytes):
                    body = body.decode('utf-8', errors='replace')
                
                boundary_matches = re.findall(r'--+[\w-]+', body[:1000])
                if boundary_matches:
                    boundary = boundary_matches[0][2:]
                    print(f"Auto-detected boundary from body: {boundary}")
                    
            if not boundary:
                return cors_response(400, "Cannot detect boundary in the multipart request")
                
            print(f"Using boundary: {boundary}")

            body = event.get('body', '')
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(body)
            
            if isinstance(body, bytes):
                body = body.decode('utf-8', errors='replace')

            boundary_pattern = f'--{boundary}'
            parts = body.split(boundary_pattern)
            
            model = None
            file_content = None
            filename = None
            filetype = None

            print(f"Found {len(parts)} parts in the multipart request")
            
            for i, part in enumerate(parts):
                part = part.strip()
                if not part or part == '--': 
                    continue
                    
                print(f"Processing part {i}: length={len(part)}")
                
                if 'Content-Disposition:' not in part and 'content-disposition:' not in part:
                    continue
                
                if '\r\n\r\n' in part:
                    headers, content = part.split('\r\n\r\n', 1)
                elif '\n\n' in part:
                    headers, content = part.split('\n\n', 1)
                else:
                    print(f"Couldn't find header/content delimiter in part {i}")
                    continue
                
                headers_lower = headers.lower()
                
                if 'name="file"' in headers_lower or "name='file'" in headers_lower:
                    file_content = content
                    if '--' in file_content:
                        file_content = file_content.split('--')[0]
                    
                    if isinstance(file_content, str):
                        file_content = file_content.encode('utf-8')
                        
                    print(f"Found file content of length: {len(file_content) if file_content else 0}")
                elif 'name="model"' in headers_lower or "name='model'" in headers_lower:
                    model = content.split('--')[0].strip()
                    print(f"Found model: {model}")
                elif 'name="filename"' in headers_lower or "name='filename'" in headers_lower:
                    filename = content.split('--')[0].strip()
                    print(f"Found filename: {filename}")
                elif 'name="filetype"' in headers_lower or "name='filetype'" in headers_lower:
                    filetype = content.split('--')[0].strip()
                    print(f"Found filetype: {filetype}")

            if not model:
                return cors_response(400, "Model parameter is required")

            if not file_content:
                return cors_response(400, "No file content found in the request")
                
            if not filename:
                return cors_response(400, "Filename parameter is required")
                
            if not filetype:
                return cors_response(400, "Filetype parameter is required")

        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Error parsing multipart data: {str(e)}\n{traceback_str}")
            return cors_response(400, f"Error processing file upload: {str(e)}")

        unique_filename = f"{uuid.uuid4()}-{filename}"
        
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_SCRAPED_BUCKET_NAME']

        try:
            s3_response = s3_client.put_object(
                Bucket=bucket_name,
                Key=f"user-{user_id}/{unique_filename}",
                Body=file_content,
                ContentType=filetype
            )

            insert_query = """
                INSERT INTO scrapedFiles (userId, model, filename, filepath, filetype)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, userId, model, filename, filepath, filetype, uploadDate
            """
            filepath = f"user-{user_id}/{unique_filename}"
            cur.execute(insert_query, (user_id, model, filename, filepath, filetype))
            file_record = cur.fetchone()
            
            conn.commit()

            return cors_response(201, {
                "message": "File uploaded successfully",
                "file": file_record,
                "s3Response": s3_response
            })

        except ClientError as e:
            return cors_response(500, f"Error uploading to S3: {str(e)}")

    except Exception as e:
        if conn:
            conn.rollback()
        return cors_response(500, f"Error uploading file: {str(e)}")
    finally:
        if conn:
            conn.close()
            
def getFile(event, context):
    conn = None
    try:
        # Handle OPTIONS request for CORS
        if event['httpMethod'] == 'OPTIONS':
            return cors_response(200, "ok")
            
        # Get file ID from path parameters
        file_id = event['pathParameters'].get('fileId')
        if not file_id:
            return cors_response(400, "File ID is required")

        # Get user ID from token
        auth_header = event.get('headers', {}).get('Authorization')
        token = auth_header.split(' ')[-1]
        token_payload = verify_token(token)
        cognito_user_id = token_payload.get('sub')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id FROM users WHERE cognito_id = %s", (cognito_user_id,))
        db_user = cur.fetchone()
        if not db_user:
            return cors_response(404, "User not found")
        user_id = db_user['id']

        # Get file metadata from database
        cur.execute(
            "SELECT * FROM scrapedFiles WHERE id = %s AND userId = %s",
            (file_id, user_id)
        )
        file_record = cur.fetchone()

        if not file_record:
            return cors_response(404, "File not found or unauthorized access")

        # Initialize S3 client
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_SCRAPED_BUCKET_NAME']

        try:
            # Get the actual file content from S3
            s3_response = s3_client.get_object(
                Bucket=bucket_name,
                Key=file_record['filepath']
            )
            
            # Read the file content
            file_content = s3_response['Body'].read()
            content_type = file_record['filetype']
            
            # Important: Add Content-Disposition header for all files
            headers = {
                'Content-Type': content_type,
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE,HEAD',
                'Content-Disposition': f'attachment; filename="{file_record["filename"]}"'
            }
            
            # For text files, decode and return as text
            if ('text/' in content_type or 
                content_type in ['application/json', 'application/xml', 'application/javascript']):
                try:
                    file_content = file_content.decode('utf-8')
                    # Return with custom headers for text content
                    return {
                        'statusCode': 200,
                        'body': file_content,
                        'headers': headers
                    }
                except UnicodeDecodeError:
                    # If we can't decode it as UTF-8, treat as binary
                    encoded_content = base64.b64encode(file_content).decode('utf-8')
                    return {
                        'statusCode': 200,
                        'body': encoded_content,
                        'headers': headers,
                        'isBase64Encoded': True
                    }
            else:
                # For binary files (PDFs, images, etc.), base64 encode and set the flag
                encoded_content = base64.b64encode(file_content).decode('utf-8')
                return {
                    'statusCode': 200,
                    'body': encoded_content,
                    'headers': headers,
                    'isBase64Encoded': True  # This flag is critical for API Gateway
                }

        except ClientError as e:
            return cors_response(500, f"Error retrieving file content: {str(e)}")

    except Exception as e:
        return cors_response(500, f"Error retrieving file: {str(e)}")
    finally:
        if conn:
            conn.close()
            
def deleteFile(event, context):
    conn = None
    try:
        file_id = event['pathParameters'].get('fileId')
        if not file_id:
            return cors_response(400, "File ID is required")

        auth_header = event.get('headers', {}).get('Authorization')
        token = auth_header.split(' ')[-1]
        token_payload = verify_token(token)
        cognito_user_id = token_payload.get('sub')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id FROM users WHERE cognito_id = %s", (cognito_user_id,))
        db_user = cur.fetchone()
        if not db_user:
            return cors_response(404, "User not found")
        user_id = db_user['id']

        cur.execute(
            "SELECT filepath FROM scrapedFiles WHERE id = %s AND userId = %s",
            (file_id, user_id)
        )
        file_record = cur.fetchone()

        if not file_record:
            return cors_response(404, "File not found or unauthorized access")

        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_SCRAPED_BUCKET_NAME']

        try:
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=file_record['filepath']
            )

            cur.execute(
                "DELETE FROM scrapedFiles WHERE id = %s AND userId = %s RETURNING id",
                (file_id, user_id)
            )
            deleted = cur.fetchone()

            if not deleted:
                return cors_response(404, "File not found or unauthorized access")

            conn.commit()

            return cors_response(200, {
                "message": "File deleted successfully",
                "fileId": file_id
            })

        except ClientError as e:
            return cors_response(500, f"Error deleting from S3: {str(e)}")

    except Exception as e:
        if conn:
            conn.rollback()
        return cors_response(500, f"Error deleting file: {str(e)}")
    finally:
        if conn:
            conn.close()