"""
Apple Health Data Analyzer
-------------------------

This script analyzes exported Apple Health data (export.xml) with a focus on:
- Steps
- Walking/Running Distance
- Heart Rate
- Weight
- Sleep
- Workouts (specifically WHOOP workout data)

Requirements:
- Python 3.6+
- pandas
- matplotlib7
- xml.etree.ElementTree
- openai
- dotenv
- ollama

Usage:
1. Export your Apple Health data from the Health app on your iPhone
2. Place the 'export.xml' file in the same directory as this script
3. Run the script and choose which health metric to analyze

Author: Keith Rumjahn
License: MIT
Version: 1.0.0
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pandas import DataFrame, read_csv
from pandas.core.groupby import DataFrameGroupBy
import matplotlib.pyplot as plt
import openai
import os
from dotenv import load_dotenv
import sys
import ollama

def parse_health_data(file_path, record_type):
    """
    Parse specific health metrics from Apple Health export.xml file.
    
    Args:
        file_path (str): Path to the export.xml file
        record_type (str): The type of health record to parse (e.g., 'HKQuantityTypeIdentifierStepCount')
    
    Returns:
        pandas.DataFrame: DataFrame containing dates and values for the specified metric
    """
    print(f"Starting to parse {record_type}...")
    dates = []
    values = []
    
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    print("XML file loaded, searching records...")
    
    for record in root.findall('.//Record'):
        if record.get('type') == record_type:
            try:
                value = float(record.get('value'))
                date = datetime.strptime(record.get('endDate'), '%Y-%m-%d %H:%M:%S %z')
                dates.append(date)
                values.append(value)
            except (ValueError, TypeError):
                continue
    
    print(f"Found {len(dates)} records")
    return DataFrame({'date': dates, 'value': values})

def analyze_steps():
    """
    Analyze and visualize daily step count data.
    Shows a time series plot of daily total steps and exports data to CSV.
    """
    export_path = '../export.xml' if not os.path.exists('export.xml') else 'export.xml'
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierStepCount')
    
    # Check if any step data was found
    if len(df) == 0:
        print("No step data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv('steps_data.csv', index=False)
        print("Created empty steps_data.csv file.")
        return
    
    # Daily sum of steps
    daily_steps = df.groupby(df['date'].dt.date)['value'].sum()
    
    # Export to CSV
    daily_steps.to_csv('steps_data.csv', header=True)
    print("Steps data exported to 'steps_data.csv'")
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_steps.plot()
    plt.title('Daily Steps')
    plt.xlabel('Date')
    plt.ylabel('Steps')
    plt.grid(True)
    plt.show()

def analyze_distance():
    """
    Analyze and visualize daily walking/running distance.
    Shows a time series plot of daily total distance in kilometers and exports data to CSV.
    """
    export_path = '../export.xml' if not os.path.exists('export.xml') else 'export.xml'
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierDistanceWalkingRunning')
    
    # Check if any distance data was found
    if len(df) == 0:
        print("No distance data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv('distance_data.csv', index=False)
        print("Created empty distance_data.csv file.")
        return
    
    # Daily sum of distance (already in kilometers from Apple Health)
    daily_distance = df.groupby(df['date'].dt.date)['value'].sum()
    
    # Export to CSV
    daily_distance.to_csv('distance_data.csv', header=True)
    print("Distance data exported to 'distance_data.csv'")
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_distance.plot()
    plt.title('Daily Walking/Running Distance')
    plt.xlabel('Date')
    plt.ylabel('Distance (km)')
    plt.grid(True)
    plt.show()

def analyze_heart_rate():
    """
    Analyze and visualize daily heart rate data.
    Shows a time series plot of daily average heart rate in BPM and exports data to CSV.
    """
    export_path = '../export.xml' if not os.path.exists('export.xml') else 'export.xml'
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierHeartRate')
    
    # Check if any heart rate data was found
    if len(df) == 0:
        print("No heart rate data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv('heart_rate_data.csv', index=False)
        print("Created empty heart_rate_data.csv file.")
        return
    
    # Daily average heart rate
    daily_hr = df.groupby(df['date'].dt.date)['value'].mean()
    
    # Export to CSV
    daily_hr.to_csv('heart_rate_data.csv', header=True)
    print("Heart rate data exported to 'heart_rate_data.csv'")
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_hr.plot()
    plt.title('Daily Average Heart Rate')
    plt.xlabel('Date')
    plt.ylabel('Heart Rate (BPM)')
    plt.grid(True)
    plt.show()

def analyze_weight():
    """
    Analyze and visualize body weight data.
    Shows a time series plot of daily weight measurements in kg.
    """
    export_path = '../export.xml' if not os.path.exists('export.xml') else 'export.xml'
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierBodyMass')
    
    # Check if any weight data was found
    if len(df) == 0:
        print("No weight data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv('weight_data.csv', index=False)
        print("Created empty weight_data.csv file.")
        return
    
    # Daily weight (taking the last measurement of each day)
    daily_weight = df.groupby(df['date'].dt.date)['value'].last()
    
    # Export to CSV
    daily_weight.to_csv('weight_data.csv', header=True)
    print("Weight data exported to 'weight_data.csv'")

    # Plot
    plt.figure(figsize=(12, 6))
    daily_weight.plot()
    plt.title('Body Weight Over Time')
    plt.xlabel('Date')
    plt.ylabel('Weight (kg)')
    plt.grid(True)
    plt.show()

def analyze_sleep():
    """
    Analyze and visualize sleep duration data.
    Shows a time series plot of daily total sleep duration in hours.
    """
    print("Analyzing sleep data...")
    export_path = '../export.xml' if not os.path.exists('export.xml') else 'export.xml'
    tree = ET.parse(export_path)
    root = tree.getroot()
    
    sleep_records = []
    
    # Process sleep records
    for record in root.findall('.//Record'):
        if record.get('type') == 'HKCategoryTypeIdentifierSleepAnalysis':
            try:
                start_date_str = record.get('startDate')
                end_date_str = record.get('endDate')
                sleep_value = record.get('value')
                source_name = record.get('sourceName', 'Unknown')
                
                if not start_date_str or not end_date_str or not sleep_value:
                    continue
                    
                # Parse dates
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S %z')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S %z')
                
                # Calculate duration in minutes
                duration_minutes = (end_date - start_date).total_seconds() / 60
                
                # Classify sleep type
                sleep_type = 'Unknown'
                if 'InBed' in sleep_value:
                    sleep_type = 'In Bed'
                elif 'AsleepUnspecified' in sleep_value:
                    sleep_type = 'Asleep'
                elif 'AsleepREM' in sleep_value:
                    sleep_type = 'REM Sleep'
                elif 'AsleepCore' in sleep_value:
                    sleep_type = 'Core Sleep'
                elif 'AsleepDeep' in sleep_value:
                    sleep_type = 'Deep Sleep'
                elif 'Awake' in sleep_value:
                    sleep_type = 'Awake'
                
                sleep_records.append({
                    'date': start_date.date(),
                    'start_time': start_date.time(),
                    'end_time': end_date.time(),
                    'duration_minutes': round(duration_minutes, 1),
                    'duration_hours': round(duration_minutes / 60, 2),
                    'sleep_type': sleep_type,
                    'sleep_value': sleep_value,
                    'source': source_name
                })
                
            except (ValueError, TypeError) as e:
                continue
    
    if not sleep_records:
        print("No sleep data found!")
        return
        
    df = DataFrame(sleep_records)
    df = df.sort_values('date')
    
    # Export to CSV
    export_df = df.copy()
    export_df['date'] = export_df['date'].astype(str)
    export_df.to_csv('sleep_data.csv', index=False)
    print(f"\nSleep data exported to 'sleep_data.csv'")
    print(f"Exported {len(export_df)} sleep records")
    
    # Display first few rows
    print("\nFirst few rows of exported data:")
    print(export_df.head())
    
    # Calculate daily sleep totals (excluding 'Awake' periods for actual sleep time)
    sleep_only = df[~df['sleep_type'].isin(['Awake', 'In Bed'])]
    daily_sleep = sleep_only.groupby('date')['duration_hours'].sum()
    
    # Also calculate total time in bed
    in_bed_data = df[df['sleep_type'] == 'In Bed']
    daily_in_bed = in_bed_data.groupby('date')['duration_hours'].sum()
    
    # Plot
    plt.figure(figsize=(12, 8))
    
    # Plot 1: Daily sleep duration
    plt.subplot(2, 1, 1)
    if len(daily_sleep) > 0:
        daily_sleep.plot(kind='line', marker='o', alpha=0.7)
        plt.title('Daily Sleep Duration (Excluding Awake Time)')
        plt.xlabel('Date')
        plt.ylabel('Sleep Duration (hours)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
    
    # Plot 2: Sleep type breakdown over time
    plt.subplot(2, 1, 2)
    sleep_type_daily = df.groupby(['date', 'sleep_type'])['duration_hours'].sum().unstack(fill_value=0)
    sleep_type_daily.plot(kind='area', stacked=True, alpha=0.7)
    plt.title('Daily Sleep Composition by Type')
    plt.xlabel('Date')
    plt.ylabel('Duration (hours)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print(f"\nSleep Summary:")
    print(f"Total sleep records: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    if len(daily_sleep) > 0:
        print(f"Average nightly sleep: {daily_sleep.mean():.1f} hours")
        print(f"Total sleep time: {daily_sleep.sum():.1f} hours")
    
    # Sleep type breakdown
    print(f"\nSleep Type Breakdown:")
    type_summary = df.groupby('sleep_type').agg({
        'duration_hours': ['count', 'sum', 'mean']
    }).round(2)
    for sleep_type in df['sleep_type'].unique():
        records = df[df['sleep_type'] == sleep_type]
        total_hours = records['duration_hours'].sum()
        avg_duration = records['duration_hours'].mean()
        count = len(records)
        print(f"  {sleep_type}: {count} records, {total_hours:.1f} total hours (avg {avg_duration:.1f}h per record)")
    
    # Source breakdown
    print(f"\nData Sources:")
    for source in df['source'].unique():
        count = len(df[df['source'] == source])
        print(f"  {source}: {count} records")
    
    print(f"\nRecent Sleep Records:")
    recent = df.sort_values('date', ascending=False).head(10)
    for _, record in recent.iterrows():
        print(f"\nDate: {record['date']} ({record['start_time']} - {record['end_time']})")
        print(f"Type: {record['sleep_type']}")
        print(f"Duration: {record['duration_hours']:.1f} hours")
        print(f"Source: {record['source']}")

def analyze_workouts():
    """
    Analyze and visualize Apple Workout data from export.xml.
    Exports workout data to CSV and shows time series plot of daily workout durations.
    """
    print("Analyzing workout data...")
    tree = ET.parse('../export.xml' if not os.path.exists('export.xml') else 'export.xml')
    root = tree.getroot()
    
    workouts = []
    
    # Process Workout elements
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
                duration_minutes = duration_value  # assume minutes
            
            # Extract calories and distance from WorkoutStatistics
            calories = 0
            distance_km = 0
            
            for stat in workout.findall('.//WorkoutStatistics'):
                stat_type = stat.get('type', '')
                sum_value = stat.get('sum')
                unit = stat.get('unit', '')
                
                if sum_value:
                    if 'ActiveEnergyBurned' in stat_type:
                        calories = float(sum_value)
                    elif 'DistanceWalkingRunning' in stat_type:
                        if unit == 'km':
                            distance_km = float(sum_value)
                        elif unit == 'm':
                            distance_km = float(sum_value) / 1000
            
            workouts.append({
                'date': start_date.date(),
                'start_time': start_date.time(),
                'activity_type': activity_type.replace('HKWorkoutActivityType', ''),
                'duration_minutes': round(duration_minutes, 1),
                'duration_hours': round(duration_minutes / 60, 2),
                'calories': round(calories, 1),
                'distance_km': round(distance_km, 2),
                'source': source_name
            })
                
        except (ValueError, TypeError) as e:
            continue
    
    if not workouts:
        print("No workout data found!")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'duration_hours', 'avg_heart_rate', 'measurements']).to_csv('workout_data.csv', index=False)
        print("Created empty workout_data.csv file.")
        return
        
    df = DataFrame(workouts)
    df = df.sort_values('date')
    
    # Export to CSV with more descriptive column names
    export_df = df.copy()
    export_df['date'] = export_df['date'].astype(str)  # Convert date to string for better CSV compatibility
    export_df.to_csv('workout_data.csv', index=False)
    print(f"\nWorkout data exported to 'workout_data.csv'")
    print(f"Exported {len(export_df)} workouts")
    
    # Display first few rows of exported data
    print("\nFirst few rows of exported data:")
    print(export_df.head())
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.scatter(df['date'], df['duration_hours'], alpha=0.6, c=df.index, cmap='viridis')
    plt.title('Workout Duration Over Time')
    plt.xlabel('Date')
    plt.ylabel('Duration (Hours)')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print("\nWorkout Summary:")
    print(f"Total workouts: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Average workout duration: {df['duration_minutes'].mean():.1f} minutes")
    print(f"Total workout time: {df['duration_hours'].sum():.1f} hours")
    print(f"Total calories burned: {df['calories'].sum():.0f} kcal")
    print(f"Total distance: {df['distance_km'].sum():.1f} km")
    
    # Activity type breakdown
    print(f"\nWorkout Types:")
    activity_counts = df['activity_type'].value_counts()
    for activity, count in activity_counts.head(10).items():
        avg_duration = df[df['activity_type'] == activity]['duration_minutes'].mean()
        print(f"  {activity}: {count} workouts (avg {avg_duration:.1f} min)")
    
    print(f"\nRecent Workouts:")
    recent = df.sort_values('date', ascending=False).head(5)
    for _, workout in recent.iterrows():
        print(f"\nDate: {workout['date']} at {workout['start_time']}")
        print(f"Activity: {workout['activity_type']}")
        print(f"Duration: {workout['duration_minutes']:.1f} minutes")
        if workout['calories'] > 0:
            print(f"Calories: {workout['calories']:.0f} kcal")
        if workout['distance_km'] > 0:
            print(f"Distance: {workout['distance_km']:.1f} km")

def analyze_with_chatgpt(csv_files):
    """
    Analyze health data using OpenAI's ChatGPT.
    
    Args:
        csv_files: List of CSV files to analyze
    """
    # Check if .env file exists and load API key
    if not os.path.exists('.env'):
        print("\nError: .env file not found!")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
        return
    
    # Load environment variables
    load_dotenv()
    
    # Check if API key is set
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\nError: OPENAI_API_KEY not found in .env file!")
        print("Please add your OpenAI API key to the .env file.")
        return
    
    # Set API key
    openai.api_key = api_key
    
    # Check if required data files exist and run analyses if needed
    missing_files = []
    for file_name, data_type in csv_files:
        if not os.path.exists(file_name):
            missing_files.append((file_name, data_type))
    
    if missing_files:
        print("\nSome required data files are missing. Running analyses to generate them...")
        print("Note: This will generate all required data files without displaying plots.")
        print("You can view the plots later by running options 1-6 individually.")
        
        # Temporarily disable plot display to avoid blocking
        original_show = plt.show
        plt.show = lambda: None  # Replace with no-op function
        
        try:
            # Map file names to their corresponding analysis functions
            analysis_functions = {
                'steps_data.csv': analyze_steps,
                'distance_data.csv': analyze_distance,
                'heart_rate_data.csv': analyze_heart_rate,
                'weight_data.csv': analyze_weight,
                'sleep_data.csv': analyze_sleep,
                'workout_data.csv': analyze_workouts
            }
            
            # Run the necessary analyses
            for file_name, data_type in missing_files:
                if file_name in analysis_functions:
                    print(f"\nGenerating {file_name} from {data_type} data...")
                    analysis_functions[file_name]()
                    # Verify the file was created
                    if os.path.exists(file_name):
                        print(f"✓ Successfully generated {file_name}")
                    else:
                        print(f"✗ Failed to generate {file_name}")
        finally:
            # Restore original plt.show function
            plt.show = original_show
    
    # Add data preparation code
    data_summary = {}
    files_found = False
    
    print("\nProcessing data files for ChatGPT analysis...")
    for file_name, data_type in csv_files:
        try:
            if os.path.exists(file_name):
                df = read_csv(file_name)
                
                # Skip empty dataframes
                if len(df) == 0:
                    print(f"Note: {file_name} exists but contains no data.")
                    continue
                
                print(f"Found {data_type} data in {file_name}")
                
                data_summary[data_type] = {
                    'total_records': len(df),
                    'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df and len(df) > 0 else 'N/A',
                    'average': f"{df['value'].mean():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'max_value': f"{df['value'].max():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'min_value': f"{df['value'].min():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'data_sample': df.head(50).to_string() if len(df) > 0 else 'No data available'
                }
                files_found = True
            else:
                print(f"Warning: {file_name} still not found after attempted generation.")
                
        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            continue

    if not files_found:
        print("\nNo data files with content could be processed! Please check your export.xml file.")
        print("It appears your Apple Health export doesn't contain the expected health metrics.")
        return

    # Build the prompt
    prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
    for data_type, summary in data_summary.items():
        prompt += f"\n{data_type} Data Summary:\n"
        prompt += f"- Total Records: {summary['total_records']}\n"
        prompt += f"- Date Range: {summary['date_range']}\n"
        prompt += f"- Average Value: {summary['average']}\n"
        prompt += f"- Maximum Value: {summary['max_value']}\n"
        prompt += f"- Minimum Value: {summary['min_value']}\n"
        prompt += f"\nSample Data:\n{summary['data_sample']}\n"
        prompt += "\n" + "="*50 + "\n"

    prompt += """Please provide a comprehensive analysis including:
    1. Notable patterns or trends in the data
    2. Unusual findings or correlations between different metrics
    3. Actionable health insights based on the data
    4. Areas that might need attention or improvement
    """

    try:
        # Send to OpenAI API using the new client syntax (v1.0.0+)
        print("\nSending data to ChatGPT for analysis...")
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        analysis_content = response.choices[0].message.content
        
        print("\nChatGPT Analysis:")
        print("=" * 50)
        print(analysis_content)
        
        # Ask if user wants to save the analysis
        save_option = input("\nWould you like to save this analysis as a markdown file? (y/n): ").strip().lower()
        if save_option == 'y' or save_option == 'yes':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_analysis_chatgpt_{timestamp}.md"
            
            # Create markdown content
            markdown_content = f"# Apple Health Data Analysis (ChatGPT)\n\n"
            markdown_content += f"*Analysis generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            markdown_content += f"## Data Summary\n\n"
            
            for data_type, summary in data_summary.items():
                markdown_content += f"### {data_type}\n\n"
                markdown_content += f"- **Total Records:** {summary['total_records']}\n"
                markdown_content += f"- **Date Range:** {summary['date_range']}\n"
                markdown_content += f"- **Average Value:** {summary['average']}\n"
                markdown_content += f"- **Maximum Value:** {summary['max_value']}\n"
                markdown_content += f"- **Minimum Value:** {summary['min_value']}\n\n"
            
            markdown_content += f"## Analysis Results\n\n"
            markdown_content += analysis_content
            
            # Save to file
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as f:
                f.write(markdown_content)
            
            print(f"\nAnalysis saved to {filepath}")
        
    except Exception as e:
        print(f"\nError during ChatGPT analysis: {str(e)}")
        print("This might be due to an invalid API key or network issues.")
        print("\nIf you're seeing an error about API versions, you have two options:")
        print("1. Run 'pip install openai==0.28' to downgrade to the older version")
        print("2. Or keep the current version and the updated code should work")

def analyze_with_ollama(csv_files):
    """
    Analyze health data using a local Ollama LLM.
    
    Args:
        csv_files: List of CSV files to analyze
    """
    try:
        # Check if required data files exist and run analyses if needed
        missing_files = []
        for file_name, data_type in csv_files:
            if not os.path.exists(file_name):
                missing_files.append((file_name, data_type))
        
        if missing_files:
            print("\nSome required data files are missing. Running analyses to generate them...")
            print("Note: This will generate all required data files without displaying plots.")
            print("You can view the plots later by running options 1-6 individually.")
            
            # Temporarily disable plot display to avoid blocking
            original_show = plt.show
            plt.show = lambda: None  # Replace with no-op function
            
            try:
                # Map file names to their corresponding analysis functions
                analysis_functions = {
                    'steps_data.csv': analyze_steps,
                    'distance_data.csv': analyze_distance,
                    'heart_rate_data.csv': analyze_heart_rate,
                    'weight_data.csv': analyze_weight,
                    'sleep_data.csv': analyze_sleep,
                    'workout_data.csv': analyze_workouts
                }
                
                # Run the necessary analyses
                for file_name, data_type in missing_files:
                    if file_name in analysis_functions:
                        print(f"\nGenerating {file_name} from {data_type} data...")
                        analysis_functions[file_name]()
                        # Verify the file was created
                        if os.path.exists(file_name):
                            print(f"✓ Successfully generated {file_name}")
                        else:
                            print(f"✗ Failed to generate {file_name}")
            finally:
                # Restore original plt.show function
                plt.show = original_show
        
        # Add data preparation code
        data_summary = {}
        files_found = False
        
        print("\nProcessing data files...")
        for file_name, data_type in csv_files:
            try:
                if os.path.exists(file_name):
                    df = read_csv(file_name)
                    
                    # Skip empty dataframes
                    if len(df) == 0:
                        print(f"Note: {file_name} exists but contains no data.")
                        continue
                    
                    print(f"Found {data_type} data in {file_name}")
                    
                    data_summary[data_type] = {
                        'total_records': len(df),
                        'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df and len(df) > 0 else 'N/A',
                        'average': f"{df['value'].mean():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'max_value': f"{df['value'].max():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'min_value': f"{df['value'].min():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'data_sample': df.head(50).to_string() if len(df) > 0 else 'No data available'
                    }
                    files_found = True
                else:
                    print(f"Warning: {file_name} still not found after attempted generation.")
                    
            except Exception as e:
                print(f"Error processing {file_name}: {str(e)}")
                continue

        if not files_found:
            print("\nNo data files with content could be processed! Please check your export.xml file.")
            print("It appears your Apple Health export doesn't contain the expected health metrics.")
            return

        # Build the prompt
        prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
        for data_type, summary in data_summary.items():
            prompt += f"\n{data_type} Data Summary:\n"
            prompt += f"- Total Records: {summary['total_records']}\n"
            prompt += f"- Date Range: {summary['date_range']}\n"
            prompt += f"- Average Value: {summary['average']}\n"
            prompt += f"- Maximum Value: {summary['max_value']}\n"
            prompt += f"- Minimum Value: {summary['min_value']}\n"
            prompt += f"\nSample Data:\n{summary['data_sample']}\n"
            prompt += "\n" + "="*50 + "\n"

        prompt += """Please provide a comprehensive analysis including:
        1. Notable patterns or trends in the data
        2. Unusual findings or correlations between different metrics
        3. Actionable health insights based on the data
        4. Areas that might need attention or improvement
        """

        # Rest of the Ollama API call
        print("\nSending data to Deepseek-R1 via Ollama...")
        response = ollama.chat(
            model='deepseek-r1',
            messages=[{
                "role": "system",
                "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."
            }, {
                "role": "user", 
                "content": prompt
            }],
            options={
                'temperature': 0.3,
                'num_ctx': 6144
            }
        )

        analysis_content = response['message']['content']
        
        print("\nDeepseek-R1 Analysis:")
        print("=" * 50)
        print(analysis_content)
        
        # Ask if user wants to save the analysis
        save_option = input("\nWould you like to save this analysis as a markdown file? (y/n): ").strip().lower()
        if save_option == 'y' or save_option == 'yes':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_analysis_ollama_{timestamp}.md"
            
            # Create markdown content
            markdown_content = f"# Apple Health Data Analysis (Ollama Deepseek-R1)\n\n"
            markdown_content += f"*Analysis generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            markdown_content += f"## Data Summary\n\n"
            
            for data_type, summary in data_summary.items():
                markdown_content += f"### {data_type}\n\n"
                markdown_content += f"- **Total Records:** {summary['total_records']}\n"
                markdown_content += f"- **Date Range:** {summary['date_range']}\n"
                markdown_content += f"- **Average Value:** {summary['average']}\n"
                markdown_content += f"- **Maximum Value:** {summary['max_value']}\n"
                markdown_content += f"- **Minimum Value:** {summary['min_value']}\n\n"
            
            markdown_content += f"## Analysis Results\n\n"
            markdown_content += analysis_content
            
            # Save to file
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as f:
                f.write(markdown_content)
            
            print(f"\nAnalysis saved to {filepath}")

    except Exception as e:
        print(f"Error during analysis: {str(e)}")

def main():
    """
    Main function providing an interactive menu to choose which health metric to analyze.
    """
    while True:
        print("\nWhat would you like to analyze?")
        print("1. Steps")
        print("2. Distance")
        print("3. Heart Rate")
        print("4. Weight")
        print("5. Sleep")
        print("6. Workouts")
        print("7. Analyze All Data with ChatGPT")
        print("8. Analyze with Local LLM (Ollama)")
        print("9. Advanced AI Settings")
        print("10. Exit")
        
        choice = input("Enter your choice (1-10): ")
        
        # List of available data files and their types
        data_files = [
            ('steps_data.csv', 'Steps'),
            ('distance_data.csv', 'Distance'),
            ('heart_rate_data.csv', 'Heart Rate'),
            ('weight_data.csv', 'Weight'),
            ('sleep_data.csv', 'Sleep'),
            ('workout_data.csv', 'Workout')
        ]
        
        if choice == '1':
            analyze_steps()
        elif choice == '2':
            analyze_distance()
        elif choice == '3':
            analyze_heart_rate()
        elif choice == '4':
            analyze_weight()
        elif choice == '5':
            analyze_sleep()
        elif choice == '6':
            analyze_workouts()
        elif choice == '7':
            analyze_with_chatgpt(data_files)
        elif choice == '8':
            analyze_with_ollama(data_files)
        elif choice == '9':
            print("\nAdvanced AI Settings:")
            print("Current default temperature: 0.3")
            print("\nTemperature Guide:")
            print("0.0-0.3: Best for statistical analysis and consistent insights")
            print("0.3-0.5: Balanced analysis with some variation")
            print("0.5-0.7: More creative insights and patterns")
            print("0.7-1.0: Most varied and exploratory analysis")
            print("\nRecommended: 0.3 for health data analysis")
            input("\nPress Enter to continue...")
        elif choice == '10':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import pandas
        import matplotlib
        import openai
        from dotenv import load_dotenv
        print("All required packages are installed!")
    except ImportError as e:
        print(f"Missing required package: {str(e)}")
        print("\nPlease install required packages using:")
        print("pip install -r ../requirements.txt")
        exit(1)

def check_env():
    """Check if .env file exists and contains API key"""
    if not os.path.exists('.env'):
        print("Warning: .env file not found!")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
        return False
    return True

if __name__ == "__main__":
    check_requirements()
    if not check_env():
        print("\nContinuing without AI analysis capabilities...")
    main()