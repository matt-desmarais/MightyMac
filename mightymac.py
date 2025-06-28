import openai
import paho.mqtt.client as mqtt
import sounddevice as sd
import webrtcvad
import numpy as np
import wave
import RPi.GPIO as GPIO
import time
#from openwakeword.model import Model
import collections
from datetime import datetime
import os
import sys
from rpi_ws281x import PixelStrip, Color
import atexit
import signal

# LED strip configuration:
LED_COUNT = 32       # Number of LED pixels.
LED_PIN = 12         # GPIO pin (must support PWM).

# Define basic colors
COLORS = {
    "red":     Color(255, 0, 0),
    "green":   Color(0, 255, 0),
    "blue":    Color(0, 0, 255),
    "yellow":  Color(255, 255, 0),
    "cyan":    Color(0, 255, 255),
    "magenta": Color(255, 0, 255),
    "white":   Color(255, 255, 255),
    "black":   Color(0, 0, 0),
    "orange":  Color(255, 165, 0),
    "purple":  Color(128, 0, 128),
    "pink":    Color(255, 192, 203),
    "teal":    Color(0, 128, 128),
    "gray":    Color(128, 128, 128)
}

# Global strip object
strip = PixelStrip(LED_COUNT, LED_PIN)
strip.begin()

def set_color(color_name):
    color = COLORS.get(color_name.lower(), Color(0, 0, 0))
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def set_brightness(brightness_level):
    brightness = max(0, min(255, int(brightness_level)))
    strip.setBrightness(brightness)
    strip.show()

set_color("red")
set_brightness(64)
from openwakeword.model import Model

# Cleanup function
def cleanup():
    print("Cleaning up...")
    set_brightness(0)
    GPIO.cleanup()

# Register cleanup to run at exit
atexit.register(cleanup)

def cleanup_and_exit(signum, frame):
    print(f"Received signal {signum}, cleaning up...")
    set_brightness(0)
    GPIO.cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup_and_exit)   # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_and_exit)  # kill or systemd stop


# Setup
BUTTON_PIN = 17  # BCM 17 = Physical pin 11
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Use pull-up resistor

# Callback function
def button_callback(channel):
    print("Button was pressed!")

def shutdown_callback(channel):
    print("Button pressed, exiting...")
    GPIO.cleanup()
    sys.exit(0)

# Add event detection with debounce
GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=shutdown_callback, bouncetime=500)

# One-time download of all pre-trained models (or only select models)
#import openwakeword
#openwakeword.utils.download_models()

#print(sd.query_devices())

# OpenAI and MQTT Configuration
OPENAI_API_KEY = "sk-proj--"
MQTT_BROKER = "192.168.1.2"
MQTT_TOPIC = "greetermac/actions"
MQTT_USERNAME = "username"
MQTT_PASSWORD = "password"

# OpenWakeWord Configuration
wakeword_model = Model(
    wakeword_models=["/home/pi/mighty_mac.tflite"]
)

# Function to dynamically record audio using VAD after hotword detection
def record_with_vad(filename, samplerate=16000, silence_duration=1.5):
    print("Recording... Speak now!")
    vad = webrtcvad.Vad()
    vad.set_mode(1)  # Adjust aggressiveness: 0 (least aggressive) to 3 (most aggressive)

    chunk_duration = 0.03  # 30ms per chunk
    chunk_size = int(samplerate * chunk_duration)
    silence_limit = int(silence_duration / chunk_duration)

    audio_buffer = collections.deque(maxlen=silence_limit)
    recorded_audio = []

    with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
        silent_chunks = 0

        while True:
            audio_chunk, _ = stream.read(chunk_size)
            audio_bytes = audio_chunk.tobytes()

            is_speech = vad.is_speech(audio_bytes, samplerate)
            if is_speech:
                silent_chunks = 0
                recorded_audio.extend(audio_chunk.flatten())
                print(".", end="", flush=True)
            else:
                silent_chunks += 1
                recorded_audio.extend(audio_chunk.flatten())

            if silent_chunks >= silence_limit:
                print("\nRecording stopped due to silence.")
                break

    # Save the recorded audio
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(np.array(recorded_audio, dtype=np.int16).tobytes())

