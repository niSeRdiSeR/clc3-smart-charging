import sys
import paho.mqtt.client as mqtt

WP_PK = os.getenv('WP_PK', None)
PROJECT_ID = os.getenv('GCLOUD_PROJECT', None)
SUB_TOPIC = os.getenv('SUB_TOPIC', None)
PUB_TOPIC = os.getenv('PUB_TOPIC', None)
MQTT_IP = os.getenv('MQTT_IP', None)

if WP_PK is None:
    sys.exit("env variable 'WP_PK' not set")

WP_PK = int(WP_PK)

mqtt_client = mqtt.Client("wp-edge")
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

sub_topic_name = f'projects/{PROJECT_ID}/topics/{SUB_TOPIC}'

pub_topic_name = f'projects/{PROJECT_ID}/topics/{PUB_TOPIC}',

def mqtt_msg_handler(client, userdata, message):
    prop = message.topic.split('/')[-2]
    val = int(message.payload.decode("utf-8"))
    publisher.publish(pub_topic_name, json.dumps({"pk": WP_PK, "prop": prop, "val": val}))

mqtt_client.subscribe("wattpilot/properties/nrg_ptotal/state") # float
mqtt_client.on_message=mqtt_msg_handler

try:
    mqtt_client.connect(MQTT_IP)
except:
    print(f"Couldn't connect with mqtt @ {MQTT_IP}")

def sub_msg_handler(msg):
    msg_json = json.loads(msg)
    if msg_json['pk'] = WP_PK:
        mqtt_client.publish(f"wattpilot/properties/{msg_json['prop']}/set", msg_json['val'], qos=1)

try:
    subscription_name = f'projects/{PROJECT_ID}/subscriptions/wp-edge-sub'
    subscriber.create_subscription(
        name=subscription_name, topic=sub_topic_name)
    future = subscriber.subscribe(subscription_name, sub_msg_handler)
except:
    print(f"Couldn't subscribe to pub/sub with '{subscription_name}' @ {sub_topic_name}")