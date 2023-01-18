import datetime

from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from django.db import models

# Create your models here.
class Inverter(models.Model):
    name = models.CharField(max_length=50)
    ip = models.GenericIPAddressField(default="127.0.0.1")
    token = models.CharField(max_length=100)
    site_id = models.CharField(max_length=10)
    from_grid = models.FloatField(default=-1)
    last_fetch = models.DateTimeField(null=True, blank=True)

    @property
    def pv_delta_kw(self):
        return self.production - self.consumption

    def fetch_optimizers(self):
        communication_method, connected_optimizers = get_connectedOptimizers(self.site_id, self.token)
        self.communication_method = communication_method
        self.optimizers = connected_optimizers
        inverter_status_to_influx(communication_method, connected_optimizers, self.pk)
        self.save()

    def fetch_power_flow(self):
        prod, cons, grid = get_currentPowerFlow(self.site_id, self.token)
        self.production = prod
        self.consumption = cons
        self.from_grid = grid
        self.last_fetch = datetime.datetime.utcnow()
        inverter_stats_to_influx(prod, cons, grid, self.pk)
        self.save(update_fields=("production", "consumption", "from_grid", "last_fetch",))


class Wattpilot(models.Model):
    class WattpilotState(models.TextChoices):
        IDLE = 'ID', _('Idle')
        WAIT_CAR = 'WC', _('WaitCar')
        CHARGING = 'CH', _('Charging')
        COMPLETE = 'CO', _('Complete')
        ERROR = 'ER', _('Error')

    name = models.CharField(max_length=50)
    inverter = models.ForeignKey(Inverter, on_delete=models.SET_NULL, null=True, blank=True)
    ip = models.GenericIPAddressField(default="127.0.0.1")
    mqtt_ip = models.GenericIPAddressField(default="127.0.0.1")
    smart_charging_enabled = models.BooleanField(default=False)
    target_kw = models.FloatField(default=11)
    actual_energy_watt = models.IntegerField(default=-1)
    current_amps = models.IntegerField(validators=(MinValueValidator(-1), MaxValueValidator(16),))
    psm = models.IntegerField(validators=(MinValueValidator(0), MaxValueValidator(2),))
    forced_state = models.IntegerField(validators=(MinValueValidator(0), MaxValueValidator(2),))
    data_connected = models.BooleanField(default=False)
    state = models.CharField(
        max_length=2,
        choices=WattpilotState.choices,
        default=WattpilotState.IDLE,
    )
    last_logic_action = models.CharField(max_length=100, default="-")
    last_logic_action_ts = models.DateTimeField(null=True, blank=True)

    @property
    def actual_energy_kw(self):
        return self.actual_energy_watt / 1000

    @property
    def current_power_kw(self):
        if self.psm == 1:
            return (self.current_amps * c_233_3) / 1000
        else:
            return (self.current_amps * (400*1.73)) / 1000