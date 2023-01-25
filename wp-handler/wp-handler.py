import base64
import os
import json
import requests
import redis
from datetime import datetime
from google.cloud import secretmanager
import influxdb_client
from influxdb_client.domain.write_precision import WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

REDIS_HOST = os.getenv('REDIS_HOST')
PROJECT_ID = os.getenv('GCLOUD_PROJECT')
INFLUX_SECRET_NAME = os.getenv('INFLUX_SECRET_NAME')
INFLUX_URL = os.getenv('INFLUX_HOST')
BUCKET = os.getenv('INFLUX_BUCKET') 
ORG = os.getenv('INFLUX_ORG') 

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

    # parsing
    print(f"processing: {pubsub_message} @ {src_topic}")
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    message_json = json.loads(pubsub_message)
    src_topic = context.resource['name']
    pk = message_json.pop('pk')
    dt = datetime.fromtimestamp(message_json['timestamp'])

    # redis
    r.hset(f"wp-{pk}", message_json['prop'], message_json['val'])
    r.hset(f"wp-{pk}", message_json['prop'], message_json['val'])
    print(r.hgetall(f"wp-{pk}"))

    # influx
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{INFLUX_SECRET_NAME}/versions/latest"
    token = client.access_secret_version(name=name).payload.data.decode("utf-8")
    
    influx_client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=token, org=ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    # write to influx
    p = influxdb_client.Point("wp_updates").tag("wp", pk).field(message_json['prop'], message_json['val']).time(dt, write_precision=WritePrecision.S)
    write_api.write(bucket=BUCKET, org=ORG, record=p)
