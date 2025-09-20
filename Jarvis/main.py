import os
import time
import pyttsx3
import pyautogui
import speech_recognition as sr
from google import genai
client = genai.Client(api_key="AIzaSyCg2F4555PTKn-8rfmvUeJZwR0prOJveKw")


def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print('Listening...')
        r.pause_threshold = 1
        audio = r.listen(source)

    try:
        print('Recognizing...')
        query = r.recognize_google(audio, language='en-in')
        return query

    except Exception as e:
        print(e)
        print('Say that again please...')
        return 'None'
    
def speak(audio):
    engine = pyttsx3.init()
    engine.say(audio)
    engine.runAndWait()


def generate_response(prompt):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    return response.text

def write_to_notepad(text):
    os.system("start notepad")
    time.sleep(2)
    pyautogui.write(text, interval=0.01)
    speak(text)


input = ''
speak("Hello, I am Jarvis. How can I help you today?")
while True:
    input = takeCommand()
    print(f'User: {input}')
    print('Processing...')
    if input.lower() in ['exit', 'ok thank you']:
        speak("Goodbye!")
        break

    # Open Notepad
    if 'open notepad' in input.lower():
        os.system("start notepad")
        speak("Opening Notepad.")
        continue

    # Open YouTube
    if 'open youtube' in input.lower():
        os.system("start https://www.youtube.com")
        speak("Opening YouTube.")
        continue

    # Open Telegram (assuming Telegram Desktop is installed)
    if 'open telegram' in input.lower():
        os.system(r'start "" "C:\Users\xyz\Desktop\Telegram.lnk"')
        speak("Opening Telegram.")
        continue

    # Open Spotify (if installed)
    if 'open spotify' in input.lower():
        os.system(r'start "" "C:\Users\xyz\Desktop\Spotify.lnk"')
        speak("Opening Spotify.")
        continue

    # Open Calculator
    if 'open calculator' in input.lower():
        os.system("start calc")
        speak("Opening Calculator.")
        continue

    # Open Paint
    if 'open paint' in input.lower():
        os.system("start mspaint")
        speak("Opening Paint.")
        continue

    # Open Settings
    if 'open settings' in input.lower():
        os.system("start ms-settings:")
        speak("Opening Settings.")
        continue

    # Open File Explorer
    if 'open file explorer' in input.lower() or 'open explorer' in input.lower():
        os.system("start explorer")
        speak("Opening File Explorer.")
        continue

    # Open Microsoft Edge
    if 'open edge' in input.lower() or 'open browser' in input.lower():
        os.system("start msedge")
        speak("Opening Microsoft Edge.")
        continue

    if 'start' in input:
        os.system(input)
    else:
        response = generate_response(input)
        modified_responce = ''
        for chr in response:
            if chr != '*':
                modified_responce += chr
        response = modified_responce
        if 'notepad' in input.lower():
            write_to_notepad(response)
        else:
            print(f'Jarvis: {response}')
            speak(response)