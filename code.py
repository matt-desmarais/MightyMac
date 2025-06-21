import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
import supervisor

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

led.value = True

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

### Topic Setup ###

# MQTT Topic
# Use this topic if you'd like to connect to a standard MQTT broker
mqtt_topic = "greetermac/actions"

### Code ###
# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connect(mqtt_client, userdata, flags, rc):
    # This function will be called when the mqtt_client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")
    print("Flags: {0}\n RC: {1}".format(flags, rc))

def disconnect(mqtt_client, userdata, rc):
    # This method is called when the mqtt_client disconnects
    # from the broker.
    print("Disconnected from MQTT Broker!")

def subscribe(mqtt_client, userdata, topic, granted_qos):
    # This method is called when the mqtt_client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    # This method is called when the mqtt_client publishes data to a feed.
    print("Published to {0} with PID {1}".format(topic, pid))

def filter_ascii(text):
    return ''.join(char if ord(char) < 128 else '' for char in text)

def convert_international_to_ascii(text):
    char_map = {
        # Lowercase letters with accents and special marks
        'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a', 'å': 'a', 'ā': 'a', 'ă': 'a', 'ą': 'a',
        'ç': 'c', 'ć': 'c', 'č': 'c', 'ĉ': 'c', 'ċ': 'c',
        'ď': 'd', 'đ': 'd',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e', 'ē': 'e', 'ė': 'e', 'ę': 'e', 'ě': 'e',
        'ƒ': 'f',
        'ĝ': 'g', 'ğ': 'g', 'ġ': 'g', 'ģ': 'g',
        'ĥ': 'h', 'ħ': 'h',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i', 'ī': 'i', 'ĩ': 'i', 'į': 'i', 'ı': 'i',
        'ĵ': 'j',
        'ķ': 'k',
        'ĺ': 'l', 'ļ': 'l', 'ľ': 'l', 'ł': 'l',
        'ñ': 'n', 'ń': 'n', 'ň': 'n', 'ņ': 'n', 'ŋ': 'n',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o', 'ø': 'o', 'ō': 'o', 'ő': 'o', 'ŏ': 'o',
        'œ': 'oe',
        'ŕ': 'r', 'ř': 'r', 'ŗ': 'r',
        'ś': 's', 'ŝ': 's', 'š': 's', 'ş': 's', 'ș': 's', 'ß': 'ss',
        'ť': 't', 'ţ': 't', 'ŧ': 't', 'ț': 't',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ū': 'u', 'ů': 'u', 'ű': 'u', 'ŭ': 'u', 'ų': 'u',
        'ŵ': 'w',
        'ý': 'y', 'ÿ': 'y', 'ŷ': 'y',
        'ž': 'z', 'ź': 'z', 'ż': 'z', 'ž': 'z',

        # Uppercase letters with accents and special marks
        'À': 'A', 'Á': 'A', 'Â': 'A', 'Ä': 'A', 'Ã': 'A', 'Å': 'A', 'Ā': 'A', 'Ă': 'A', 'Ą': 'A',
        'Ç': 'C', 'Ć': 'C', 'Č': 'C', 'Ĉ': 'C', 'Ċ': 'C',
        'Ď': 'D', 'Đ': 'D',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'Ē': 'E', 'Ė': 'E', 'Ę': 'E', 'Ě': 'E',
        'Ĝ': 'G', 'Ğ': 'G', 'Ġ': 'G', 'Ģ': 'G',
        'Ĥ': 'H', 'Ħ': 'H',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I', 'Ī': 'I', 'Ĩ': 'I', 'Į': 'I', 'İ': 'I',
        'Ĵ': 'J',
        'Ķ': 'K',
        'Ĺ': 'L', 'Ļ': 'L', 'Ľ': 'L', 'Ł': 'L',
        'Ñ': 'N', 'Ń': 'N', 'Ň': 'N', 'Ņ': 'N', 'Ŋ': 'N',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Ö': 'O', 'Õ': 'O', 'Ø': 'O', 'Ō': 'O', 'Ő': 'O', 'Ŏ': 'O',
        'Œ': 'OE',
        'Ŕ': 'R', 'Ř': 'R', 'Ŗ': 'R',
        'Ś': 'S', 'Ŝ': 'S', 'Š': 'S', 'Ş': 'S', 'Ș': 'S',
        'Ť': 'T', 'Ţ': 'T', 'Ŧ': 'T', 'Ț': 'T',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U', 'Ū': 'U', 'Ů': 'U', 'Ű': 'U', 'Ŭ': 'U', 'Ų': 'U',
        'Ŵ': 'W',
        'Ý': 'Y', 'Ÿ': 'Y', 'Ŷ': 'Y',
        'Ž': 'Z', 'Ź': 'Z', 'Ż': 'Z', 'Ž': 'Z',

        # Ligatures and special symbols
        'Æ': 'AE', 'æ': 'ae',
        'Þ': 'TH', 'þ': 'th',
        'Ð': 'D', 'ð': 'd',
        'Œ': 'OE', 'œ': 'oe',
        'ß': 'ss',

        # Miscellaneous symbols
        '©': '(c)', '®': '(r)', '™': '(tm)', '°': 'deg',

    }

    # Replace characters in the text
    return ''.join(char_map.get(char, char) for char in text)


def message(client, topic, message):
    # Method called when a client's subscribed feed has a new value.
    print("New message on topic {0}: {1}".format(topic, message))
    if(message == "reboot"):
        supervisor.reload()
    #ascii_text = message.encode("ascii", "ignore").decode("ascii")
    #ascii_text = filter_ascii(message)
    ascii_text = convert_international_to_ascii(message)
    ascii_text = filter_ascii(ascii_text)
    led.value = True
    keyboard.press(Keycode.COMMAND)
    keyboard.press(Keycode.N)
    time.sleep(.25)
    keyboard.release_all()
    keyboard_layout.write(ascii_text)
    time.sleep(.5)
    keyboard.press(Keycode.COMMAND)
    keyboard.press(Keycode.T)
    time.sleep(.25)
    keyboard.release_all()
    led.value = False


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["user"],
    password=secrets["pass"],
    socket_pool=pool,
#    ssl_context=ssl.create_default_context(),
)

# Function to connect to MQTT broker with retry
def connect_to_broker():
    try:
        mqtt_client.connect()
        print("Connected to MQTT broker!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        time.sleep(5)  # Wait before retrying
        connect_to_broker()  # Recursively try to reconnect

# Connect callback handlers to mqtt_client
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message

print("Attempting to connect to %s" % mqtt_client.broker)
mqtt_client.connect()

print("Publishing to %s" % mqtt_topic)
mqtt_client.publish(mqtt_topic, "Mac SE Board Online!")

print("Subscribing to %s" % mqtt_topic)
mqtt_client.subscribe(mqtt_topic, qos=0)

#print("Unsubscribing from %s" % mqtt_topic)
#mqtt_client.unsubscribe(mqtt_topic)

#print("Disconnecting from %s" % mqtt_client.broker)
#mqtt_client.disconnect()

while True:
    try:
        led.value = True
        mqtt_client.loop(timeout=0.1)
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        mqtt_client.reconnect()
        continue
    led.value = False
    time.sleep(1)
