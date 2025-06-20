# Mighty Mac

*A talking 1987 Macintosh SE brought to life with AI, MQTT, and original Macintalk.*  
This project combines vintage charm with modern microcontrollers, giving a beige classic a voice — and a bit of attitude.

---

## Overview

Mighty Mac is a working Macintosh SE running System 6 from a floppy and speaking with Macintalk. With some help from a few microcontrollers and modern AI tools, it listens for voice prompts, responds intelligently, and reacts verbally when bumped. It lives on as a whimsical, chatty greeter at an automated [computer museum](https://www.patreon.com/niftymuseum)

---

## What It Can Do

- Respond to voice input using ChatGPT and Whisper  
- Speak out loud using original Macintalk  
- Type responses automatically using a keyboard emulator  
- React verbally to bumps, triggered by Home Assistant  
- Receive MQTT messages to trigger speech from any system

---

## Hardware

- **Macintosh SE** — running System 6 and Macintalk  
- **Raspberry Pi Zero 2** — handles hotword detection, voice recording, transcription, AI interaction, and MQTT publishing  
- **Raspberry Pi Pico W** — acts as a USB keyboard via USB Wombat; listens for MQTT messages and types responses  
- **Wemos D1 Mini + MPU6050** — configured via ESPHome; detects bumps and reports them to Home Assistant  
- **USB Wombat** — converts USB HID output from the Pico into ADB for the Mac  
- **WM8960 Audio HAT** — microphone and speaker interface for the Pi Zero 2  
- **Waveshare LED Hat** — for visual feedback (optional)

---

## Software Components

- Wake word detection and speech recording on the Pi Zero 2  
- Speech-to-text using [Whisper](https://github.com/openai/whisper)  
- AI replies using [ChatGPT API](https://platform.openai.com/)  
- MQTT for messaging  
- CircuitPython on the Pico W for keyboard emulation  
- ESPHome on the Wemos D1 Mini for bump detection  
- Home Assistant automation listens for bump events and publishes randomized responses to MQTT

---

## MQTT Topic

- **Topic:** `/greetermac/actions`  
- **Payload:** Plain text string  
- **Result:** The message is typed into the Mac and spoken aloud with Macintalk  
- **Publishers:** Pi Zero 2, Home Assistant, or any external source
