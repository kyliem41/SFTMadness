import json
import os
import psycopg2
from datetime import datetime, date
import boto3
# import base64
import jwt
from botocore.exceptions import ClientError
from psycopg2.extras import RealDictCursor
import requests
from jwt import algorithms

def cors_response(status_code, body, content_type="application/json"):
    headers = {
        'Content-Type': content_type,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,PUT,DELETE',
    }

    if content_type == "application/json":
        body = json.dumps(body, default=str)
        # is_base64_encoded = False
    # else:
        # is_base64_encoded = True

    return {
        'statusCode': status_code,
        'body': body,
        'headers': headers,
        # 'isBase64Encoded': is_base64_encoded, #base64 for images if used
    }

def lambda_handler(event, context):
    if event['httpMethod'] == 'OPTIONS':
        return cors_response(200, "ok")
    
    print(f"Event received: {json.dumps(event)}")
    
    http_method = event['httpMethod']
    resource_path = event['resource']

    #for no authentication
    if resource_path == '/users' and http_method == 'POST':
        return registerUser(event, context)
    
    try:
        #verify token
        auth_header = event.get('headers', {}).get('Authorization')
        print(f"Auth header: {auth_header}")
        if not auth_header:
            return cors_response(401, "Unauthorized")
        if not auth_header.startswith('Bearer '):
            return cors_response(401, "Invalid Authorization header format. Must start with 'Bearer '")
        
        token = auth_header.split(' ')[-1]
        try:
            # verify_token(token)
            token_payload = verify_token(token)
            print(f"Token verified successfully: {json.dumps(token_payload)}")
        except Exception as e:
            print(f"Token verification failed: {str(e)}")
            return cors_response(401, f"Authentication failed: {str(e)}")

    except Exception as e:
        return cors_response(401, "Authentication failed")
        
    #routes with authentication
    try:
        if resource_path == '/users/{userId}' and http_method == 'GET':
            return getUser(event, context)
        elif resource_path == '/users/{userId}' and http_method == 'PUT':
            return updateUser(event, context)
        elif resource_path == '/users/{userId}' and http_method == 'DELETE':
            return deleteUser(event, context)
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
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ['DB_PORT'],

        connect_timeout=5)
    
#AUTH
def verify_token(token):
    try:
        # Get the JWT token from the Authorization header
        if not token:
            raise Exception('No token provided')

        region = boto3.session.Session().region_name

        # Get the JWT kid (key ID)
        try:
            headers = jwt.get_unverified_header(token)
            kid = headers['kid']
        except Exception as e:
                print(f"Error getting token header: {str(e)}")
                raise Exception(f'Invalid token header: {str(e)}')

        # Get the public keys from Cognito
        try:
            url = f'https://cognito-idp.{region}.amazonaws.com/{os.environ["COGNITO_USER_POOL_ID"]}/.well-known/jwks.json'
            response = requests.get(url)
            response.raise_for_status()
            keys = response.json()['keys']
            print(f"Retrieved keys: {json.dumps(keys)}")
        except Exception as e:
                print(f"Error fetching keys: {str(e)}")
                raise Exception(f'Error fetching public keys: {str(e)}')

        # Find the correct public key
        public_key = None
        for key in keys:
            if key['kid'] == kid:
                try:
                    public_key = algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break
                except Exception as e:
                        raise Exception(f'Error parsing public key: {str(e)}')

        if not public_key:
            raise Exception('Public key not found')

        # Verify the token
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_aud': True,
                    'verify_iss': True
                },
                audience=os.environ['COGNITO_CLIENT_ID'],
                issuer=f'https://cognito-idp.us-east-2.amazonaws.com/{os.environ["COGNITO_USER_POOL_ID"]}'
            )
            print(f"Token verification successful. Payload: {json.dumps(payload)}")
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception('Token has expired')
        except jwt.InvalidTokenError:
            raise Exception('Invalid token')
        except Exception as e:
            raise Exception(f'Token verification error: {str(e)}')

    except Exception as e:
        print(f"Token verification failed: {str(e)}")  # Add logging
        raise    

####################
#user functions
def registerUser(event, context):

    conn = None
    user_pool_id = os.environ['COGNITO_USER_POOL_ID']
    cognito_client = boto3.client('cognito-idp')

    try:
        body = json.loads(event.get('body', {}))
    except json.JSONDecodeError:
        return cors_response(400, f"Invalid JSON: {str(e)}")
    
    email = body.get('email')
    password = body.get('password')
    role = body.get('role')
    companyName = body.get('companyName')
    phoneNumber = body.get('phoneNumber')

    if not email or not password or not role:
        return cors_response(400, "Missing required fields")
    
    try:
        try:
            #create user in cognito
            cognito_response = cognito_client.admin_create_user(
                UserPoolId=user_pool_id, #use aws parameter names - case sensitive
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                TemporaryPassword=password,
                MessageAction='SUPPRESS',
            )

            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=email,
                Password=password,
                Permanent=True
            )

            #create user in db
            cognito_user_id = None
            for attribute in cognito_response['User']['Attributes']:
                if attribute['Name'] == 'sub':
                    cognito_user_id = attribute['Value']
                    break

            if not cognito_user_id:
                raise Exception("Could not get Cognito user ID")
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            user_insert_query = """INSERT INTO users (email, password, role, companyName, phoneNumber, joinDate, cognito_id) 
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s) 
                        RETURNING id, email, password, role, companyName, phoneNumber, joinDate, cognito_id"""
            cur.execute(user_insert_query, (email, password, role, companyName, phoneNumber, cognito_user_id))
            new_user = cur.fetchone()
            conn.commit()

            return cors_response(201, {
                "message": "User created",
                "user": new_user,
                "cognitoUser": cognito_response['User']
            })

        except ClientError as e:
            return cors_response(400, f"Error creating user: {str(e)}")
    except Exception as e:
        return cors_response(500, f"Error creating user: {str(e)}")
    finally:
        if conn:
            conn.close()

