import base64
import os
import json
import requests
import redis
from google.cloud import pubsub_v1

PROJECT_ID = os.getenv('GCLOUD_PROJECT')
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
    
    pk = message_json.pop('pk')

    r.hset(f"wp-{pk}", message_json['prop'], message_json['val'])
    print(r.hgetall(f"wp-{pk}"))
