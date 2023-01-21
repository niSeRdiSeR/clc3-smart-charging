import base64
import os
import json
import requests
import redis

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

    pk = message_json.pop('pk')

    r.hset(f"wp-{pk}", message_json['prop'], message_json['val'])
    print(r.hgetall(f"wp-{pk}"))
