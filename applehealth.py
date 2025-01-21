import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

def parse_health_data(file_path, record_type):
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

# Example analysis
def analyze_steps():
    # Make sure export.xml is in the same folder as this script
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierStepCount')
    
    # Daily sum of steps
    daily_steps = df.groupby(df['date'].dt.date)['value'].sum()
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_steps.plot()
    plt.title('Daily Steps')
    plt.xlabel('Date')
    plt.ylabel('Steps')
    plt.grid(True)
    plt.show()

def analyze_distance():
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierDistanceWalkingRunning')
    
    # Daily sum of distance (in kilometers)
    daily_distance = df.groupby(df['date'].dt.date)['value'].sum() / 1000  # Convert meters to kilometers
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_distance.plot()
    plt.title('Daily Walking/Running Distance')
    plt.xlabel('Date')
    plt.ylabel('Distance (km)')
    plt.grid(True)
    plt.show()

def analyze_heart_rate():
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierHeartRate')
    
    # Daily average heart rate
    daily_hr = df.groupby(df['date'].dt.date)['value'].mean()
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_hr.plot()
    plt.title('Daily Average Heart Rate')
    plt.xlabel('Date')
    plt.ylabel('Heart Rate (BPM)')
    plt.grid(True)
    plt.show()

def analyze_weight():
    df = parse_health_data('export.xml', 'HKQuantityTypeIdentifierBodyMass')
    
    # Daily weight (taking the last measurement of each day)
    daily_weight = df.groupby(df['date'].dt.date)['value'].last()
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_weight.plot()
    plt.title('Body Weight Over Time')
    plt.xlabel('Date')
    plt.ylabel('Weight (kg)')
    plt.grid(True)
    plt.show()

def analyze_sleep():
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
    print("Analyzing workout data...")
    tree = ET.parse('export.xml')
    root = tree.getroot()
    
    # Dictionary to store daily workout durations
    daily_workouts = {}
    
    for record in root.findall('.//Record'):
        if record.get('sourceName') == 'WHOOP':
            try:
                date = datetime.strptime(record.get('startDate'), '%Y-%m-%d %H:%M:%S %z')
                day = date.date()  # Get just the date part
                heart_rate = float(record.get('value'))
                
                # Initialize the day if we haven't seen it before
                if day not in daily_workouts:
                    daily_workouts[day] = {
                        'total_minutes': 0,
                        'heart_rates': [],
                        'measurement_count': 0
                    }
                
                # Add heart rate measurement
                daily_workouts[day]['heart_rates'].append(heart_rate)
                daily_workouts[day]['measurement_count'] += 1
                
            except (ValueError, TypeError) as e:
                continue
    
    # Convert to DataFrame
    workout_days = []
    for day, data in daily_workouts.items():
        # Estimate workout time (assuming measurements are roughly every 6 seconds)
        estimated_minutes = data['measurement_count'] * (6/60)  # Convert to minutes
        
        # Calculate average heart rate only if we have measurements
        if data['heart_rates']:
            avg_hr = sum(data['heart_rates']) / len(data['heart_rates'])
        else:
            avg_hr = 0
        
        workout_days.append({
            'date': day,
            'duration_min': estimated_minutes,
            'avg_heart_rate': avg_hr,
            'measurements': data['measurement_count']
        })
    
    if not workout_days:
        print("No workout data found!")
        return
        
    df = pd.DataFrame(workout_days)
    df = df.sort_values('date')
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.scatter(df['date'], df['duration_min']/60, alpha=0.5)  # Convert to hours
    plt.plot(df['date'], df['duration_min']/60, alpha=0.3)     # Convert to hours
    plt.title('Daily Workout Duration')
    plt.xlabel('Date')
    plt.ylabel('Hours')
    plt.grid(True)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    plt.show()
    
    # Print summary statistics
    print("\nWorkout Summary:")
    print(f"Total days with workouts: {len(df)}")
    print(f"Average daily workout time: {df['duration_min'].mean()/60:.2f} hours")
    print(f"Total time recorded: {df['duration_min'].sum()/60:.2f} hours")
    
    # Only print heart rate stats if we have valid heart rate data
    if df['avg_heart_rate'].mean() > 0:
        print(f"Average heart rate: {df['avg_heart_rate'].mean():.1f} BPM")
    
    # Print some individual day details for verification
    print("\nRecent Days:")
    recent = df.sort_values('date', ascending=False).head(5)
    for _, day in recent.iterrows():
        print(f"\nDate: {day['date']}")
        print(f"Duration: {day['duration_min']/60:.2f} hours")
        if day['avg_heart_rate'] > 0:
            print(f"Average Heart Rate: {day['avg_heart_rate']:.1f} BPM")
        print(f"Measurements: {day['measurements']}")

if __name__ == "__main__":
    while True:
        print("\nWhat would you like to analyze?")
        print("1. Steps")
        print("2. Distance")
        print("3. Heart Rate")
        print("4. Weight")
        print("5. Sleep")
        print("6. Workouts")
        print("7. Exit")
        
        choice = input("Enter your choice (1-7): ")
        
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
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")