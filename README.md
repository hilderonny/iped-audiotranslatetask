# iped-audiotranslatetask

[IPED](https://github.com/sepinf-inc/IPED) task for audio translation via distributed workers. Uses [Task Bridge](https://github.com/hilderonny/taskbridge) together with [Transcribe](https://github.com/hilderonny/taskworker-transcribe) and [Translate](https://github.com/hilderonny/taskworker-translate) workers for distributing and doing the work.

## Output

Using this task each media file (audio, video) will get the following additional metadata.

|Property|Description|
|-|-|
|`audio:translation:language`|First language detected in the media file. If the file contains mutliple languages, only the first one is detected.|
|`audio:translation:original`|Transcribed text of the media file in its original language|
|`audio:translation:de`|Text in german|
|`audio:translation:error`|Error message when the transcription or translation was unsuccessful|

## Installation

First download an install [IPED](https://github.com/sepinf-inc/IPED).

Next copy the file `scripts/tasks/AudioTranslateTask.py` into the `scripts/tasks`folder of your IPED installation.

Copy the file `conf/AudioTranslation.txt` into the `conf`directory of your IPED installation.

In your IPED folder open the file `IPEDConfig.txt` and add the following line.

```
enableAudioTranslation = true
```

Finally open the file `conf/TaskInstaller.xml` and look for a line containing `iped.engine.task.transcript.AudioTranscriptTask`. Add the following line immediately after this line:

```xml
<task script="AudioTranslateTask.py"></task>
```

## Configuration

The configuration is done in the file `conf/AudioTranslation.txt` in your IPED directory. This files contains comments on how to setup the connection to the task bridge.