def getUser(event, context):
    conn = None
    try:
        # Get user ID from path parameters
        user_id = event['pathParameters'].get('userId')
        if not user_id:
            return cors_response(400, "User ID is required")

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Query to get user details
        user_query = """
            SELECT id, email, role, companyName, phoneNumber, joinDate 
            FROM users 
            WHERE id = %s"""
        cur.execute(user_query, (user_id,))
        user = cur.fetchone()

        if not user:
            return cors_response(404, "User not found")

        return cors_response(200, {"user": user})

    except Exception as e:
        return cors_response(500, f"Error retrieving user: {str(e)}")
    finally:
        if conn:
            conn.close()

def updateUser(event, context):
    conn = None
    try:
        # Get user ID from path parameters
        user_id = event['pathParameters'].get('userId')
        if not user_id:
            return cors_response(400, "User ID is required")

        # Parse request body
        try:
            body = json.loads(event.get('body', {}))
        except json.JSONDecodeError as e:
            return cors_response(400, f"Invalid JSON: {str(e)}")

        # Extract updateable fields
        updateable_fields = {
            'email': body.get('email'),
            'role': body.get('role'),
            'companyName': body.get('companyName'),
            'phoneNumber': body.get('phoneNumber')
        }

        # Remove None values
        update_fields = {k: v for k, v in updateable_fields.items() if v is not None}

        if not update_fields:
            return cors_response(400, "No valid fields to update")
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get the token payload to check the requester's role
        auth_header = event.get('headers', {}).get('Authorization')
        token = auth_header.split(' ')[-1]
        token_payload = verify_token(token)
        
        # Get requester's user info from database using their email
        requester_email = token_payload.get('email')
        cur.execute("SELECT role FROM users WHERE email = %s", (requester_email,))
        requester = cur.fetchone()
        
        if not requester:
            return cors_response(404, "Requester not found")
            
        # Get the target user's current role
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        target_user = cur.fetchone()
        
        if not target_user:
            return cors_response(404, "Target user not found")

        # Validate role if it's being updated
        if 'role' in update_fields:
            # Validate role value
            if update_fields['role'] not in ['customer', 'admin']:
                return cors_response(400, "Invalid role specified")
                
            # Only allow role updates if requester is admin
            if requester['role'] != 'admin':
                return cors_response(403, "Only administrators can update user roles")
                
            # If target user is trying to update their own role, prevent it
            if str(user_id) == str(token_payload.get('sub')):
                return cors_response(403, "Users cannot update their own role")

        # Construct UPDATE query dynamically
        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        values = list(update_fields.values()) + [user_id]  # Add user_id for WHERE clause
        
        update_query = f"""
            UPDATE users 
            SET {set_clause}
            WHERE id = %s
            RETURNING id, email, role, companyName, phoneNumber, joinDate"""

        cur.execute(update_query, values)
        updated_user = cur.fetchone()

        if not updated_user:
            return cors_response(404, "User not found")

        conn.commit()

        # If email was updated, update in Cognito as well
        if 'email' in update_fields:
            try:
                cognito_client = boto3.client('cognito-idp')
                cognito_client.admin_update_user_attributes(
                    UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                    Username=body.get('email'),
                    UserAttributes=[
                        {'Name': 'email', 'Value': body.get('email')},
                        {'Name': 'email_verified', 'Value': 'true'}
                    ]
                )
            except ClientError as e:
                # Rollback database changes if Cognito update fails
                conn.rollback()
                return cors_response(500, f"Error updating Cognito user: {str(e)}")

        return cors_response(200, {"user": updated_user})

    except Exception as e:
        if conn:
            conn.rollback()
        return cors_response(500, f"Error updating user: {str(e)}")
    finally:
        if conn:
            conn.close()

def deleteUser(event, context):
    conn = None
    try:
        # Get user ID from path parameters
        user_id = event['pathParameters'].get('userId')
        if not user_id:
            return cors_response(400, "User ID is required")

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # First, get the user's email for Cognito deletion
        cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        if not user:
            return cors_response(404, "User not found")

        # Delete from database
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        deleted = cur.fetchone()

        if not deleted:
            return cors_response(404, "User not found")

        conn.commit()

        # Delete from Cognito
        try:
            cognito_client = boto3.client('cognito-idp')
            cognito_client.admin_delete_user(
                UserPoolId=os.environ['COGNITO_USER_POOL_ID'],
                Username=user['email']
            )
        except ClientError as e:
            # Note: Database deletion is already committed, so we just log the Cognito error
            print(f"Error deleting Cognito user: {str(e)}")

        return cors_response(200, {"message": "User deleted successfully", "userId": user_id})

    except Exception as e:
        if conn:
            conn.rollback()
        return cors_response(500, f"Error deleting user: {str(e)}")
    finally:
        if conn:
            conn.close()