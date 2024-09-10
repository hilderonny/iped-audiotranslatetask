# Test upload of big video files

# python -m venv python-venv
# python-venv\Scripts\activate
# pip install requests argparse
# python test_bigfile.py --taskbridgeurl http://192.168.0.152:42000/ --file d:\videos\bigvideofile.mpg

import requests
import argparse
import time
import json

parser = argparse.ArgumentParser()
parser.add_argument('--taskbridgeurl', type=str, action='store', required=True)
parser.add_argument('--file', type=str, action='store', required=True)
args = parser.parse_args()

TASKBRIDGEURL = args.taskbridgeurl
if not TASKBRIDGEURL.endswith("/"):
    TASKBRIDGEURL = f"{TASKBRIDGEURL}/"
APIURL = f"{TASKBRIDGEURL}api/v2/"
FILE = args.file

fp = open(FILE, "rb")

files = { "file" : fp }
transcribe_json = { "type" : "transcribe" }

# Add task and upload file
add_response = requests.post(f"{APIURL}tasks/add/", files=files, data={ "json" : json.dumps(transcribe_json) })
if add_response.status_code != 200:
    print("ERROR while adding task")
    exit
task_id = add_response.json()["id"]
print(task_id)

# Wait for completion
task_completed = False
while not task_completed:
    status_response = requests.get(f"{APIURL}tasks/status/{task_id}")
    if status_response.status_code != 200:
        print("ERROR while requesting status")
        exit
    status = status_response.json()["status"]
    print(f"Status: {status}")
    if status == "completed":
        task_completed = True
    else:
        time.sleep(1)

# Request result
result_response = requests.get(f"{APIURL}tasks/result/{task_id}")
print(result_response.json())

# Delete task
requests.delete(f"{APIURL}tasks/remove/{task_id}")
print("Done")