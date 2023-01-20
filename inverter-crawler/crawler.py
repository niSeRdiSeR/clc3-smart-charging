import base64
import os
import json
import requests
import psycopg2
import sqlalchemy
from google.cloud import pubsub_v1
from google.cloud import secretmanager

PROJECT_ID = os.getenv('GCLOUD_PROJECT')
DB_INSTANCE_CONN_NAME = os.getenv('DB_INSTANCE_CONN_NAME')
DB_NAME = os.getenv('DB_NAME')
TARGET_TOPIC = os.getenv('TARGET_TOPIC')
DB_SECRET_NAME = os.getenv('DB_SECRET_NAME')
API_BASE = 'https://monitoringapi.solaredge.com'

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
    settings_name = os.environ.get("SETTINGS_NAME", "django_settings")
    name = f"projects/{PROJECT_ID}/secrets/{DB_SECRET_NAME}/versions/latest"
    payload = json.loads(client.access_secret_version(name=name).payload.data.decode("utf-8"))
    db_user = payload['user']
    db_password = payload['password']

    project_path = f"projects/{PROJECT_ID}"
    publisher = pubsub_v1.PublisherClient()

    topic_path = publisher.topic_path(PROJECT_ID, TARGET_TOPIC)
    topic_strings = [t.name for t in publisher.list_topics(request={"project": project_path})]

    if topic_path not in topic_strings:
        publisher.create_topic(request={"name": topic_path})
    
    engine = sqlalchemy.create_engine(f'postgresql+psycopg2://{db_user}:{db_password}@/{DB_NAME}?host=/cloudsql/{DB_INSTANCE_CONN_NAME}')
    with engine.connect() as conn:
        rows = conn.execute('SELECT id, token, site_id FROM management_inverter')
        for row in rows:
            pk = row[0]
            token = row[1]
            site_id = row[2]
            wp_rows = conn.execute(f'SELECT id FROM management_wattpilot WHERE inverter_id={pk}')
            wp_pk = wp_rows.fetchone()[0] if wp_rows.rowcount > 0 else None
            try:
                prod, cons, from_grid = fetch_powerflow(site_id, token)
                publisher.publish(topic_path, json.dumps({"pk": pk, "wp_pk": wp_pk, "production": prod, "consumption": cons, "from_grid": from_grid}).encode('utf-8'))
            except:
                print(f"error fetching: {pk}, {site_id}")