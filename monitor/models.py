from django.db import models

class MonitorDevice(models.Model):
    name = models.CharField(max_length=100)
    stream_url = models.URLField()
    is_authenticated = models.BooleanField(default=False)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    yellow_threshold = models.IntegerField(default=1000)
    red_threshold = models.IntegerField(default=5000)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AudioEvent(models.Model):
    device = models.ForeignKey(MonitorDevice, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    peak_value = models.IntegerField()
    alert_level = models.CharField(
        max_length=10,
        choices=[('NONE', 'None'), ('YELLOW', 'Yellow'), ('RED', 'Red')]
    )
    recording_path = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.device.name} - {self.alert_level} - {self.timestamp}"