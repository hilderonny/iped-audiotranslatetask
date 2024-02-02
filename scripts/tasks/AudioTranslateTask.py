# Transcription and translation of audio files
# Configuration
# =============
# enabling: enableAudioTranslation
# Config file: AudioTranslation.txt

import os
import time
import logging
import json
import shutil
import stat
import requests

logging.basicConfig(format='%(asctime)s [%(levelname)s] [AudioTranslateTask.py] %(message)s', level=logging.DEBUG)
logging.getLogger("faster_whisper").setLevel(logging.DEBUG)

# Configuration properties
enableProp = "enableAudioTranslation"
configFile = "AudioTranslation.txt"
inputDirectoryProp = "inputDirectory"
outputDirectoryProp = "outputDirectory"
processVideoProp = "processVideo"
useForensicTaskBridgeProp = "useForensicTaskBridge"
forensicTaskBridgeApiUrlProp = "forensicTaskBridgeApiUrl"
forensicTaskBridgeShareDirectoryProp = "forensicTaskBridgeShareDirectory"

INPUT_DIR = None
OUTPUT_DIR = None
PROCESS_VIDEO = False
USE_API = False
API_URL = None
API_SHARE_DIR = None

def readJsonFile(file_path):
    with open(file_path) as json_file:
        file_contents = json_file.read()
    parsed_json = json.loads(file_contents)
    return parsed_json

