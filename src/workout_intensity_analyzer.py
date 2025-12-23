#!/usr/bin/env python3
"""
Enhanced Workout Intensity Analyzer for Apple Health Data
Extracts heart rate data during workouts and calculates training zones
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import os


def calculate_heart_rate_zones(age=None, max_hr=None, resting_hr=None):
    """
    Calculate heart rate training zones.

    Zones based on percentage of max heart rate:
    - Zone 1: 50-60% (Very light)
    - Zone 2: 60-70% (Light)
    - Zone 3: 70-80% (Moderate)
    - Zone 4: 80-90% (Hard)
    - Zone 5: 90-100% (Maximum)
    """
    if max_hr is None:
        if age is None:
            # Default to age 35 if not provided
            age = 35
        # Traditional formula: 220 - age
        max_hr = 220 - age

    zones = {
        'zone_1': {'min': 0.50 * max_hr, 'max': 0.60 * max_hr, 'name': 'Very Light'},
        'zone_2': {'min': 0.60 * max_hr, 'max': 0.70 * max_hr, 'name': 'Light'},
        'zone_3': {'min': 0.70 * max_hr, 'max': 0.80 * max_hr, 'name': 'Moderate'},
        'zone_4': {'min': 0.80 * max_hr, 'max': 0.90 * max_hr, 'name': 'Hard'},
        'zone_5': {'min': 0.90 * max_hr, 'max': max_hr, 'name': 'Maximum'}
    }

    return zones, max_hr


def get_zone_from_hr(hr_value, zones):
    """Determine which zone a heart rate value falls into."""
    for zone_name, zone_range in zones.items():
        if zone_range['min'] <= hr_value <= zone_range['max']:
            return zone_name
    if hr_value > zones['zone_5']['max']:
        return 'zone_5'
    return 'zone_1'


def parse_heart_rate_records(export_path):
    """Extract all heart rate records from the export.xml file."""
    print("Parsing heart rate records...")
    tree = ET.parse(export_path)
    root = tree.getroot()

    hr_records = []
    for record in root.findall('.//Record'):
        if record.get('type') == 'HKQuantityTypeIdentifierHeartRate':
            try:
                hr_value = float(record.get('value'))
                # Use startDate for heart rate records to get the actual reading time
                date_str = record.get('startDate')
                date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
                source = record.get('sourceName', 'Unknown')

                hr_records.append({
                    'timestamp': date,
                    'heart_rate': hr_value,
                    'source': source
                })
            except (ValueError, TypeError):
                continue

    print(f"Found {len(hr_records)} heart rate records")
    return pd.DataFrame(hr_records).sort_values('timestamp')


def extract_workout_events(workout_element):
    """Extract workout events like pause/resume from a workout element."""
    events = []
    for event in workout_element.findall('.//WorkoutEvent'):
        event_type = event.get('type')
        date_str = event.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
            events.append({
                'type': event_type,
                'timestamp': date
            })
    return events


def analyze_workout_intensity(export_path, age=None, max_hr=None):
    """
    Analyze workout intensity by linking heart rate data to workouts.
    Returns enhanced workout data with heart rate zones.
    """
    print("Starting enhanced workout intensity analysis...")

    # Parse heart rate records
    hr_df = parse_heart_rate_records(export_path)

    if hr_df.empty:
        print("No heart rate data found!")
        return None

    # Calculate heart rate zones
    zones, calculated_max_hr = calculate_heart_rate_zones(age, max_hr)
    print(f"Using max heart rate: {calculated_max_hr}")

    # Parse workouts
    tree = ET.parse(export_path)
    root = tree.getroot()

    enhanced_workouts = []

    for workout in root.findall('.//Workout'):
        try:
            # Extract basic workout info
            activity_type = workout.get('workoutActivityType', 'Unknown')
            duration_str = workout.get('duration')
            duration_unit = workout.get('durationUnit', 'min')
            start_date_str = workout.get('startDate')
            end_date_str = workout.get('endDate')
            source_name = workout.get('sourceName', 'Unknown')

            if not duration_str or not start_date_str:
                continue

            # Parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S %z')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S %z')

            # Convert duration to minutes
            duration_value = float(duration_str)
            if duration_unit == 'min':
                duration_minutes = duration_value
            elif duration_unit == 'sec':
                duration_minutes = duration_value / 60
            elif duration_unit == 'h':
                duration_minutes = duration_value * 60
            else:
                duration_minutes = duration_value

            # Extract existing statistics
            calories = 0
            distance_km = 0
            avg_hr_from_stats = None

            for stat in workout.findall('.//WorkoutStatistics'):
                stat_type = stat.get('type', '')
                sum_value = stat.get('sum')
                avg_value = stat.get('average')

                if sum_value:
                    if 'ActiveEnergyBurned' in stat_type:
                        calories = float(sum_value)
                    elif 'DistanceWalkingRunning' in stat_type or 'DistanceCycling' in stat_type:
                        unit = stat.get('unit', '')
                        if unit == 'km':
                            distance_km = float(sum_value)
                        elif unit == 'm':
                            distance_km = float(sum_value) / 1000

                # Check if Apple already calculated average heart rate
                if 'HeartRate' in stat_type and avg_value:
                    avg_hr_from_stats = float(avg_value)

            # Extract workout events
            events = extract_workout_events(workout)

            # Find heart rate data during this workout
            # Add a small buffer (1 minute) to catch HR data at boundaries
            buffer = timedelta(minutes=1)
            workout_hr = hr_df[
                (hr_df['timestamp'] >= start_date - buffer) &
                (hr_df['timestamp'] <= end_date + buffer)
            ]

            # Calculate heart rate statistics if we have data
            hr_stats = {}
            zone_time = defaultdict(float)
            zone_percentages = {}

            if not workout_hr.empty:
                hr_values = workout_hr['heart_rate'].values
                hr_stats = {
                    'hr_count': len(hr_values),
                    'hr_avg': float(workout_hr['heart_rate'].mean()),
                    'hr_max': float(workout_hr['heart_rate'].max()),
                    'hr_min': float(workout_hr['heart_rate'].min()),
                    'hr_std': float(workout_hr['heart_rate'].std())
                }

                # Calculate time in each zone
                # Assuming HR readings are roughly evenly spaced during workout
                time_per_reading = duration_minutes / len(hr_values) if len(hr_values) > 0 else 0

                for hr in hr_values:
                    zone = get_zone_from_hr(hr, zones)
                    zone_time[zone] += time_per_reading

                # Calculate zone percentages
                for zone in ['zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5']:
                    zone_percentages[f'{zone}_percent'] = round(
                        (zone_time[zone] / duration_minutes * 100) if duration_minutes > 0 else 0,
                        1
                    )
                    zone_percentages[f'{zone}_minutes'] = round(zone_time[zone], 1)

            # Combine all workout data
            workout_data = {
                'date': start_date.date(),
                'start_time': start_date,
                'end_time': end_date,
                'activity_type': activity_type.replace('HKWorkoutActivityType', ''),
                'duration_minutes': round(duration_minutes, 1),
                'duration_hours': round(duration_minutes / 60, 2),
                'calories': round(calories, 1),
                'distance_km': round(distance_km, 2),
                'source': source_name,
                'workout_events': len(events),
                'has_pauses': any(e['type'] == 'HKWorkoutEventTypePause' for e in events)
            }

            # Add heart rate statistics
            workout_data.update(hr_stats)
            workout_data.update(zone_percentages)

            # Add Apple's average HR if available
            if avg_hr_from_stats:
                workout_data['hr_avg_apple'] = avg_hr_from_stats

            enhanced_workouts.append(workout_data)

        except Exception as e:
            print(f"Error processing workout: {e}")
            continue

    if not enhanced_workouts:
        print("No workouts found!")
        return None

    # Create DataFrame and sort by date
    df = pd.DataFrame(enhanced_workouts)
    df = df.sort_values('start_time')

    # Print summary
    print(f"\nProcessed {len(df)} workouts with heart rate data")
    workouts_with_hr = df[df['hr_count'] > 0] if 'hr_count' in df.columns else pd.DataFrame()
    print(f"Workouts with heart rate data: {len(workouts_with_hr)}")

    if len(workouts_with_hr) > 0:
        print("\nHeart Rate Zone Summary across all workouts:")
        for zone in ['zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5']:
            col = f'{zone}_percent'
            if col in workouts_with_hr.columns:
                avg_percent = workouts_with_hr[col].mean()
                zone_info = zones[zone]
                print(f"  {zone.replace('_', ' ').title()} ({zone_info['name']}, "
                      f"{int(zone_info['min'])}-{int(zone_info['max'])} bpm): "
                      f"{avg_percent:.1f}% average time")

    return df, zones


def export_enhanced_workout_data(df, output_path):
    """Export the enhanced workout data to CSV."""
    csv_path = os.path.join(output_path, 'enhanced_workout_data.csv')
    df.to_csv(csv_path, index=False)
    print(f"\nEnhanced workout data exported to {csv_path}")
    return csv_path


def generate_ai_prompt_with_intensity(df, zones):
    """Generate an AI analysis prompt that includes workout intensity data."""
    prompt = "Enhanced Workout Analysis with Heart Rate Zones:\n\n"

    # Overall statistics
    workouts_with_hr = df[df['hr_count'] > 0] if 'hr_count' in df.columns else pd.DataFrame()

    prompt += f"Total Workouts: {len(df)}\n"
    prompt += f"Workouts with HR data: {len(workouts_with_hr)}\n"
    prompt += f"Date Range: {df['date'].min()} to {df['date'].max()}\n\n"

    if len(workouts_with_hr) > 0:
        # Heart rate statistics
        prompt += "Heart Rate Statistics:\n"
        prompt += f"- Average HR across workouts: {workouts_with_hr['hr_avg'].mean():.1f} bpm\n"
        prompt += f"- Highest max HR: {workouts_with_hr['hr_max'].max():.0f} bpm\n"
        prompt += f"- Average max HR: {workouts_with_hr['hr_max'].mean():.1f} bpm\n\n"

        # Zone distribution
        prompt += "Training Zone Distribution (% of workout time):\n"
        for zone in ['zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5']:
            col = f'{zone}_percent'
            if col in workouts_with_hr.columns:
                avg_percent = workouts_with_hr[col].mean()
                zone_info = zones[zone]
                prompt += f"- {zone.replace('_', ' ').title()} ({zone_info['name']}, "
                prompt += f"{int(zone_info['min'])}-{int(zone_info['max'])} bpm): "
                prompt += f"{avg_percent:.1f}%\n"

        prompt += "\n"

        # Activity type breakdown with intensity
        prompt += "Workout Types with Average Intensity:\n"
        activity_stats = workouts_with_hr.groupby('activity_type').agg({
            'duration_minutes': ['count', 'mean'],
            'hr_avg': 'mean',
            'zone_4_percent': 'mean',
            'zone_5_percent': 'mean'
        }).round(1)

        for activity in activity_stats.index[:10]:
            count = activity_stats.loc[activity, ('duration_minutes', 'count')]
            avg_duration = activity_stats.loc[activity, ('duration_minutes', 'mean')]
            avg_hr = activity_stats.loc[activity, ('hr_avg', 'mean')]
            high_intensity = (activity_stats.loc[activity, ('zone_4_percent', 'mean')] +
                            activity_stats.loc[activity, ('zone_5_percent', 'mean')])
            prompt += f"- {activity}: {count} workouts, avg {avg_duration:.1f} min, "
            prompt += f"avg HR {avg_hr:.0f} bpm, {high_intensity:.1f}% high intensity\n"

        prompt += "\n"

        # Recent intense workouts
        prompt += "Recent High-Intensity Workouts (>50% time in zones 4-5):\n"
        high_intensity_workouts = workouts_with_hr[
            (workouts_with_hr['zone_4_percent'] + workouts_with_hr['zone_5_percent']) > 50
        ].sort_values('start_time', ascending=False).head(10)

        for _, workout in high_intensity_workouts.iterrows():
            high_percent = workout['zone_4_percent'] + workout['zone_5_percent']
            prompt += f"- {workout['date']}: {workout['activity_type']}, "
            prompt += f"{workout['duration_minutes']:.1f} min, "
            prompt += f"avg HR {workout['hr_avg']:.0f}, max HR {workout['hr_max']:.0f}, "
            prompt += f"{high_percent:.1f}% high intensity\n"

    prompt += "\nPlease analyze this enhanced workout data, focusing on:\n"
    prompt += "1. Training intensity patterns and zone distribution\n"
    prompt += "2. Whether the user is training too hard, too easy, or balanced\n"
    prompt += "3. Specific insights about high-intensity training (zones 4-5)\n"
    prompt += "4. Recommendations for optimizing training intensity\n"
    prompt += "5. Any concerning patterns in heart rate data\n"

    return prompt


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python workout_intensity_analyzer.py <path_to_export.xml> [age] [max_hr]")
        sys.exit(1)

    export_path = sys.argv[1]
    age = int(sys.argv[2]) if len(sys.argv) > 2 else None
    max_hr = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # Run analysis
    df, zones = analyze_workout_intensity(export_path, age, max_hr)

    if df is not None:
        # Export enhanced data
        output_path = os.path.dirname(export_path) or '.'
        export_enhanced_workout_data(df, output_path)

        # Generate AI prompt
        prompt = generate_ai_prompt_with_intensity(df, zones)
        print("\n" + "="*50)
        print("AI ANALYSIS PROMPT:")
        print("="*50)
        print(prompt)