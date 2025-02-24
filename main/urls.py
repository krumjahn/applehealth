from django.urls import path
from .views import *

urlpatterns = [
    path('export/upload/', UploadHealthDataView.as_view(), name='upload_health_data'),
    path('export/analyze/', HealthDataAnalysisView.as_view(), name='analyze-health-data'),

    path('csv/steps/<int:export_id>/', StepsView.as_view(), name='steps_data'),
    path('csv/distance/<int:export_id>/', DistanceView.as_view(), name='distance_data'),
    path('csv/heart-rate/<int:export_id>/', HeartRateView.as_view(), name='heart_rate_data'),
    path('csv/weight/<int:export_id>/', WeightView.as_view(), name='weight_data'),
    path('csv/sleep/<int:export_id>/', SleepView.as_view(), name='sleep_data'),

    path('list/export', HealthDataFileListView.as_view(), name='list-health-data'),
    path('list/csv', HealthMetricListView.as_view(), name='list-csv'),
    path('list/analytics', LLMAnalyticsListView.as_view(), name='list-analytics'),
]