class AudioTranslateTask:

    enabled = False

    def isEnabled(self):
        return AudioTranslateTask.enabled

    def getConfigurables(self):
        from iped.engine.config import DefaultTaskPropertiesConfig
        return [DefaultTaskPropertiesConfig(enableProp, configFile)]

    def init(self, configuration):
        taskConfig = configuration.getTaskConfigurable(configFile)
        AudioTranslateTask.enabled = taskConfig.isEnabled()
        if not AudioTranslateTask.enabled:
            return
        extraProps = taskConfig.getConfiguration()
        global INPUT_DIR, OUTPUT_DIR, PROCESS_VIDEO, USE_API, API_URL, API_SHARE_DIR
        INPUT_DIR = extraProps.getProperty(inputDirectoryProp)
        OUTPUT_DIR = extraProps.getProperty(outputDirectoryProp)
        PROCESS_VIDEO = True if extraProps.getProperty(processVideoProp) == "true" else False
        USE_API = True if extraProps.getProperty(useForensicTaskBridgeProp) == "true" else False
        API_URL = extraProps.getProperty(forensicTaskBridgeApiUrlProp)
        API_SHARE_DIR = extraProps.getProperty(forensicTaskBridgeShareDirectoryProp)

    def finish(self):
        return
        
    # Process an Item object. This method is executed on all case items.
    # It can access any method of Item class and store results as a new extra attribute.
    #
    #  Some Getters:
    #  String:  getName(), getExt(), getType(), getPath(), getHash(), getMediaType().toString(), getCategories() (categories separated by | )
    #  Date:    getModDate(), getCreationDate(), getAccessDate() (podem ser nulos)
    #  Boolean: isDeleted(), isDir(), isRoot(), isCarved(), isSubItem(), isTimedOut(), hasChildren()
    #  Long:    getLength()
    #  Metadata getMetadata()
    #  Object:  getExtraAttribute(String key) (returns an extra attribute)
    #  String:  getParsedTextCache() (returns item extracted text, if this task is placed after ParsingTask)
    #  File:    getTempFile() (returns a temp file with item content)
    #  BufferedInputStream: getBufferedInputStream() (returns an InputStream with item content)
    #
    #  Some Setters: 
    #           setToIgnore(boolean) (ignores the item and excludes it from processing and case)
    #           setAddToCase(boolean) (inserts or not item in case, after being processed: default true)
    #           addCategory(String), removeCategory(String), setMediaTypeStr(String)
    #              setExtraAttribute(key, value), setParsedTextCache(String)
    #
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

        if USE_API == True:
            result = self.process_via_api(item, hash)
        else:
            result = self.process_locally(item, hash)

        meta_data = item.getMetadata()
        if "language" in result:
            meta_data.set("audio:translation:language", result["language"])
        if "original" in result:
            meta_data.set("audio:translation:original", result["original"]["fulltext"])
        if "en" in result: # Bei deutschen Quelldateien ist dieser Eintrag nicht vorhanden
            meta_data.set("audio:translation:en", result["en"]["fulltext"])
        if "de" in result:
            meta_data.set("audio:translation:de", result["de"]["fulltext"])
        logging.info("Finished processing item %s", item_name)

    # Result format
    #   language
    #   original
    #     fulltext
    #   en
    #     fulltext
    #   de
    #     fulltext

    def process_locally(self, item, hash):
        source_file_path = item.getTempFile().getAbsolutePath()

        # Determine file name with hash
        input_file_path = os.path.join(INPUT_DIR, hash)
        output_file_path = os.path.join(OUTPUT_DIR, hash + ".json")

        # Check whether result file already exists in output directory
        if os.path.isfile(output_file_path) == False:
            # If not, copy source file into input directory
            shutil.copy(source_file_path, input_file_path)
            os.chmod(input_file_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO ) # Let the background process delete the file afterwards
            # Wait until the result file was created in output directory
            while os.path.isfile(output_file_path) == False:
                time.sleep(5)
        # Process result file and extract metadata
        result = readJsonFile(output_file_path)
        return result

    def process_via_api(self, item, hash):
        result = {}
        # Copy file to share folder
        source_file_path = item.getTempFile().getAbsolutePath()
        share_file_path = os.path.join(API_SHARE_DIR, hash)
        shutil.copy(source_file_path, share_file_path)
        # Add transcription task
        response = requests.post(f"{API_URL}tasks/transcribe/add/{hash}/large-v2")
        if response.status_code != 200:
            logging.error(f"Cannot access {API_URL}tasks/transcribe/add/{hash}/large-v2")
            return result
        add_transcribe_json_result = response.json()
        print(add_transcribe_json_result)
        transcribe_task_id = add_transcribe_json_result["id"]
        # Wait for transcription completion
        while requests.get(f"{API_URL}tasks/status/{transcribe_task_id}").json()["status"] != "done":
            time.sleep(5)
        transcribe_result = requests.get(f"{API_URL}tasks/result/{transcribe_task_id}").json()
        print(transcribe_result)
        if "error" in transcribe_result["result"]:
            result["error"] = transcribe_result["result"]["error"]
        else:
            # Add translate task
            add_translate_json_result = requests.post(f"{API_URL}tasks/translate/add/en/de", json=transcribe_result["result"]["en"]).json()
            print(add_translate_json_result)
            translate_task_id = add_translate_json_result["id"]
            # Wait for translation completion
            while requests.get(f"{API_URL}tasks/status/{translate_task_id}").json()["status"] != "done":
                time.sleep(5)
            # Collect results
            translate_result = requests.get(f"{API_URL}tasks/result/{translate_task_id}").json()
            print(translate_result)
            if "error" in translate_result["result"]:
                result["error"] = translate_result["result"]["error"]
            else:
                result["language"] = transcribe_result["result"]["language"]
                result["original"] = { "segments" : transcribe_result["result"]["original"]["segments"], "fulltext" : ' '.join(map(lambda segment: segment['text'], transcribe_result["result"]["original"]["segments"])) }
                result["en"] = { "segments" : transcribe_result["result"]["en"]["segments"], "fulltext" : ' '.join(map(lambda segment: segment['text'], transcribe_result["result"]["en"]["segments"])) }
                result["de"] = { "segments" : translate_result["result"]["segments"], "fulltext" : ' '.join(map(lambda segment: segment['text'], translate_result["result"]["segments"])) }
        # Delete tasks from bridge
        delete_result = requests.delete(f"{API_URL}tasks/remove/{transcribe_task_id}")
        print(delete_result)
        # Delete tasks from bridge
        delete_result = requests.delete(f"{API_URL}tasks/remove/{translate_task_id}")
        print(delete_result)
        print(result)
        return result
