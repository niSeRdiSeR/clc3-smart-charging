import base64
import os
import json
import requests
import psycopg2
import sqlalchemy
from datetime import datetime
from google.cloud import pubsub_v1
from google.cloud import secretmanager
import influxdb_client
from influxdb_client.domain.write_precision import WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

PROJECT_ID = os.getenv('GCLOUD_PROJECT')
DB_INSTANCE_CONN_NAME = os.getenv('DB_INSTANCE_CONN_NAME')
DB_NAME = os.getenv('DB_NAME')
TARGET_TOPIC = os.getenv('TARGET_TOPIC')
DB_SECRET_NAME = os.getenv('DB_SECRET_NAME')
INFLUX_SECRET_NAME = os.getenv('INFLUX_SECRET_NAME')
API_BASE = 'https://monitoringapi.solaredge.com'
INFLUX_URL = os.getenv('INFLUX_HOST')
BUCKET = os.getenv('INFLUX_BUCKET') 
ORG = os.getenv('INFLUX_ORG') 

def fetch_powerflow(site_id, token):
    url = f"{API_BASE}/site/{site_id}/currentPowerFlow"
    params = {
        'api_key': token
    }
    r = requests.get(url, params)
    r.raise_for_status()
    res = r.json()
    production = res["siteCurrentPowerFlow"]["PV"]["currentPower"]
    consumption = res["siteCurrentPowerFlow"]["LOAD"]["currentPower"]
    from_grid = res["siteCurrentPowerFlow"]["GRID"]["currentPower"]
    return production, consumption, from_grid


def handle(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    print(pubsub_message)

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{DB_SECRET_NAME}/versions/latest"
    payload = json.loads(client.access_secret_version(name=name).payload.data.decode("utf-8"))
    db_user = payload['user']
    db_password = payload['password']

    project_path = f"projects/{PROJECT_ID}"
    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(PROJECT_ID, TARGET_TOPIC)
    topic_strings = [t.name for t in publisher.list_topics(request={"project": project_path})]

    name = f"projects/{PROJECT_ID}/secrets/{INFLUX_SECRET_NAME}/versions/latest"
    token = client.access_secret_version(name=name).payload.data.decode("utf-8")
    
    influx_client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=token, org=ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)

    if topic_path not in topic_strings:
        publisher.create_topic(request={"name": topic_path})
    
    engine = sqlalchemy.create_engine(f'postgresql+psycopg2://{db_user}:{db_password}@/{DB_NAME}?host=/cloudsql/{DB_INSTANCE_CONN_NAME}')
    with engine.connect() as conn:
        rows = conn.execute('SELECT id, token, site_id, wattpilot_id, smart_charging_enabled FROM management_inverter')
        for row in rows:
            pk = row[0]
            token = row[1]
            site_id = row[2]
            wp_pk = row[3]
            smart_charging_enabled = row[4]
            try:
                prod, cons, from_grid = fetch_powerflow(site_id, token)
                publisher.publish(topic_path, json.dumps({"pk": pk, "wp_pk": wp_pk, "smart_charging_enabled": smart_charging_enabled, "production": prod, "consumption": cons, "from_grid": from_grid}).encode('utf-8'))
                # write to influx
                p = influxdb_client.Point("inverter-updates").tag("inverter", pk).field("production", prod).field("consumption", cons).field("from_grid", from_grid).time(datetime.utcnow(), write_precision=WritePrecision.S)
                write_api.write(bucket=BUCKET, org=ORG, record=p)
            except:
                print(f"error fetching: {pk}, {site_id}")            

