from django.db import models


class Inverter(models.Model):
    name = models.CharField(max_length=50)
    token = models.CharField(max_length=100)
    site_id = models.CharField(max_length=10)


class Wattpilot(models.Model):
    name = models.CharField(max_length=50)
    inverter = models.ForeignKey(Inverter, on_delete=models.SET_NULL, null=True, blank=True)
    ip = models.GenericIPAddressField(default="127.0.0.1")
    mqtt_ip = models.GenericIPAddressField(default="127.0.0.1")
    smart_charging_enabled = models.BooleanField(default=False)
