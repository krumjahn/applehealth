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
import pandas as pd
import matplotlib.pyplot as plt
import openai
import os
from dotenv import load_dotenv
import sys

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
    return pd.DataFrame({'date': dates, 'value': values})

def analyze_steps():
    """
    Analyze and visualize daily step count data.
    Shows a time series plot of daily total steps and exports data to CSV.
    """
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierStepCount')
    
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
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierDistanceWalkingRunning')
    
    # Daily sum of distance (in kilometers)
    daily_distance = df.groupby(df['date'].dt.date)['value'].sum() / 1000
    
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
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierHeartRate')
    
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
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierBodyMass')
    
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
    df = parse_health_data('export.xml', 'HKCategoryTypeIdentifierSleepAnalysis')
    
    # Convert to hours
    df['value'] = df['value'] / 3600  # assuming the value is in seconds
    
    # Daily total sleep
    daily_sleep = df.groupby(df['date'].dt.date)['value'].sum()
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_sleep.plot()
    plt.title('Daily Sleep Duration')
    plt.xlabel('Date')
    plt.ylabel('Sleep Duration (hours)')
    plt.grid(True)
    plt.show()

def analyze_workouts():
    """
    Analyze and visualize WHOOP workout data from heart rate measurements.
    Exports workout data to CSV and shows time series plot of daily workout durations.
    """
    print("Analyzing workout data...")
    tree = ET.parse('export.xml')
    root = tree.getroot()
    
    daily_workouts = {}
    
    # Process records
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
                
            except (ValueError, TypeError) as e:
                continue
    
    if not daily_workouts:
        print("No workout data found!")
        return
        
    # Convert to DataFrame with explicit data
    workout_days = []
    for day, data in daily_workouts.items():
        estimated_minutes = data['measurement_count'] * (6/60)
        avg_hr = sum(data['heart_rates']) / len(data['heart_rates']) if data['heart_rates'] else 0
        
        workout_days.append({
            'date': day,
            'duration_hours': estimated_minutes / 60,  # Convert to hours
            'avg_heart_rate': round(avg_hr, 1),
            'measurements': data['measurement_count']
        })
    
    df = pd.DataFrame(workout_days)
    df = df.sort_values('date')
    
    # Export to CSV with more descriptive column names
    export_df = df.copy()
    export_df['date'] = export_df['date'].astype(str)  # Convert date to string for better CSV compatibility
    export_df.to_csv('workout_data.csv', index=False)
    print("\nWorkout data exported to 'workout_data.csv'")
    print(f"Exported {len(export_df)} days of workout data")
    
    # Display first few rows of exported data
    print("\nFirst few rows of exported data:")
    print(export_df.head())
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.scatter(df['date'], df['duration_hours'], alpha=0.5)
    plt.plot(df['date'], df['duration_hours'], alpha=0.3)
    plt.title('Daily Workout Duration')
    plt.xlabel('Date')
    plt.ylabel('Hours')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print("\nWorkout Summary:")
    print(f"Total days with workouts: {len(df)}")
    print(f"Average daily workout time: {df['duration_hours'].mean():.2f} hours")
    print(f"Total time recorded: {df['duration_hours'].sum():.2f} hours")
    
    if df['avg_heart_rate'].mean() > 0:
        print(f"Average heart rate: {df['avg_heart_rate'].mean():.1f} BPM")
    
    print("\nRecent Days:")
    recent = df.sort_values('date', ascending=False).head(5)
    for _, day in recent.iterrows():
        print(f"\nDate: {day['date']}")
        print(f"Duration: {day['duration_hours']:.2f} hours")
        if day['avg_heart_rate'] > 0:
            print(f"Average Heart Rate: {day['avg_heart_rate']:.1f} BPM")
        print(f"Measurements: {day['measurements']}")

