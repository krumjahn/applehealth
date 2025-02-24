from rest_framework import serializers
from .models import HealthDataFile, HealthMetric, LLMAnalytics


class HealthDataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthDataFile
        fields = '__all__'

class HealthMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthMetric
        fields = '__all__'

class LLMAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMAnalytics
        fields = '__all__'
