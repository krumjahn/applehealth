from django.db import models

class HealthDataFile(models.Model):
    file = models.FileField(upload_to='health_data/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class HealthMetric(models.Model):
    health_data = models.ForeignKey(HealthDataFile, on_delete=models.CASCADE, related_name="health_metrics")
    metric_type = models.CharField(max_length=250,null=True)
    summary_text = models.CharField(max_length=2500,null=True)
    file = models.FileField(upload_to='health_metrics/')
    created_at = models.DateTimeField(auto_now_add=True)

class LLMAnalytics(models.Model):
    health_data = models.ForeignKey(HealthDataFile, on_delete=models.CASCADE, related_name="llm_metrics")
    text = models.CharField(max_length=2500,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
