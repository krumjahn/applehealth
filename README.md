# Apple Health Data Analyzer

A Python tool that transforms Apple Health export data into insightful visualizations and analytics, with AI-powered analysis. Easily track your fitness journey with detailed analysis of steps, workouts, heart rate, sleep, and more. Features specialized support for WHOOP workout data and ChatGPT integration for personalized insights.

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Features

- 📊 Interactive data visualizations for all metrics
- 🤖 AI-powered analysis using ChatGPT
- 💪 Workout duration tracking and analysis
- ❤️ Heart rate patterns and trends
- 🏃‍♂️ Daily activity metrics (steps, distance)
- ⚖️ Weight tracking over time
- 😴 Sleep pattern analysis
- 🔄 WHOOP workout integration

## 📋 Requirements

- Python 3.6+
- pandas
- matplotlib
- openai
- python-dotenv
- xml.etree.ElementTree (included in Python standard library)

## 🛠️ Installation

1. Clone this repository:
```
git clone https://github.com/krumjahn/applehealth.git
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Set up OpenAI API key:
   - Get your API key from [OpenAI Platform](https://platform.openai.com/)
   - Create a `.env` file in the project directory
   - Add your API key:
     ```
     OPENAI_API_KEY=your-api-key-here
     ```

## 📱 Getting Your Health Data

1. On your iPhone:
   - Open the Health app
   - Tap your profile picture
   - Select "Export All Health Data"
   - Save and extract the zip file
   - Locate `export.xml`

2. Place `export.xml` in the same directory as the script

## 💻 Usage

Run the script:

```bash
python applehealth.py
```

Choose from the menu:
1. Steps Analysis
2. Distance Tracking
3. Heart Rate Analysis
4. Weight Tracking
5. Sleep Analysis
6. Workout Analysis
7. **Analyze All Data with ChatGPT** (New!)
8. Exit

### 🤖 AI Analysis

The new AI analysis feature (Option 7) will:
- Analyze all your exported health data
- Provide personalized insights using ChatGPT
- Identify patterns and trends
- Suggest potential improvements
- Highlight unusual findings

Note: You must run at least one other analysis option first to generate the data files for AI analysis.

## 📊 Example Output

```
Workout Summary:
Total days with workouts: 145
Average daily workout time: 1.25 hours
Total time recorded: 181.5 hours
Average heart rate: 132.7 BPM

AI Analysis:
[ChatGPT provides personalized insights based on your data]
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add new feature'`)
5. Push to the branch (`git push origin feature/improvement`)
6. Create a Pull Request

## 📝 Data Privacy

This tool processes your health data locally on your machine. When using the AI analysis feature:
- Only aggregated statistics are sent to OpenAI
- No personal identifiers are shared
- Data is processed according to OpenAI's privacy policy

## ⚠️ Limitations

- Currently only supports Apple Health export XML format
- WHOOP integration limited to workout data
- Sleep analysis assumes data is in standard Apple Health format
- AI analysis requires OpenAI API key and internet connection

## 🔜 Roadmap

- [ ] Add support for more data types
- [ ] Enhanced visualization options
- [ ] More detailed AI analysis
- [ ] Export capabilities
- [ ] Configuration options

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apple Health for providing comprehensive health data export
- WHOOP for workout tracking capabilities
- OpenAI for ChatGPT API
- Contributors and users of this tool

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=krumjahn/applehealth&type=Date)](https://star-history.com/#krumjahn/applehealth&Date)

---

If you find this tool useful, please consider giving it a star ⭐️
