#!/usr/bin/env python3
"""
Integration script to enhance existing Apple Health analysis with workout intensity data.
This shows how to use the workout_intensity_analyzer module with the existing applehealth.py
"""

import os
import sys
from datetime import datetime
import pandas as pd

# Add the src directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workout_intensity_analyzer import (
    analyze_workout_intensity,
    export_enhanced_workout_data,
    generate_ai_prompt_with_intensity
)

def enhance_ai_prompt_with_intensity(base_prompt, export_path, age=None, max_hr=None):
    """
    Enhance the existing AI prompt with workout intensity analysis.

    Args:
        base_prompt: The original prompt from _prepare_ai_data()
        export_path: Path to export.xml
        age: User's age for HR zone calculation
        max_hr: Known max heart rate (optional)

    Returns:
        Enhanced prompt with intensity data
    """
    print("\nEnhancing AI analysis with workout intensity data...")

    try:
        # Analyze workout intensity
        enhanced_df, zones = analyze_workout_intensity(export_path, age, max_hr)

        if enhanced_df is None or enhanced_df.empty:
            print("No enhanced workout data available")
            return base_prompt

        # Generate intensity-specific prompt section
        intensity_prompt = generate_ai_prompt_with_intensity(enhanced_df, zones)

        # Combine prompts
        enhanced_prompt = base_prompt + "\n\n" + "="*50 + "\n\n" + intensity_prompt

        # Export enhanced workout data
        output_dir = os.path.dirname(export_path) or '.'
        csv_path = export_enhanced_workout_data(enhanced_df, output_dir)

        print(f"\nEnhanced workout data saved to: {csv_path}")

        return enhanced_prompt

    except Exception as e:
        print(f"Error enhancing workout analysis: {e}")
        return base_prompt


def demonstrate_intensity_analysis():
    """
    Demonstrate how the intensity analysis improves the AI prompt.
    """
    print("Workout Intensity Analysis Enhancement Demo")
    print("="*50)

    # Example original prompt (simplified)
    original_prompt = """Analyze this Apple Health data and provide detailed insights:

Workout Data Summary:
- Total Records: 145
- Date Range: from 2023-01-01 to 2024-01-01
- Average Value: 45.2
- Maximum Value: 120.0
- Minimum Value: 15.0

Sample Data:
date       activity_type    duration_minutes  calories
2023-12-01 Running         35.5              320
2023-12-02 Cycling         60.0              450
...

Please provide a comprehensive analysis including:
1. Notable patterns or trends in the data
2. Unusual findings or correlations between different metrics
3. Actionable health insights based on the data
4. Areas that might need attention or improvement"""

    # Show what gets added with intensity analysis
    intensity_addition = """
Enhanced Workout Analysis with Heart Rate Zones:

Total Workouts: 145
Workouts with HR data: 132
Date Range: 2023-01-01 to 2024-01-01

Heart Rate Statistics:
- Average HR across workouts: 142.3 bpm
- Highest max HR: 185 bpm
- Average max HR: 168.5 bpm

Training Zone Distribution (% of workout time):
- Zone 1 (Very Light, 95-114 bpm): 8.2%
- Zone 2 (Light, 114-133 bpm): 15.3%
- Zone 3 (Moderate, 133-152 bpm): 22.1%
- Zone 4 (Hard, 152-171 bpm): 38.7%
- Zone 5 (Maximum, 171-190 bpm): 15.7%

Workout Types with Average Intensity:
- Running: 52 workouts, avg 42.3 min, avg HR 156 bpm, 65.2% high intensity
- Cycling: 38 workouts, avg 65.5 min, avg HR 138 bpm, 42.1% high intensity
- Strength Training: 25 workouts, avg 35.2 min, avg HR 125 bpm, 18.3% high intensity

Recent High-Intensity Workouts (>50% time in zones 4-5):
- 2023-12-28: Running, 45.2 min, avg HR 165, max HR 182, 72.3% high intensity
- 2023-12-26: HIIT, 30.5 min, avg HR 158, max HR 178, 68.5% high intensity
- 2023-12-23: Cycling, 90.0 min, avg HR 145, max HR 172, 55.2% high intensity

Please analyze this enhanced workout data, focusing on:
1. Training intensity patterns and zone distribution
2. Whether the user is training too hard, too easy, or balanced
3. Specific insights about high-intensity training (zones 4-5)
4. Recommendations for optimizing training intensity
5. Any concerning patterns in heart rate data"""

    print("\nORIGINAL AI PROMPT (LIMITED INFO):")
    print("-"*40)
    print(original_prompt[:400] + "...")

    print("\n\nENHANCED PROMPT ADDITIONS (WITH INTENSITY DATA):")
    print("-"*40)
    print(intensity_addition)

    print("\n\nKEY IMPROVEMENTS:")
    print("-"*40)
    print("1. ✅ Heart rate zones calculated for each workout")
    print("2. ✅ Time spent in each training zone (1-5)")
    print("3. ✅ Average and max heart rates per workout")
    print("4. ✅ High-intensity workout identification")
    print("5. ✅ Activity-specific intensity patterns")
    print("6. ✅ Training load distribution analysis")

    print("\n\nWHAT THIS FIXES:")
    print("-"*40)
    print("❌ OLD: AI only sees daily average heart rate")
    print("✅ NEW: AI sees workout-specific heart rate and zones")
    print()
    print("❌ OLD: No visibility into training intensity")
    print("✅ NEW: Clear breakdown of time in each zone")
    print()
    print("❌ OLD: Can't identify high-intensity training patterns")
    print("✅ NEW: Specific metrics for zones 4-5 training")


def suggest_implementation_changes():
    """
    Suggest specific changes to integrate this into applehealth.py
    """
    print("\n\nIMPLEMENTATION SUGGESTIONS:")
    print("="*50)

    print("\n1. Modify analyze_workouts() in applehealth.py:")
    print("-"*40)
    print("""
# In analyze_workouts() function, after line 1176:
df = DataFrame(workouts)

# Add this:
# Try to enhance with intensity data
try:
    from workout_intensity_analyzer import analyze_workout_intensity
    enhanced_df, zones = analyze_workout_intensity(export_path)
    if enhanced_df is not None:
        df = enhanced_df  # Use enhanced data
        print("Enhanced workout data with heart rate zones")
except Exception as e:
    print(f"Standard workout analysis (no HR zones): {e}")
""")

    print("\n2. Modify _prepare_ai_data() in applehealth.py:")
    print("-"*40)
    print("""
# In _prepare_ai_data() function, before returning the prompt:

# Add intensity enhancement
try:
    from integrate_intensity_analysis import enhance_ai_prompt_with_intensity
    export_path = resolve_export_xml()
    prompt = enhance_ai_prompt_with_intensity(prompt, export_path)
except Exception as e:
    print(f"Using standard prompt (no intensity data): {e}")
""")

    print("\n3. Add user configuration options:")
    print("-"*40)
    print("""
# Add to the menu or as command line arguments:
- User's age (for HR zone calculation)
- Known max heart rate (optional)
- Whether to include intensity analysis
""")


if __name__ == "__main__":
    # Run the demonstration
    demonstrate_intensity_analysis()
    suggest_implementation_changes()

    print("\n\nNOTE: This is a demonstration script.")
    print("To actually use the intensity analyzer:")
    print(f"python workout_intensity_analyzer.py /path/to/export.xml [age] [max_hr]")