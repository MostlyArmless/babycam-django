from rest_framework import serializers
from .models import MonitorDevice, AudioEvent


class MonitorDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorDevice
        fields = [
            "id",
            "name",
            "stream_url",
            "is_active",
            "is_authenticated",
            "username",
            "password",
        ]


class AudioEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioEvent
        fields = [
            "id",
            "device",
            "timestamp",
            "peak_value",
            "alert_level",
            "recording_path",
        ]
