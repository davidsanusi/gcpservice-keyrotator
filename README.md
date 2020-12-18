# gcpservice-keyrotator
Rotates GCP service account key

This tool is intended to be run within GCP environment using Cloud function
It scans through the service accounts keys that has been created and rotates keys that are greater than 90 days.

The key age to rotate can be modified according to your requirements.

The function expects two environment variables:
1. SLACK_API_TOKEN
2. KEY_HOLDERS

SLACK_API_TOKEN can be gotten from your slack account api section. This enables sending alerts to the respective users when their key has been rotated.

KEY_HOLDERS is a python dictionary of the format:

{"keyname1@gcp-project-name.iam.gserviceaccount.com": {"slack_id": "U1234567891"}, "keyname2@gcp-project-name.iam.gserviceaccount.com": {"slack_id": "U1234567892"}, "keyname3@gcp-project-name.iam.gserviceaccount.com": {"slack_id": "U1234567893"},}

You can add to the dictionary when new service account keys are added to your environment in order to keep track of the new keys as well.
