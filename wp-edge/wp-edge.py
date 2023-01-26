import os
import sys
import time
import json
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

sub_topic_name = subscriber.topic_path(PROJECT_ID, SUB_TOPIC)
pub_topic_name = publisher.topic_path(PROJECT_ID, PUB_TOPIC)

last_vals = {}

def mqtt_msg_handler(client, userdata, message):
    topic_list = message.topic.split('/')
    if 'properties' in topic_list[1]:
        prop = topic_list[2]
    elif 'available' in topic_list[1]:
        prop = 'available'
    val = str(message.payload.decode("utf-8"))
    if last_vals.get(prop, None) is not val:
        data = json.dumps({"pk": WP_PK, "prop": str(prop), "val": val, "timestamp": datetime.utcnow().timestamp()})
        publisher.publish(pub_topic_name, data.encode('utf-8'))
        last_vals[prop] = val

try:
    mqtt_client.connect(MQTT_IP)

except:
    print(f"Couldn't connect with mqtt @ {MQTT_IP}")

mqtt_client.subscribe("wattpilot/properties/nrg_ptotal/state", qos=1) # float
mqtt_client.subscribe("wattpilot/properties/psm/state", qos=1) # int
mqtt_client.subscribe("wattpilot/properties/frc/state", qos=1) # int
mqtt_client.subscribe("wattpilot/properties/amp/state", qos=1) # int
mqtt_client.subscribe("wattpilot/properties/car/state", qos=1) # string
mqtt_client.subscribe("wattpilot/properties/wh/state", qos=1) # float
mqtt_client.subscribe("wattpilot/properties/wh/state", qos=1) # float
mqtt_client.subscribe("wattpilot/available", qos=1) # online/offline

mqtt_client.on_message=mqtt_msg_handler
mqtt_client.loop_start()


def sub_msg_handler(msg):
    msg_json = json.loads(msg.data.decode('utf-8'))
    if msg_json['pk'] == WP_PK:
        mqtt_client.publish(f"wattpilot/properties/{msg_json['prop']}/set", msg_json['val'], qos=1)
        msg.ack()

try:
    subscription_name = f'projects/{PROJECT_ID}/subscriptions/wp-edge-{WP_PK}T-sub'
    project_path = f"projects/{PROJECT_ID}"
    for subscription in publisher.list_topic_subscriptions(request={"topic": sub_topic_name}):
        if f'wp-edge-{WP_PK}' in subscription:
            print("subscription exists! skipping...")
            break
    else:
        print("subscription missing! creating...")
        # create new sub
        subscriber.create_subscription(request={"name": subscription_name, "topic": sub_topic_name, "filter": f'attributes.pk = "{WP_PK}"'})
    future = subscriber.subscribe(subscription_name, sub_msg_handler)

except Exception as e:
    print(f"Couldn't subscribe to pub/sub with '{subscription_name}' @ {sub_topic_name}")

while True:
    time.sleep(60)
