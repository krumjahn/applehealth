#!/usr/bin/env python3
"""
Patch to add workout intensity analysis to applehealth.py
This shows the specific modifications needed to integrate heart rate zone analysis
"""

# ============================================================================
# ADD THESE IMPORTS AT THE TOP OF applehealth.py (around line 10)
# ============================================================================

# Add after existing imports:
"""
from workout_intensity_analyzer import (
    analyze_workout_intensity,
    export_enhanced_workout_data,
    generate_ai_prompt_with_intensity,
    calculate_heart_rate_zones
)
"""


# ============================================================================
# REPLACE analyze_workouts() FUNCTION (starting at line 1095)
# ============================================================================

def analyze_workouts_enhanced():
    """
    Enhanced version of analyze_workouts() that includes heart rate zone analysis.
    Replace the existing analyze_workouts() function with this version.
    """
    print("Analyzing workout data with intensity zones...")
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")

    # First, try the enhanced analysis with heart rate zones
    try:
        # Get user's age for HR zone calculation if available
        age = None
        max_hr = None

        # You could add prompts here or get from config
        # age = int(input("Enter your age for HR zone calculation (or press Enter to skip): ") or "0") or None

        # Run enhanced analysis
        enhanced_df, zones = analyze_workout_intensity(export_path, age, max_hr)

        if enhanced_df is not None and not enhanced_df.empty:
            # Successfully got enhanced data
            print(f"\n✅ Enhanced workout analysis complete with heart rate zones!")

            # Export the enhanced data
            csv_path = get_output_path('enhanced_workout_data.csv')
            enhanced_df['date'] = enhanced_df['date'].astype(str)
            enhanced_df['start_time'] = enhanced_df['start_time'].astype(str)
            enhanced_df['end_time'] = enhanced_df['end_time'].astype(str)
            enhanced_df.to_csv(csv_path, index=False)
            print(f"Enhanced workout data exported to {csv_path}")

            # Also export standard workout_data.csv for compatibility
            standard_columns = ['date', 'start_time', 'activity_type', 'duration_minutes',
                              'duration_hours', 'calories', 'distance_km', 'source']
            standard_df = enhanced_df[standard_columns].copy()
            standard_csv_path = get_output_path('workout_data.csv')
            standard_df.to_csv(standard_csv_path, index=False)
            print(f"Standard workout data exported to {standard_csv_path}")

            # Create visualization with intensity information
            plot_enhanced_workouts(enhanced_df, zones)

            # Print enhanced summary
            print_enhanced_workout_summary(enhanced_df, zones)

            return

    except Exception as e:
        print(f"Enhanced analysis not available: {e}")
        print("Falling back to standard workout analysis...")

    # If enhanced analysis fails, fall back to original implementation
    # [Original analyze_workouts() code continues here...]


