import base64
import os
import json
import redis
from google.cloud import pubsub_v1

PROJECT_ID = os.getenv('GCLOUD_PROJECT')
TARGET_TOPIC = os.getenv('TARGET_TOPIC')
REDIS_HOST = os.getenv('REDIS_HOST')
C_233 = 233.333333
MAX_AMPS = 16
MIN_AMPS = 6


publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TARGET_TOPIC)

def set_prop(pk, prop, val):
    data = json.dumps({"pk": pk, "prop": prop, "val": val})
    publisher.publish(topic_path, data.encode('utf-8'), pk=f"{pk}")
    print(f"sent: {data.encode('utf-8')}")


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

    wp_pk = message_json.get('wp_pk', None)
    smart_charging_enabled = message_json.get('smart_charging_enabled', None)

    if wp_pk and wp_pk >= 0:
        print("====================")
        print(f"found reg. wp {wp_pk}")
        # create link in wp hashdict
        r.hset(f"wp-{wp_pk}", "inv", pk)
        wp_dict = r.hgetall(f"wp-{pk}")
        if not smart_charging_enabled:
            print("sc not enabled -> allow max power")
            set_prop(wp_pk, "frc", 0) # auto
            set_prop(wp_pk, "psm", 0) # auto
            set_prop(wp_pk, "amp", MAX_AMPS)
        else:
            # logic processing
            print("sc enabled, applying logic")
            delta_kw = message_json['production'] - message_json['consumption']
            try:
                nrg_total_w = float(r.hget(f"wp-{wp_pk}", "nrg_ptotal"))
            except:
                nrg_total_w = 0 # assuming 0 power if no cache entry
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
                    if amps < MIN_AMPS:
                        print(f"{wp_pk}: requested less than {MIN_AMPS} amps (1-phase)")
                        amps = MIN_AMPS
                    elif amps > MAX_AMPS:
                        print(f"{wp_pk}: requested more than {MAX_AMPS} amps on (1-phase)!")
                        amps = MAX_AMPS
                    set_prop(wp_pk, "psm", psm) # 1-phase
                    set_prop(wp_pk, "amp", amps)
                else:
                    # 3-phase
                    psm = 0
                    amps = round(target_kw*1000/(400*1.73))
                    if amps < MIN_AMPS:
                        print(f"{wp_pk}: requested less than {MIN_AMPS} amps (3-phase)")
                        amps = MIN_AMPS
                    elif amps > MAX_AMPS:
                        print(f"{wp_pk}: requested more than {MAX_AMPS} amps (3-phase)")
                        amps = MAX_AMPS
                    set_prop(wp_pk, "psm", psm) # auto
                    set_prop(wp_pk, "amp", amps)
                print(f"{wp_pk}: target power > 1 kW -> allow charging ({amps}A; {psm}PSM)")
        print("====================")
    else:
        print("found no reg. wp")
