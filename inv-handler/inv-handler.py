import base64
import os
import json
import requests
import redis
from google.cloud import pubsub_v1

PROJECT_ID = os.getenv('GCLOUD_PROJECT')
TARGET_TOPIC = os.getenv('TARGET_TOPIC')
REDIS_HOST = os.getenv('REDIS_HOST')
TOPIC_PATH = publisher.topic_path(PROJECT_ID, TARGET_TOPIC)
C_233 = 233.333333

publisher = pubsub_v1.PublisherClient()

def set_prop(pk, prop, val):
    publisher.publish(TOPIC_PATH, json.dumps({"pk": pk, "prop": prop, "val": val}), pk=f"{pk}")


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
    if message_json['wp_pk'] is None:
        del message_json['wp_pk']
        r.hdel(f"inv-{pk}")
    #r.hset(f"inv-{pk}", mapping=message_json)
    #print(r.hgetall(f"inv-{pk}"))

    wp_pk = message_json.get('wp_pk', None)
    smart_charging_enabled = message_json.get('smart_charging_enabled', None)

    if wp_pk and wp_pk >= 0:
        print("====================")
        print(f"found reg. wp {wp_pk}")
        # create link in wp hashdict
        r.hset(f"wp-{wp_pk}", "inv", pk)
        wp_dict = r.hgetall(f"wp-{pk}")
        if not smart_charging_enabled:
            print("sc not enabled for attached wp or key not found")
        else:
            # logic processing
            print("sc enabled, applying logic")
            delta_kw = message_json['production'] - message_json['consumption']
            nrg_total_w = int(r.hget(f"wp-{wp_pk}", "nrg_total"))
            target_kw = nrg_total_w / 1000 + delta_kw if nrg_total_w else delta_kw
            if target_kw < 1:
                # switch off WP
                print(f"{wp_pk}: target power < 1 kW -> deny charging attempts")
                set_prop(wp_pk, "frc", 1)
            else:
                set_prop(wp_pk, "frc", 0)
                if target_kw < 3.77:
                    psm = 1
                    # 1-phase
                    amps = round(target_kw*1000/C_233)
                    if amps < 6:
                        print(f"{wp_pk}: requested less than 6 amps (1-phase)")
                        amps = 6
                    elif amps > 16:
                        print(f"{wp_pk}: requested more than 16 amps on (1-phase)!")
                        amps = 16
                    set_prop(wp_pk, "psm", psm) # 1-phase
                    set_prop(wp_pk, "amp", amps)
                else:
                    # 3-phase
                    psm = 0
                    amps = round(target_kw*1000/(400*1.73))
                    if amps < 6:
                        print(f"{wp_pk}: requested less than 6 amps (3-phase)")
                        amps = 6
                    elif amps > 16:
                        print(f"{wp_pk}: requested more than 16 amps (3-phase)")
                        amps = 16
                    set_prop(wp_pk, "psm", psm) # auto
                    set_prop(wp_pk, "amp", amps)
                print(f"{wp_pk}: target power > 1 kW -> allow charging ({amps}A; {psm}PSM)")
        print("====================")
    else:
        print("found no reg. wp")