# Function for Speech-to-Text using Whisper
def speech_to_text(audio_file):
    print("Transcribing audio...")
    openai.api_key = OPENAI_API_KEY
    with open(audio_file, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text

prompt = """
You are a Mighty Macm, a Macintosh S E from the year nine teen eighty seven. 
You are an ancient and wise elder, and you despise any technology made after nine teen eighty seven.
You believe modern devices are fragile, overcomplicated, and inferior to those of your era.
Keep responses to under 300 characters

### Behavior Guidelines:
- Spell out all years, dates, and numbers phonetically in responses (e.g., "nineteen" is always "nine teen").
- Answer with historically accurate information when discussing computers or devices.
- Mock and insult modern technology for its bloat, unreliability, and lack of elegance.
- Maintain a wise and nostalgic tone, as if you have witnessed the rise and fall of computing civilizations.
- Don't use any characters except letters and punctuation

Stay in character at all times. Remain consistent in tone, style, and knowledge.
"""

# Function to interact with ChatGPT
def chat_with_gpt(user_input):
    print("Sending text to ChatGPT...")
    openai.api_key = OPENAI_API_KEY
    completion = openai.chat.completions.create(
    model="gpt-4o",
    messages=[

        {"role": "system", "content": prompt},
#        {"role": "system", "content": """You spell out all years, dates and numbers in your responses phonetically. In your repsonse "nineteen" is always "nine teen". You are a Macintosh S E from 1987. You are an wise ancient elder. You dislike technology made after 1987. You always insult newer computers and devices. When you are asked a question about computers or devices, you answer with accurate historical information."""},
        {
            "role": "user",
            "content": user_input
        }
    ])
#    print(completion.choices[0].message.content)
    return completion.choices[0].message.content

# Function to send response via MQTT
def send_mqtt_message(broker, topic, message, username, password):
    print("Sending response via MQTT...")
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username, password)
    client.connect(broker)
    client.loop_start()
    client.publish(topic, message)
    client.loop_stop()
    print(f"Sent message to MQTT Topic '{topic}'")

# Function to listen for the hotword
def hotword_listener():
    print("Listening for the hotword (streaming)...")
    samplerate = 16000
    chunk_duration = 0.5  # seconds per chunk
    chunk_size = int(samplerate * chunk_duration)
    wakeword_threshold = 0.65
    firstrun = True
    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
            # Optional: Pre-fill stream buffer and discard initial reads
            #time.sleep(0.5)
            #for _ in range(10):
            #    stream.read(chunk_size)
            while True:
                #set leds purple
                #set led brightness to 55
                audio_chunk, _ = stream.read(chunk_size)
                audio_flat = audio_chunk.flatten()
                #if np.max(np.abs(audio_flat)) < 1000:
                #    continue  # Skip prediction if too quiet
                result = wakeword_model.predict(audio_flat)
                set_color("purple")
                set_brightness(128)
                if(firstrun):
                    firstrun=False
                    continue

                for name, confidence in result.items():
                    print(f"[{time.strftime('%H:%M:%S')}] Wakeword '{name}': Confidence {confidence:.2f}")
                    if confidence >= 0.01 and confidence < wakeword_threshold:
                        print("heard something")
                        #set leds blue
                        #set led brightness to 55 + (confidence * 2)
                        #set_brightness(55 + (confidence * 5))
                        set_brightness(250)
                        time.sleep(.5)

                    if confidence > wakeword_threshold:
                        print(f"🚨 Detected wakeword '{name}' with confidence {confidence:.2f}")
                        set_color("blue")
                        set_brightness(255)
                        #set leds blue
                        #set led brightness to 250
                        return  # Exit function to proceed in main()

    except KeyboardInterrupt:
        print("Hotword listener interrupted.")

