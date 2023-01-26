from django.db import models


class Inverter(models.Model):
    name = models.CharField(max_length=50)
    token = models.CharField(max_length=100)
    site_id = models.CharField(max_length=10)
    wattpilot_id = models.IntegerField(null=False, default=-1)
    smart_charging_enabled = models.BooleanField(default=False, null=False)
