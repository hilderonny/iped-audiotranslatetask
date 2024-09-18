# Transcription and translation of audio files
# Configuration
# =============
# enabling: enableAudioTranslation
# Config file: AudioTranslation.txt

import time
import logging
import json
import requests

PROCESS_VIDEO = False
APIURL = None

def readJsonFile(file_path):
    with open(file_path) as json_file:
        file_contents = json_file.read()
    parsed_json = json.loads(file_contents)
    return parsed_json

class AudioTranslateTask:

    enabled = False

    def isEnabled(self):
        return AudioTranslateTask.enabled
    
    def finish(self):
        return

    def getConfigurables(self):
        from iped.engine.config import DefaultTaskPropertiesConfig
        return [DefaultTaskPropertiesConfig("enableAudioTranslation", "AudioTranslation.txt")]

    def init(self, configuration):
        taskConfig = configuration.getTaskConfigurable("AudioTranslation.txt")
        AudioTranslateTask.enabled = taskConfig.isEnabled()
        if not AudioTranslateTask.enabled:
            return
        extraProps = taskConfig.getConfiguration()
        global PROCESS_VIDEO, APIURL
        PROCESS_VIDEO = True if extraProps.getProperty("processVideo") == "true" else False
        taskBridgeUrl = extraProps.getProperty("taskBridgeUrl")
        if not taskBridgeUrl.endswith("/"):
            taskBridgeUrl = f"{taskBridgeUrl}/"
        APIURL = f"{taskBridgeUrl}api/"

    def process(self, item):
        item_name = item.getName()
        # Process only if not already in cache, therefor hashing must be enabled
        hash = item.getHash()
        if (hash is None) or (len(hash) < 1):
            return
        media_type = item.getMediaType().toString()

        if not (media_type.startswith('audio') or (PROCESS_VIDEO and media_type.startswith('video'))):
            return
        
        logging.info("Processing item %s of media type %s with hash %s", item_name, media_type, hash)

        result = self.process_via_api(item, hash)

        meta_data = item.getMetadata()
        if "language" in result:
            meta_data.set("audio:translation:language", result["language"])
        if "original" in result:
            meta_data.set("audio:translation:original", result["original"])
        if "translated" in result: # Bei deutschen Quelldateien ist dieser Eintrag nicht vorhanden
            meta_data.set("audio:translation:de", result["translated"])
        if "error" in result:
            meta_data.set("audio:translation:error", result["error"])
        logging.info("Finished processing item %s", item_name)

    def process_via_api(self, item, hash):
        # Prepare result
        result = {}

        transcribe_fp = open(item.getTempFile().getAbsolutePath(), "rb")
        transcribe_files = { "file" : transcribe_fp }
        transcribe_json = { "type" : "transcribe" }

        # Add transcribe task and upload file
        add_transcribe_response = requests.post(f"{APIURL}tasks/add/", files=transcribe_files, data={ "json" : json.dumps(transcribe_json) })
        if add_transcribe_response.status_code != 200:
            result["error"] = "Error adding transcribe task"
            return result
        task_transcribe_id = add_transcribe_response.json()["id"]

        # Wait for transcribe task completion
        task_transcribe_completed = False
        while not task_transcribe_completed:
            status_transcribe_response = requests.get(f"{APIURL}tasks/status/{task_transcribe_id}")
            if status_transcribe_response.status_code != 200:
                result["error"] = "Error requesting transcribe task status"
                return result
            status_transcribe = status_transcribe_response.json()["status"]
            if status_transcribe == "completed":
                task_transcribe_completed = True
            else:
                time.sleep(3)

        # Request transcribe result
        result_transcribe_response = requests.get(f"{APIURL}tasks/result/{task_transcribe_id}")
        if result_transcribe_response.status_code != 200:
            result["error"] = "Error requesting transcribe task result"
            return result
        transcribe_result = result_transcribe_response.json()

        # Delete transcribe task
        delete_transcribe_response = requests.delete(f"{APIURL}tasks/remove/{task_transcribe_id}")
        if delete_transcribe_response.status_code != 200:
            result["error"] = "Error deleting transcribe task"
            return result
       
        # Check whether further processing makes sense
        if "result" not in transcribe_result:
            result["error"] = "Transcription gave no result"
            return result
        if "language" not in transcribe_result["result"]:
            result["error"] = "Transcription did not detect a language"
            return result
        if "texts" not in transcribe_result["result"]:
            result["error"] = "Transcription gave no texts"
            return result

        # Parse transcribe result
        source_language = transcribe_result["result"]["language"]
        transcribe_text_list = list(map(lambda element: element["text"], transcribe_result["result"]["texts"]))
        result["language"] = source_language
        result["original"] = " ".join(transcribe_text_list)

        # If source language is german, stop processing
        if source_language == "de":
            return result
        
        # Add translate task
        translate_json = {
            "type" : "translate",
            "data" : {
                "sourcelanguage" : source_language,
                "targetlanguage" : "de",
                "texts" : transcribe_text_list
            }
        }
        add_translate_response = requests.post(f"{APIURL}tasks/add/", files={"Not": (None, "Used")}, data={ "json" : json.dumps(translate_json) })
        if add_translate_response.status_code != 200:
            result["error"] = "Error adding translate task"
            return result
        task_translate_id = add_translate_response.json()["id"]

        # Wait for translate task completion
        task_translate_completed = False
        while not task_translate_completed:
            status_translate_response = requests.get(f"{APIURL}tasks/status/{task_translate_id}")
            if status_translate_response.status_code != 200:
                result["error"] = "Error requesting translate task status"
                return result
            status_translate = status_translate_response.json()["status"]
            if status_translate == "completed":
                task_translate_completed = True
            else:
                time.sleep(3)

        # Request translate result
        result_translate_response = requests.get(f"{APIURL}tasks/result/{task_translate_id}")
        if result_translate_response.status_code != 200:
            result["error"] = "Error requesting translate task result"
            return result
        translate_result = result_translate_response.json()

        # Delete translate task
        delete_translate_response = requests.delete(f"{APIURL}tasks/remove/{task_translate_id}")
        if delete_translate_response.status_code != 200:
            result["error"] = "Error deleting translate task"
            return result

        translate_text_list = list(map(lambda element: element["text"], translate_result["result"]["texts"]))
        result["translated"] = " ".join(translate_text_list)
        return result
