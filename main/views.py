import os
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd
import requests
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HealthDataFile, HealthMetric, LLMAnalytics
from .serializers import HealthDataFileSerializer, HealthMetricSerializer, LLMAnalyticsSerializer

from django.conf import settings


# Helper function to parse Apple Health data
def parse_health_data(file_path, record_type):
    tree = ET.parse(file_path)
    root = tree.getroot()
    dates, values = [], []

    for record in root.findall('.//Record'):
        if record.get('type') == record_type:
            try:
                value = float(record.get('value'))
                date = datetime.strptime(record.get('endDate'), '%Y-%m-%d %H:%M:%S %z')
                dates.append(date)
                values.append(value)
            except (ValueError, TypeError):
                continue

    return pd.DataFrame({'date': dates, 'value': values})


class UploadHealthDataView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Upload Apple Health export.xml file",
        manual_parameters=[
            openapi.Parameter(
                name="file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="Apple Health XML file",
                required=True
            )
        ],
        responses={201: "File uploaded successfully", 400: "No file provided"}
    )
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        health_file = HealthDataFile(file=file_obj)
        health_file.save()

        return Response({
            'message': 'File uploaded successfully',
            'file_id': health_file.id
        }, status=status.HTTP_201_CREATED)


# Generic API View for retrieving health metrics
class HealthMetricView(APIView):
    metric_type = None

    def get(self, request, export_id, *args, **kwargs):
        health_data = get_object_or_404(HealthDataFile, id=export_id)
        file_path = health_data.file.path

        df = parse_health_data(file_path, self.metric_type)

        if 'date' not in df.columns:
            return Response({'error': 'Column "date" not found in data'}, status=400)

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])

        df_grouped = df.groupby(df['date'].dt.date)['value'].sum().reset_index()
        df_grouped.rename(columns={'date': 'date', 'value': 'total_value'}, inplace=True)

        upload_dir = "health_metrics/"
        os.makedirs(upload_dir, exist_ok=True)

        csv_filename = f'{self.metric_type}_{export_id}.csv'
        csv_path = os.path.join(upload_dir, csv_filename)
        df_grouped.to_csv(csv_path, index=False)

        metric_file = HealthMetric(health_data=health_data, metric_type=self.metric_type, file=csv_path)
        metric_file.save()

        csv_url = request.build_absolute_uri(metric_file.file.url)

        return Response({
            'message': 'Data saved to database',
            'file_id': metric_file.id,
            'csv_url': csv_url
        })


# Specific views for each metric
class StepsView(HealthMetricView):
    metric_type = 'HKQuantityTypeIdentifierStepCount'


class DistanceView(HealthMetricView):
    metric_type = 'HKQuantityTypeIdentifierDistanceWalkingRunning'


class HeartRateView(HealthMetricView):
    metric_type = 'HKQuantityTypeIdentifierHeartRate'


class WeightView(HealthMetricView):
    metric_type = 'HKQuantityTypeIdentifierBodyMass'


class SleepView(HealthMetricView):
    metric_type = 'HKCategoryTypeIdentifierSleepAnalysis'


class ExportWorkoutDataView(APIView):
    def get(self, request, export_id):
        health_data = get_object_or_404(HealthDataFile, id=export_id)
        tree = ET.parse(health_data.file.path)
        root = tree.getroot()

        daily_workouts = {}

        for record in root.findall('.//Record'):
            if record.get('sourceName') == 'WHOOP':
                try:
                    date = datetime.strptime(record.get('startDate'), '%Y-%m-%d %H:%M:%S %z')
                    day = date.date()
                    heart_rate = float(record.get('value'))

                    if day not in daily_workouts:
                        daily_workouts[day] = {
                            'total_minutes': 0,
                            'heart_rates': [],
                            'measurement_count': 0
                        }

                    daily_workouts[day]['heart_rates'].append(heart_rate)
                    daily_workouts[day]['measurement_count'] += 1
                except (ValueError, TypeError):
                    continue

        if not daily_workouts:
            return Response({'message': 'No workout data found!'}, status=status.HTTP_404_NOT_FOUND)

        workout_days = []

        for day, data in daily_workouts.items():
            estimated_minutes = data['measurement_count'] * (6 / 60)
            avg_hr = sum(data['heart_rates']) / len(data['heart_rates']) if data['heart_rates'] else 0

            workout_days.append({
                'date': day,
                'duration_hours': estimated_minutes / 60,
                'avg_heart_rate': round(avg_hr, 1),
                'measurements': data['measurement_count']
            })

        df = pd.DataFrame(workout_days)
        df = df.sort_values('date')

        upload_dir = "health_metrics/"
        os.makedirs(upload_dir, exist_ok=True)

        csv_filename = f'workout_{export_id}.csv'
        csv_path = os.path.join(upload_dir, csv_filename)
        df.to_csv(csv_path, index=False)

        summary = {
            "total_days": len(df),
            "avg_daily_duration": round(df['duration_hours'].mean(), 2) if not df.empty else 0,
            "total_duration": round(df['duration_hours'].sum(), 2),
            "avg_heart_rate": round(df['avg_heart_rate'].mean(), 1) if not df.empty else 0,
        }

        summary_text = f"Total days: {summary['total_days']}\n" \
                       f"Avg daily workout: {summary['avg_daily_duration']} hours\n" \
                       f"Total time: {summary['total_duration']} hours\n" \
                       f"Avg heart rate: {summary['avg_heart_rate']} BPM\n"

        metric_file = HealthMetric(health_data=health_data, summary_text=summary_text, file=csv_path)
        metric_file.save()

        csv_url = request.build_absolute_uri(metric_file.file.url)

        return JsonResponse({
            "message": "Workout data exported successfully",
            "csv_url": csv_url,
            "summary": summary
        })


