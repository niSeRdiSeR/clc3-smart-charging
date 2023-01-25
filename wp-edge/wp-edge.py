import sys
import paho.mqtt.client as mqtt
from datetime import datetime
from google.cloud import pubsub_v1

WP_PK = os.getenv('WP_PK', None)
PROJECT_ID = os.getenv('GCLOUD_PROJECT', None)
SUB_TOPIC = os.getenv('SUB_TOPIC', None)
PUB_TOPIC = os.getenv('PUB_TOPIC', None)
MQTT_IP = os.getenv('MQTT_HOST', None)

if WP_PK is None:
    sys.exit("env variable 'WP_PK' not set")

WP_PK = int(WP_PK)

mqtt_client = mqtt.Client("wp-edge")
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

sub_topic_name = f'projects/{PROJECT_ID}/topics/{SUB_TOPIC}'

pub_topic_name = f'projects/{PROJECT_ID}/topics/{PUB_TOPIC}',

def mqtt_msg_handler(client, userdata, message):
    topic_list = message.topic.split('/')
    if 'properties' in topic_list[1]:
        prop = topic_list[3]
    elif 'available' in topic_list[1]:
        prop = 'available'
    val = str(message.payload.decode("utf-8"))
    publisher.publish(pub_topic_name, json.dumps({"pk": WP_PK, "prop": prop, "val": val, "timestamp": datetime.utcnow().timestamp()}))

mqtt_client.subscribe("wattpilot/properties/nrg_ptotal/state", qos=1) # float
mqtt_client.subscribe("wattpilot/properties/psm/state", qos=1) # int
mqtt_client.subscribe("wattpilot/properties/frc/state", qos=1) # int
mqtt_client.subscribe("wattpilot/properties/amp/state", qos=1) # int
mqtt_client.subscribe("wattpilot/properties/car/state", qos=1) # string
mqtt_client.subscribe("wattpilot/properties/wh/state", qos=1) # float
mqtt_client.subscribe("wattpilot/properties/wh/state", qos=1) # float
mqtt_client.subscribe("wattpilot/available", qos=1) # online/offline

mqtt_client.on_message=mqtt_msg_handler

try:
    mqtt_client.connect(MQTT_IP)
    mqtt_client.loop_start()

except:
    print(f"Couldn't connect with mqtt @ {MQTT_IP}")

def sub_msg_handler(msg):
    msg_json = json.loads(msg)
    if msg_json['pk'] == WP_PK:
        mqtt_client.publish(f"wattpilot/properties/{msg_json['prop']}/set", msg_json['val'], qos=1)

try:
    subscription_name = f'projects/{PROJECT_ID}/subscriptions/wp-edge-sub'
    subscriber.create_subscription(
        name=subscription_name, topic=sub_topic_name)
    future = subscriber.subscribe(subscription_name, sub_msg_handler)
except:
    print(f"Couldn't subscribe to pub/sub with '{subscription_name}' @ {sub_topic_name}")
