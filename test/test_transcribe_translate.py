# Test complete process of transcribing and translating

# python -m venv python-venv
# python-venv\Scripts\activate
# pip install requests argparse
# python test_transcribe_translate.py --taskbridgeurl http://192.168.0.152:42000/ --file d:\videos\video.mpg

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

transcribe_fp = open(FILE, "rb")
transcribe_files = { "file" : transcribe_fp }
transcribe_json = { "type" : "transcribe" }

# Add transcribe task and upload file
add_transcribe_response = requests.post(f"{APIURL}tasks/add/", files=transcribe_files, data={ "json" : json.dumps(transcribe_json) })
if add_transcribe_response.status_code != 200:
    print("ERROR while adding transcribe task")
    exit
task_transcribe_id = add_transcribe_response.json()["id"]
print(task_transcribe_id)

# Wait for transcribe task completion
task_transcribe_completed = False
while not task_transcribe_completed:
    status_transcribe_response = requests.get(f"{APIURL}tasks/status/{task_transcribe_id}")
    if status_transcribe_response.status_code != 200:
        print("ERROR while requesting transcribe status")
        exit
    status_transcribe = status_transcribe_response.json()["status"]
    print(f"Status: {status_transcribe}")
    if status_transcribe == "completed":
        task_transcribe_completed = True
    else:
        time.sleep(1)

# Request transcribe result
result_transcribe_response = requests.get(f"{APIURL}tasks/result/{task_transcribe_id}")
transcribe_result = result_transcribe_response.json()
print(transcribe_result)

# Delete transcribe task
requests.delete(f"{APIURL}tasks/remove/{task_transcribe_id}")


# Add translate task
translate_json = {
    "type" : "translate",
    "data" : {
        "sourcelanguage" : transcribe_result["result"]["language"],
        "targetlanguage" : "de",
        "texts" : list(map(lambda element: element["text"], transcribe_result["result"]["texts"]))
    }
}
add_translate_response = requests.post(f"{APIURL}tasks/add/", files={"Not": (None, "Used")}, data={ "json" : json.dumps(translate_json) })
if add_translate_response.status_code != 200:
    print("ERROR while adding translate task")
    exit
task_translate_id = add_translate_response.json()["id"]
print(task_translate_id)

# Wait for translate task completion
task_translate_completed = False
while not task_translate_completed:
    status_translate_response = requests.get(f"{APIURL}tasks/status/{task_translate_id}")
    if status_translate_response.status_code != 200:
        print("ERROR while requesting translate status")
        exit
    status_translate = status_translate_response.json()["status"]
    print(f"Status: {status_translate}")
    if status_translate == "completed":
        task_translate_completed = True
    else:
        time.sleep(1)

# Request translate result
result_translate_response = requests.get(f"{APIURL}tasks/result/{task_translate_id}")
translate_result = result_translate_response.json()
print(translate_result)

# Delete translate task
requests.delete(f"{APIURL}tasks/remove/{task_translate_id}")


print("Done")