class HealthDataAnalysisView(APIView):
    @swagger_auto_schema(
        operation_description="Analyze health data by providing a export_id",
        manual_parameters=[
            openapi.Parameter(
                'export_id',
                openapi.IN_QUERY,
                description="ID of the HealthDataFile",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: openapi.Response("Analysis result", openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            "analysis": openapi.Schema(type=openapi.TYPE_STRING)
        }))}
    )
    def get(self, request, *args, **kwargs):
        try:
            health_data_id = request.GET.get('export_id')
            if not health_data_id:
                return Response({"error": "health_data_id is required."}, status=status.HTTP_400_BAD_REQUEST)

            health_data = get_object_or_404(HealthDataFile, id=health_data_id)
            health_metrics = HealthMetric.objects.filter(health_data=health_data)

            if not health_metrics.exists():
                return Response({"error": "No files found for the given health_data_id."},
                                status=status.HTTP_400_BAD_REQUEST)

            data_summary = {}
            files_found = False

            for metric in health_metrics:
                try:
                    df = pd.read_csv(metric.file.path)
                    data_type = metric.metric_type or metric.file.name

                    data_summary[data_type] = {
                        'total_records': len(df),
                        'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df else 'N/A',
                        'average': f"{df['value'].mean():.2f}" if 'value' in df else 'N/A',
                        'max_value': f"{df['value'].max():.2f}" if 'value' in df else 'N/A',
                        'min_value': f"{df['value'].min():.2f}" if 'value' in df else 'N/A',
                        'data_sample': df.head(50).to_string()
                    }
                    files_found = True
                except Exception as e:
                    return Response({"error": f"Error processing {metric.file.name}: {str(e)}"},
                                    status=status.HTTP_400_BAD_REQUEST)

            if not files_found:
                return Response({"error": "No valid data files found."}, status=status.HTTP_400_BAD_REQUEST)

            prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
            for data_type, summary in data_summary.items():
                prompt += f"\n{data_type} Data Summary:\n"
                prompt += f"- Total Records: {summary['total_records']}\n"
                prompt += f"- Date Range: {summary['date_range']}\n"
                prompt += f"- Average Value: {summary['average']}\n"
                prompt += f"- Maximum Value: {summary['max_value']}\n"
                prompt += f"- Minimum Value: {summary['min_value']}\n"
                prompt += f"\nSample Data:\n{summary['data_sample']}\n"
                prompt += "\n" + "=" * 50 + "\n"

            prompt += """Please provide a comprehensive analysis including:
            1. Notable patterns or trends in the data
            2. Unusual findings or correlations between different metrics
            3. Actionable health insights based on the data
            4. Areas that might need attention or improvement
            """

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "deepseek/deepseek-r1",
                "messages": [
                    {"role": "system",
                     "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 6144
            }
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                analysis_result = result["choices"][0]["message"]["content"]

                LLMAnalytics.objects.create(
                    health_data=health_data,
                    text=analysis_result
                )

                return Response({"analysis": analysis_result}, status=status.HTTP_200_OK)
            else:
                return Response({"error": f"API error: {response.status_code}, {response.text}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthDataFileListView(APIView):
    def get(self, request):
        files = HealthDataFile.objects.all()
        serializer = HealthDataFileSerializer(files, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class HealthMetricListView(APIView):
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('export_id', openapi.IN_QUERY, description="ID of the health data file",
                          type=openapi.TYPE_INTEGER)
    ])
    def get(self, request):
        health_data_id = request.GET.get('export_id')
        if not health_data_id:
            return Response({'error': 'export_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        metrics = HealthMetric.objects.filter(health_data_id=health_data_id)
        serializer = HealthMetricSerializer(metrics, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LLMAnalyticsListView(APIView):
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('export_id', openapi.IN_QUERY, description="ID of the health data file",
                          type=openapi.TYPE_INTEGER)
    ])
    def get(self, request):
        health_data_id = request.GET.get('export_id')
        if not health_data_id:
            return Response({'error': 'export_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        llm_data = LLMAnalytics.objects.filter(health_data_id=health_data_id)
        serializer = LLMAnalyticsSerializer(llm_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
