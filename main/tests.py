from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from main.models import HealthDataFile, HealthMetric, LLMAnalytics

class HealthDataViewsTestCase(APITestCase):
    def setUp(self):
        self.health_file = HealthDataFile.objects.create(file=SimpleUploadedFile("test.xml", b"<HealthData></HealthData>", content_type="text/xml"))
        self.metric = HealthMetric.objects.create(health_data=self.health_file, metric_type="HKQuantityTypeIdentifierStepCount", file="steps.csv")
        self.analysis = LLMAnalytics.objects.create(health_data=self.health_file, text="Sample analysis result")

    def test_upload_health_data(self):
        file = SimpleUploadedFile("test.xml", b"<HealthData></HealthData>", content_type="text/xml")
        response = self.client.post(reverse('upload-health-data'), {'file': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_health_data_files(self):
        response = self.client.get(reverse('list-health-data'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_health_metrics(self):
        response = self.client.get(reverse('list-csv') + f"?health_data_id={self.health_file.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_llm_analytics(self):
        response = self.client.get(reverse('list-analytics') + f"?health_data_id={self.health_file.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
