# Apple Health A.I. Data Analyzer

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
- 🧠 **Local LLM Support** - Analyze data privately using Ollama models like Deepseek-R1
- 🌐 **External LLM Support** (New!) - Connect to remote Ollama instances for analysis

## Example A.I. analysis

[Read more here](https://rumjahn.com/how-i-used-a-i-to-analyze-8-years-of-apple-health-fitness-data-to-uncover-actionable-insights/)

Here are the most surprising insights from your health data:

```
Marathon-Level Days: You've had several "super active" days exceeding 40,000 steps, with your record being 46,996 steps on March 24, 2018 - equivalent to walking about 23 miles! Interestingly, these extremely active days often don't coincide with recorded workouts.

Reversed Weekend Pattern: Unlike most people who are more active on weekends, your data shows consistently lower step counts on weekends, suggesting your physical activity is more tied to workdays than leisure time.

Workout Evolution: Your exercise patterns have notably changed over the years - you've shifted from frequent, shorter workouts to less frequent but more intense sessions. Recent workouts show higher average heart rates despite being less frequent.

Seasonal Anomalies: While there's a general trend of higher activity in spring/summer, some of your most active periods occurred during winter months, particularly in December and January of recent years.

Heart Rate Cycles: Your data shows interesting 3-4 week cycles where resting heart rate gradually increases then drops, possibly indicating training load and recovery patterns.

COVID Impact: There's a clear signature of the pandemic in your data, with more erratic step patterns and changed workout routines during 2020-2021, followed by a distinct recovery pattern in late 2021.

Morning Consistency: Your most successful workout periods consistently occur in morning hours, with these sessions showing better heart rate performance compared to other times.
```

## Examples of charts

![workouts](https://github.com/user-attachments/assets/6c373d3e-e038-4428-a8be-7c86c973a662)
![Figure_1](https://github.com/user-attachments/assets/fd25d50b-d303-46fe-aac3-0bba9c3295b7)
![distance](https://github.com/user-attachments/assets/72009a90-3687-4008-a208-a0f1702d3843)
![heartrate](https://github.com/user-attachments/assets/7f739661-f822-49e7-b79c-209c5164ecdc)

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

3. Set up OpenAI API key and optional Ollama configuration:
   - Get your OpenAI API key from [OpenAI Platform](https://platform.openai.com/)
   - Copy `.env.example` to `.env` in the project directory
   - Add your OpenAI API key and optional configuration:

     ```
     OPENAI_API_KEY=your-api-key-here
     OLLAMA_HOST=http://your-ollama-server:11434
     ```

   Note: If OLLAMA_HOST is not set, it will default to http://localhost:11434

4. **Set up Ollama for local AI analysis**:
   - Install Ollama: <https://ollama.ai/download>
   - Start Ollama service (keep running in background):

     ```bash
     ollama serve
     ```

   - Download Deepseek-R1 model:

     ```bash
     ollama pull deepseek-r1
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

## 🐳 Docker Usage

1. Build the Docker image:

   ```bash
   docker build -t applehealth .
   ```

2. Run the Docker container:

   ```bash
   docker run --network="host" -v $(pwd)/export.xml:/app/export.xml -it applehealth
   ```

Choose from the menu:

1. Steps Analysis
2. Distance Tracking
3. Heart Rate Analysis
4. Weight Tracking
5. Sleep Analysis
6. Workout Analysis
7. Analyze All Data with ChatGPT
8. Analyze with Local LLM (Ollama)
9. Analyze with External LLM (Ollama)
10. Advanced AI Settings
11. Exit

### 🤖 AI Analysis

The new AI analysis feature (Option 7) will:

- Analyze all your exported health data
- Provide personalized insights using ChatGPT
- Identify patterns and trends
- Suggest potential improvements
- Highlight unusual findings

Note: You must run at least one other analysis option first to generate the data files for AI analysis.

### 🖥️ Local LLM Analysis

The local analysis feature (Option 8) will:

- Process data entirely on your machine
- Use Ollama with Deepseek-R1 by default
- Provide technical analysis of health patterns
- No data leaves your computer

### 🌐 External LLM Analysis

The external LLM analysis feature (Option 9) will:

- Connect to a remote Ollama instance
- Default to a preconfigured remote server
- Allow customization of the server URL
- Automatically detect available models
- Fall back to local Ollama if remote connection fails

**To use different models**:

1. For local analysis, edit `applehealth.py` and find the `analyze_with_ollama()` function
2. Change the model name in this line:

   ```python
   model='deepseek-r1'  # Change to 'llama2', 'mistral', etc.
   ```

3. Pull your desired model first:

   ```bash
   ollama pull <model-name>
   ```
   
4. For external analysis, when prompted, enter the URL of your remote Ollama server

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
- Local LLM analysis requires minimum 8GB RAM for decent performance
- Model quality depends on local hardware capabilities
- External LLM connectivity depends on network and server availability

## 🔜 Roadmap

- [ ] Add support for more data types
- [ ] Enhanced visualization options
- [ ] More detailed AI analysis
- [ ] Export capabilities
- [ ] Configuration options
- [ ] Add model selection UI
- [ ] Support multiple local LLM providers
- [x] Support external Ollama LLM instances
- [ ] Add authentication for secure remote LLM connections

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apple Health for providing comprehensive health data export
- WHOOP for workout tracking capabilities
- OpenAI for ChatGPT API
- Ollama team for local and distributed LLM capabilities
- Contributors and users of this tool

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=nicolasluckie/applehealth&type=Date)](https://star-history.com/#nicolasluckie/applehealth&Date)

---

If you find this tool useful, please consider giving it a star ⭐️