def analyze_with_chatgpt(csv_files, temperature=None):
    """
    Analyze health data using ChatGPT API.
    Uses GPT-4 Turbo for enhanced analysis capabilities.
    
    Args:
        csv_files: List of CSV files to analyze
        temperature: Optional float between 0 and 1 for AI response variation
                    - 0.0: Most focused, consistent analysis
                    - 0.3: Default, balanced analysis
                    - 0.7: More creative insights
                    - 1.0: Most varied analysis
    """
    try:
        # Get temperature setting from user if not provided
        if temperature is None:
            print("\nAI Analysis Temperature Setting:")
            print("Lower = more focused, consistent analysis")
            print("Higher = more creative, varied insights")
            print("Recommended settings:")
            print("  0.3 = Default, balanced analysis (recommended for health data)")
            print("  0.1 = Most focused, statistical analysis")
            print("  0.7 = More creative insights")
            print("  1.0 = Most varied analysis")
            
            temp_input = input("\nEnter temperature (0.0-1.0) or press Enter for default (0.3): ").strip()
            
            if temp_input == "":
                temperature = 0.3
            else:
                try:
                    temperature = float(temp_input)
                    if not 0 <= temperature <= 1:
                        print("Invalid temperature. Using default (0.3)")
                        temperature = 0.3
                except ValueError:
                    print("Invalid input. Using default temperature (0.3)")
                    temperature = 0.3
        
        print(f"\nUsing temperature: {temperature}")
        
        # Load API key from .env file
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: No OpenAI API key found in .env file")
            return
            
        client = openai.OpenAI(api_key=api_key)
        
        # Prepare data for analysis
        data_summary = {}
        files_found = False
        
        print("\nProcessing data files...")
        for file_name, data_type in csv_files:
            try:
                df = pd.read_csv(file_name)
                print(f"Found {data_type} data in {file_name}")
                
                # Calculate meaningful statistics
                data_summary[data_type] = {
                    'total_records': len(df),
                    'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df else 'N/A',
                    'average': f"{df['value'].mean():.2f}" if 'value' in df else 'N/A',
                    'max_value': f"{df['value'].max():.2f}" if 'value' in df else 'N/A',
                    'min_value': f"{df['value'].min():.2f}" if 'value' in df else 'N/A',
                    'data_sample': df.head(50).to_string()  # Include first 50 rows
                }
                files_found = True
                
            except FileNotFoundError:
                print(f"Warning: {file_name} not found, skipping...")
                continue
            except Exception as e:
                print(f"Error processing {file_name}: {str(e)}")
                continue
        
        if not files_found:
            print("\nNo data files found! Please run some analyses first to generate CSV files.")
            return
        
        print("\nSending data to GPT-4 Turbo for analysis...")
        
        # Prepare the prompt with comprehensive data
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
        
        prompt += """
        Please provide a comprehensive analysis including:
        1. Notable patterns or trends in the data
        2. Unusual findings or correlations between different metrics
        3. Actionable health insights based on the data
        4. Areas that might need attention or improvement
        5. Comparison to general health guidelines where applicable
        6. Statistical significance of any findings
        7. Recommendations for improvement
        """
        
        # Make API call with GPT-4 Turbo
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert health data analyst specializing in Apple Health data analysis. \
                               Provide detailed, actionable insights based on the data. Use statistical analysis \
                               where appropriate and focus on identifying meaningful patterns and trends."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=4096
        )
        
        # Print analysis with temperature info
        print(f"\nGPT-4 Turbo Analysis (Temperature: {temperature}):")
        print("=" * 50)
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        print("If this is an API error, check your OpenAI API key in the .env file")

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
        print("8. Advanced AI Settings")
        print("9. Exit")
        
        choice = input("Enter your choice (1-9): ")
        
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
            print("\nAdvanced AI Settings:")
            print("Current default temperature: 0.3")
            print("\nTemperature Guide:")
            print("0.0-0.3: Best for statistical analysis and consistent insights")
            print("0.3-0.5: Balanced analysis with some variation")
            print("0.5-0.7: More creative insights and patterns")
            print("0.7-1.0: Most varied and exploratory analysis")
            print("\nRecommended: 0.3 for health data analysis")
            input("\nPress Enter to continue...")
        elif choice == '9':
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