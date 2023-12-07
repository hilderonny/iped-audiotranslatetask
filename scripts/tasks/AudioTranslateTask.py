# Transcription and translation of audio files
# https://github.com/hilderonny/iped-audiotranslatetask
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
logging.basicConfig(format='%(asctime)s [%(levelname)s] [AudioTranslateTask.py] %(message)s', level=logging.DEBUG)

# Configuration properties
enableProp = "enableAudioTranslation"
configFile = "AudioTranslation.txt"
inputDirectoryProp = "inputDirectory"
outputDirectoryProp = "outputDirectory"
processVideoProp = "processVideo"

INPUT_DIR = None
OUTPUT_DIR = None
PROCESS_VIDEO = False

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
        global INPUT_DIR, OUTPUT_DIR, PROCESS_VIDEO
        INPUT_DIR = extraProps.getProperty(inputDirectoryProp)
        OUTPUT_DIR = extraProps.getProperty(outputDirectoryProp)
        PROCESS_VIDEO = True if extraProps.getProperty(processVideoProp) == "true" else False

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
