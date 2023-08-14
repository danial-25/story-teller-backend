import re
from google.cloud import texttospeech
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] ='key.json' 
client = texttospeech.TextToSpeechClient()

def first_word(string):#acquring first word if no topic was generated
    words = string.split()
    first_word = words[0]
    return first_word

def extract_name(string):#retrieving topic of text to provide name for audio
    paragraphs = re.split(r'\n{2,}', string.strip())
    if paragraphs:
    # Retrieve the first paragraph
        first_paragraph = paragraphs[0]
        first_paragraph = first_paragraph.replace('"', '')
        return first_paragraph
    else:
        return None
def text_to_audio(text, language):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
    language_code=language, ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
    audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)
    response = client.synthesize_speech(
    input=synthesis_input, voice=voice, audio_config=audio_config
)
    name=extract_name(text)
    if len(name)>50:
        name=first_word(name)   
    with open(f'stories/utilities/sounds/{name}.mp3', 'wb') as f:
        f.write(response.audio_content)
        print('success')

