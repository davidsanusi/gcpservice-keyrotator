import os
from google.oauth2 import service_account
import googleapiclient.discovery
from datetime import datetime, time
import urllib, json, base64
from google.cloud import storage
from slack import WebClient
from slack.errors import SlackApiError
from oauth2client.client import GoogleCredentials
from pathlib import Path

# Turn off ssl checking when testing on MACOS by uncommenting the two lines below. Turn on again on production environment.
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context

# Credit partially to Google
# Get existing key parameter
def get_key_parameters(service_account_email):
    """Lists all keys for a service account."""

    credentials = GoogleCredentials.get_application_default()

    service = googleapiclient.discovery.build('iam', 'v1', credentials=credentials)

    # Uncomment this to work locally
    # credentials = service_account.Credentials.from_service_account_file(
    #     filename=os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    #     scopes=['https://www.googleapis.com/auth/cloud-platform'])

    # # Uncomment this to work locally
    # service = googleapiclient.discovery.build(
    #     'iam', 'v1', credentials=credentials)

    # Uncomment this to deploy in a google environment
    service = googleapiclient.discovery.build('iam', 'v1')

    keys = service.projects().serviceAccounts().keys().list(
        name='projects/-/serviceAccounts/' + service_account_email).execute()

    key_parameters = None
    
    # Extract only user created keys because list returns keys created and managed by Google.
    for key in keys['keys']:
        # print('Key: ' + key['name'])
        if key['keyType'] == 'USER_MANAGED': # Because there are keys automatically created by gcp of type SYSTEM_MANAGED
            key_of_interest = key
            created_date = datetime.strptime(key_of_interest['validAfterTime'], '%Y-%m-%dT%H:%M:%SZ')   # Date formst from output: 2020-11-04T12:01:44Z
            key_age = datetime.now() - created_date
            key_id = key['name']
            print("...............")
            print(f"Current time: {datetime.now()}")
            print(f"Date created: {created_date}")
            print(f"Key age: {key_age.total_seconds()} seconds")
            print("...............")
            key_parameters = (key_age.total_seconds(), key_id)
    
    return key_parameters

# Credit: Google
# Create new key
def create_key(service_account_email):
    """Creates a key for a service account."""

    credentials = GoogleCredentials.get_application_default()

    service = googleapiclient.discovery.build('iam', 'v1', credentials=credentials)

    # Uncomment this to work locally
    # credentials = service_account.Credentials.from_service_account_file(
    #     filename=os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    #     scopes=['https://www.googleapis.com/auth/cloud-platform'])

    # # Uncomment this to work locally
    # service = googleapiclient.discovery.build(
    #     'iam', 'v1', credentials=credentials)

    # Uncomment this to deploy in a google environment
    service = googleapiclient.discovery.build('iam', 'v1')

    key = service.projects().serviceAccounts().keys().create(
        name='projects/-/serviceAccounts/' + service_account_email, body={}
        ).execute()

    print('Created key: ' + key['name'])

    return key


# Source: Google
# Delete key
def delete_key(full_key_name):
    """Deletes a service account key."""
# from googleapiclient import discovery


    credentials = GoogleCredentials.get_application_default()

    service = googleapiclient.discovery.build('iam', 'v1', credentials=credentials)

    # Uncomment this to work to use json key file to authenticate
    # credentials = service_account.Credentials.from_service_account_file(
    #     filename=os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    #     scopes=['https://www.googleapis.com/auth/cloud-platform'])

    # # Uncomment this to work locally
    # service = googleapiclient.discovery.build(
    #     'iam', 'v1', credentials=credentials)

    # Uncomment this to deploy in a google environment
    service = googleapiclient.discovery.build('iam', 'v1')

    service.projects().serviceAccounts().keys().delete(
        name=full_key_name).execute()

    print('Deleted key: ' + full_key_name)


# Build private_key
def generate_private_key(service_account_email):

    new_key = create_key(service_account_email)

    # Create JSON key file name
    id_key = new_key['name'].split("keys/")[-1]
    json_key_name = service_account_email.replace("@", "-")
    json_file_name = json_key_name.replace(".iam.gserviceaccount.com", "-") + id_key + ".json"
    temp_folder = Path("/tmp")
    final_json_filename = temp_folder / json_file_name
    # print(final_json_filename)

    # privateKeyData is returned in base64 format so it needs to be decoded and converted to proper json before it can be used.
    decoded_keyfile = json.dumps(json.loads(base64.b64decode(new_key['privateKeyData'])))
    
    # Write json key to file
    # print(decoded_keyfile)
    with open(final_json_filename, 'w', encoding='utf-8') as f:
        f.write(decoded_keyfile)

    # Upload JSON key to Cloud storage bucket by calling the upload_blob function
    bucket_name = "sa-credstore"
    source_file_name = str(final_json_filename)
    destination_blob_name = json_file_name

    upload_blob(bucket_name, source_file_name, destination_blob_name)
    
    # return json_file_name

# Source: https://cloud.google.com/storage/docs/uploading-objects#storage-upload-object-python
def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )


# Send slack alert
def send_slack_alert(slack_id):
    # Present api key as environment variable and all other credentials 
    # Dynamically present channelid to the channel variable 

    client = WebClient(token=os.getenv("SLACK_API_TOKEN"))

    # Build alert message 
    text_user = "Your GCP service account key has just been rotated. Please contact your Administrator for the new key."
    text_admin = "GCP Service account key(s) has just been rotated."

    if slack_id == "#slack-channel-name":   # Add slack channel name here
        text_to_send = text_admin
    else:
        text_to_send = text_user

    try:
        response = client.chat_postMessage(
            channel=slack_id, # Set channel id here
            text=text_to_send)
        assert response["message"]["text"] == text_to_send
        print("Slack message sent")
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

# #######################################

def entrypoint(event, context):

    key_holders = json.loads(os.getenv("KEY_HOLDERS"))

    for each_key in key_holders:
        key_params = get_key_parameters(each_key)

        # If key_params is not None or empty
        if key_params:
            age_of_key = key_params[0]
            id_of_key = key_params[1]
            if age_of_key >= 7776000:
                print("................")
                print("Age of key is greater than 90 days or 7776000 seconds")
                print(f"Age of key: {age_of_key} seconds")
                print(f"Key ID: {id_of_key}")
                print("................")

                generate_private_key(each_key)
                delete_key(id_of_key)
                print('................')

                send_slack_alert(key_holders[each_key]['slack_id'])
                send_slack_alert("#slack-channel-name")
            else:
                print(f"Age of key: {age_of_key} seconds")
                print(f"Key ID: {id_of_key}")
                print("Key age less than 90 days. No actions necessary")
                print("................")
