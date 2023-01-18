import os
import requests
from google.cloud import pubsub_v1

# id
# ip
# token

inverters = {0: {"ip": "127.0.0.1", "token" :"yeehah"}}

publisher = pubsub_v1.PublisherClient()
topic_name = 'projects/{project_id}/topics/{topic}'.format(
    project_id="clc3-375021",
    topic='clc-test-topic',  # Set this to something appropriate.
)
#publisher.create_topic(name=topic_name)
future = publisher.publish(topic_name, b'My first message!')
future.result()
        