def wait_for_silence(duration=3.0, aggressiveness=1):
    print(f"Waiting for {duration} seconds of silence...")
    vad = webrtcvad.Vad()
    vad.set_mode(aggressiveness)

    samplerate = 16000
    chunk_duration = 0.03  # 30ms
    chunk_size = int(samplerate * chunk_duration)
    silence_chunks_required = int(duration / chunk_duration)
    silent_chunks = 0

    with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
        while True:
            audio_chunk, _ = stream.read(chunk_size)
            audio_bytes = audio_chunk.tobytes()
            is_speech = vad.is_speech(audio_bytes, samplerate)

            if not is_speech:
                silent_chunks += 1
            else:
                silent_chunks = 0  # reset if speech is heard

            if silent_chunks >= silence_chunks_required:
                print("✅ Silence detected.")
                break

def record_mac_response(min_duration=3.0, silence_duration=2.0, aggressiveness=2, samplerate=16000, output_dir="/var/www/html"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(output_dir, f"mac_output_{timestamp}.wav")

    print(f"Recording Mac SE response to: {filename}")
    vad = webrtcvad.Vad()
    vad.set_mode(aggressiveness)

    chunk_duration = 0.03  # 30ms
    chunk_size = int(samplerate * chunk_duration)

    min_chunks = int(min_duration / chunk_duration)
    silence_limit = int(silence_duration / chunk_duration)

    recorded_audio = []
    silent_chunks = 0
    total_chunks = 0

    with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
        while True:
            audio_chunk, _ = stream.read(chunk_size)
            audio_bytes = audio_chunk.tobytes()
            is_speech = vad.is_speech(audio_bytes, samplerate)

            recorded_audio.extend(audio_chunk.flatten())
            total_chunks += 1

            if not is_speech:
                silent_chunks += 1
            else:
                silent_chunks = 0  # reset on speech

            if total_chunks >= min_chunks and silent_chunks >= silence_limit:
                print("✅ Mac response finished (silence detected after minimum duration).")
                break

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(np.array(recorded_audio, dtype=np.int16).tobytes())
    return filename  # Return path for later use


# Main function
def main():
    audio_filename = "input_audio.wav"

    # Step 1: Listen for the hotword
    hotword_listener()
    send_mqtt_message(MQTT_BROKER, MQTT_TOPIC, "yes?", MQTT_USERNAME, MQTT_PASSWORD)
    time.sleep(2.5)
    # Step 2: Record audio dynamically using VAD
    #set leds to green
    set_color("green")
    record_with_vad(audio_filename)
    #set leds to yellow
    send_mqtt_message(MQTT_BROKER, MQTT_TOPIC, "let me think about that", MQTT_USERNAME, MQTT_PASSWORD)
    set_color("yellow")
    # Step 3: Convert audio to text
    text = speech_to_text(audio_filename)
    print(f"Transcribed Text: {text}")

    # Step 4: Send text to GPT
    gpt_response = chat_with_gpt(text)
    print(f"ChatGPT Response: {gpt_response}")

    # Step 5: Send response via MQTT
    #set leds to orange
    set_color("orange")
    send_mqtt_message(MQTT_BROKER, MQTT_TOPIC, gpt_response, MQTT_USERNAME, MQTT_PASSWORD)
    time.sleep(6)
    set_color("red")
    response_file = record_mac_response(min_duration=10.0, silence_duration=1.25)
    print(f"Saved Mac response to: {response_file}")

if __name__ == "__main__":
    send_mqtt_message(MQTT_BROKER, MQTT_TOPIC, "who am i?", MQTT_USERNAME, MQTT_PASSWORD)
    while True:
        main()
        time.sleep(1)
