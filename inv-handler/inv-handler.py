import base64
import os
import json
import requests
import redis
from google.cloud import pubsub_v1

PROJECT_ID = os.getenv('GCLOUD_PROJECT')
#INVERTER_SRC_TOPIC = os.getenv('INVERTER_SRC_TOPIC')
#WATTPILOT_SRC_TOPIC = os.getenv('WATTPILOT_SRC_TOPIC')
TARGET_TOPIC = os.getenv('TARGET_TOPIC')
REDIS_HOST = os.getenv('REDIS_HOST')

def handle(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    message_json = json.loads(pubsub_message)
    src_topic = context.resource['name']

    print(f"processing: {pubsub_message} @ {src_topic}")


    project_path = f"projects/{PROJECT_ID}"
    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(PROJECT_ID, TARGET_TOPIC)
    topic_strings = [t.name for t in publisher.list_topics(request={"project": project_path})]

    if topic_path not in topic_strings:
        publisher.create_topic(request={"name": topic_path})
    
    #if WATTPILOT_SRC_TOPIC in src_topic:
        
        #r.hset(message_json['pk'], message_json['value'])
    #elif INVERTER_SRC_TOPIC in src_topic:
    pk = message_json.pop('pk')
    if message_json['wp_pk'] is None:
        del message_json['wp_pk']
    r.hset(f"inv-{pk}", mapping=message_json)
    print(r.hgetall(f"inv-{pk}"))

    wp_pk = message_json.get('wp_pk', None)

    if wp_pk:
        print(f"found reg. wp {wp_pk}")
        # create link in wp hashdict
        r.hset(f"wp-{wp_pk}", "inv", pk)
        wp_dict = r.hgetall(f"wp-{pk}")
        if not wp_dict.get("smart_charging_enabled"):
            print("sc not enabled for attached wp or key not found")
        else:
            # logic processing
            print("sc enabled, applying logic")
            
    else:
        print("found no reg. wp")
