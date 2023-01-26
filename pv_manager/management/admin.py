import json
import os

from django.contrib import admin
from django.core.exceptions import ValidationError

from management.models import Inverter
from pv_manager import settings

admin.site.register(Inverter)
