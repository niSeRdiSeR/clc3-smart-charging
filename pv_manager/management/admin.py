import json
import os

from django.contrib import admin
from django.core.exceptions import ValidationError

from management.models import Wattpilot, Inverter
from google.cloud import pubsub_v1

from pv_manager import settings

publisher = pubsub_v1.PublisherClient()
project_path = f"projects/{settings.PROJECT_ID}"


class WattpilotAdmin(admin.ModelAdmin):
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        topic_path = publisher.topic_path(settings.PROJECT_ID, settings.WATTPILOT_TOPIC)
        topic_strings = [t.name for t in publisher.list_topics(request={"project": project_path})]

        if topic_path not in topic_strings:
            publisher.create_topic(request={"name": topic_path})

        config = {
            "wp_pk": obj.pk,
            "wp_ip": obj.ip,
            "wp_mqtt_ip": obj.mqtt_ip,
            "wp_sc_enabled": obj.smart_charging_enabled,
            "wp_inv_pk": obj.inverter.pk if obj.inverter else None
        }
        publisher.publish(topic_path, json.dumps(config).encode('utf-8'))


class InverterAdmin(admin.ModelAdmin):
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        topic_path = publisher.topic_path(settings.PROJECT_ID, settings.INVERTER_TOPIC)
        topic_strings = [t.name for t in publisher.list_topics(request={"project": project_path})]

        if topic_path not in topic_strings:
            publisher.create_topic(request={"name": topic_path})

        config = {
            "inv_pk": obj.pk,
            "inv_site_id": obj.site_id,
            "inv_token": obj.token,
        }
        publisher.publish(topic_path, json.dumps(config).encode('utf-8'))


admin.site.register(Wattpilot, WattpilotAdmin)
admin.site.register(Inverter)