def plot_enhanced_workouts(df, zones):
    """
    Create enhanced workout visualization showing intensity zones.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Workout duration over time (original)
    ax1.scatter(df['date'], df['duration_hours'], alpha=0.6, c=df.index, cmap='viridis')
    ax1.set_title('Workout Duration Over Time')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Duration (Hours)')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Workout intensity (new)
    if 'hr_avg' in df.columns and df['hr_avg'].notna().any():
        # Color by predominant zone
        colors = []
        for _, workout in df.iterrows():
            if pd.isna(workout.get('hr_avg', None)):
                colors.append('gray')
            else:
                # Find predominant zone
                max_zone = 'zone_1'
                max_percent = 0
                for zone in ['zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5']:
                    if f'{zone}_percent' in workout and workout[f'{zone}_percent'] > max_percent:
                        max_percent = workout[f'{zone}_percent']
                        max_zone = zone

                zone_colors = {
                    'zone_1': '#3498db',  # Blue (very light)
                    'zone_2': '#2ecc71',  # Green (light)
                    'zone_3': '#f39c12',  # Orange (moderate)
                    'zone_4': '#e74c3c',  # Red (hard)
                    'zone_5': '#9b59b6'   # Purple (maximum)
                }
                colors.append(zone_colors.get(max_zone, 'gray'))

        # Plot average heart rate colored by zone
        scatter = ax2.scatter(df['date'], df['hr_avg'], c=colors, alpha=0.7, s=50)
        ax2.set_title('Workout Intensity by Heart Rate Zone')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Average Heart Rate (BPM)')
        ax2.grid(True, alpha=0.3)

        # Add zone reference lines
        for zone_name, zone_info in zones.items():
            ax2.axhline(y=zone_info['min'], color='gray', linestyle='--', alpha=0.3)
            ax2.text(df['date'].min(), zone_info['min'],
                    f"{zone_name.replace('_', ' ').title()}",
                    fontsize=8, alpha=0.5)

        # Create legend
        legend_elements = [
            mpatches.Patch(color='#3498db', label='Zone 1 (Very Light)'),
            mpatches.Patch(color='#2ecc71', label='Zone 2 (Light)'),
            mpatches.Patch(color='#f39c12', label='Zone 3 (Moderate)'),
            mpatches.Patch(color='#e74c3c', label='Zone 4 (Hard)'),
            mpatches.Patch(color='#9b59b6', label='Zone 5 (Maximum)'),
            mpatches.Patch(color='gray', label='No HR Data')
        ]
        ax2.legend(handles=legend_elements, loc='upper right')

    plt.tight_layout()
    plot_path = get_output_path('enhanced_workout_plot.png')
    try:
        plt.savefig(plot_path)
        print(f"Enhanced workout plot saved to {plot_path}")
    except Exception:
        pass
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()


def print_enhanced_workout_summary(df, zones):
    """
    Print enhanced workout summary including intensity analysis.
    """
    print("\nEnhanced Workout Summary:")
    print("="*50)

    # Basic stats (original)
    print(f"Total workouts: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Total workout time: {df['duration_hours'].sum():.1f} hours")
    print(f"Average workout duration: {df['duration_minutes'].mean():.1f} minutes")

    # Enhanced stats (new)
    workouts_with_hr = df[df['hr_count'] > 0] if 'hr_count' in df.columns else pd.DataFrame()

    if len(workouts_with_hr) > 0:
        print(f"\nWorkouts with heart rate data: {len(workouts_with_hr)} ({len(workouts_with_hr)/len(df)*100:.1f}%)")
        print(f"Average heart rate: {workouts_with_hr['hr_avg'].mean():.1f} BPM")
        print(f"Average max heart rate: {workouts_with_hr['hr_max'].mean():.1f} BPM")

        print("\nTraining Zone Distribution (average % time):")
        for zone in ['zone_1', 'zone_2', 'zone_3', 'zone_4', 'zone_5']:
            col = f'{zone}_percent'
            if col in workouts_with_hr.columns:
                avg_percent = workouts_with_hr[col].mean()
                zone_info = zones[zone]
                print(f"  {zone.replace('_', ' ').title()} ({zone_info['name']}): {avg_percent:.1f}%")

        # High intensity analysis
        high_intensity_percent = (workouts_with_hr['zone_4_percent'].mean() +
                                workouts_with_hr['zone_5_percent'].mean())
        print(f"\nAverage time in high intensity (zones 4-5): {high_intensity_percent:.1f}%")

        # Activity-specific intensity
        print("\nIntensity by Activity Type:")
        activity_intensity = workouts_with_hr.groupby('activity_type').agg({
            'hr_avg': 'mean',
            'zone_4_percent': 'mean',
            'zone_5_percent': 'mean'
        }).round(1)

        for activity in activity_intensity.index[:5]:
            avg_hr = activity_intensity.loc[activity, 'hr_avg']
            high_int = (activity_intensity.loc[activity, 'zone_4_percent'] +
                       activity_intensity.loc[activity, 'zone_5_percent'])
            print(f"  {activity}: avg HR {avg_hr:.0f} BPM, {high_int:.1f}% high intensity")


# ============================================================================
# MODIFY _prepare_ai_data() FUNCTION (around line 1915)
# ============================================================================

def _prepare_ai_data_enhanced(csv_files):
    """
    Enhanced version of _prepare_ai_data() that includes workout intensity analysis.
    Add this code to the existing _prepare_ai_data() function after line 1988.
    """
    # [Original _prepare_ai_data() code up to building the prompt...]

    # After the prompt is built (around line 1988), add:

    # Try to enhance with workout intensity data
    try:
        export_path = resolve_export_xml()

        # Check if we have enhanced workout data
        enhanced_workout_path = get_output_path('enhanced_workout_data.csv')
        if os.path.exists(enhanced_workout_path):
            print("\nAdding workout intensity analysis to AI prompt...")

            # Load the enhanced workout data
            enhanced_df = pd.read_csv(enhanced_workout_path)

            # Recalculate zones (using default age/max_hr)
            zones, _ = calculate_heart_rate_zones()

            # Generate intensity-specific prompt
            intensity_prompt = generate_ai_prompt_with_intensity(enhanced_df, zones)

            # Add to main prompt
            prompt += "\n\n" + "="*50 + "\n\n" + intensity_prompt

            print("✅ AI prompt enhanced with workout intensity data!")
        else:
            print("\nNote: Run workout analysis first to include intensity data in AI analysis")

    except Exception as e:
        print(f"Could not add intensity analysis to prompt: {e}")

    return data_summary, prompt


# ============================================================================
# ADD NEW MENU OPTION (in the main menu around line 1830)
# ============================================================================

# Add this to the menu options:
"""
12. Analyze Workouts with Heart Rate Zones (Enhanced)
"""

# And in the menu handling code:
"""
elif choice == '12':
    analyze_workouts_enhanced()
"""


# ============================================================================
# SUMMARY OF CHANGES
# ============================================================================

print("""
INTEGRATION SUMMARY
==================

To integrate workout intensity analysis into applehealth.py:

1. Add imports from workout_intensity_analyzer at the top

2. Replace or enhance analyze_workouts() function to:
   - Try enhanced analysis first
   - Fall back to standard analysis if needed
   - Export both enhanced and standard CSV files

3. Modify _prepare_ai_data() to:
   - Check for enhanced workout data
   - Add intensity analysis to the AI prompt

4. Add visualization for workout intensity zones

5. Optionally add menu option for enhanced workout analysis

BENEFITS:
- AI can see actual workout intensity, not just duration
- Heart rate zones (1-5) calculated for each workout
- Identifies high-intensity training patterns
- Links heart rate data to specific workouts
- Provides training load distribution insights

This directly addresses the customer's complaint about AI underestimating
high-intensity workouts and missing BPM information!
""")