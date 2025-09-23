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

## 📺 Youtube tutorial

[Watch youtube tutorial here](https://www.youtube.com/watch?v=fkvOE9Gxwzk)

## ⚡ Quick Start

Local (recommended for interactive charts)

```bash
# 1) Clone and enter the repo
git clone https://github.com/krumjahn/applehealth.git
cd applehealth

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app (you'll be prompted for export.xml; outputs go to ./health_out)
python src/applehealth.py

# Optional: Advanced flags if you already know the paths
# python src/applehealth.py --export "/absolute/path/to/export.xml" --out "./health_out"
```

Docker (saves charts/CSVs to your host folder)

```bash
# 1) Build the image
docker build -t applehealth .

# 2) Run the container (quote paths with spaces)
docker run -it \
  -v "/absolute/path/to/export.xml":/export.xml \
  -v "$(pwd)":/out \
  applehealth
```

Windows (PowerShell) example

```powershell
git clone https://github.com/krumjahn/applehealth.git
cd applehealth
pip install -r requirements.txt
python src/applehealth.py --export "C:\Users\you\Downloads\export.xml" --out ".\health_out"

# Docker
docker build -t applehealth .
docker run -it `
  -v "C:\Users\you\Downloads\export.xml:/export.xml" `
  -v "${PWD}:/out" `
  applehealth
```

### Makefile shortcuts (macOS/Linux)

For convenience, you can use the included Makefile:

```bash
# Build the Docker image
make docker-build

# Run via Docker (set EXPORT to your export.xml, OUT is where files will be written)
make docker-run EXPORT="/absolute/path/to/export.xml" OUT="$(pwd)"

# Run locally with interactive charts
make run-local EXPORT="/absolute/path/to/export.xml" OUT="./health_out"

# Start a shell in the container (for debugging)
make docker-run-bash EXPORT="/absolute/path/to/export.xml" OUT="$(pwd)"
```

Note: On Windows, Makefile targets require a Make tool (e.g., Git Bash + make or WSL). Otherwise use the plain docker/python commands above.

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
- openai, anthropic, google-generativeai
- python-dotenv
- xml.etree.ElementTree (included in Python standard library)

## 🛠️ Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/krumjahn/applehealth.git
   cd applehealth
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up OpenAI API key and optional Ollama configuration (optional, only needed for AI analysis):
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

You can run the tool locally (recommended for interactive charts) or via Docker (saves charts as PNGs).

Local (interactive charts):

```bash
# From the repository root (simplest):
python src/applehealth.py

# or change into src/ then run
cd src
python applehealth.py

# Optional: if you already know the paths, you can specify them
# python src/applehealth.py --export "/path/to/export.xml" --out "./health_out"
```

Notes:
- If you omit `--export`, the app will prompt you for the path (you can drag-and-drop the file or folder).
- By default, outputs are saved to `./health_out`.
- `--out` lets you choose a different output folder.

## 🐳 Docker Usage

Docker runs in a headless environment: charts do not pop up, but are saved as PNGs. Outputs are written to `/out` inside the container by default.

1) Build the image:

```bash
docker build -t applehealth .
```

2) Run the container, mounting your `export.xml` and an output directory from your host:

```bash
# macOS/Linux (paths with spaces must be quoted)
docker run -it \
  -v "/absolute/path/to/export.xml":/export.xml \
  -v "$(pwd)":/out \
  applehealth
```

Examples:
- If your export is in Downloads with a space in the name:
  `-v "/Users/you/Downloads/apple_health_export 2/export.xml":/export.xml`
- Write outputs to a custom folder on host:
  `-v "/Users/you/Desktop/health_out":/out`

Windows (PowerShell):

```powershell
docker run -it `
  -v "C:\Users\you\Downloads\export.xml:/export.xml" `
  -v "${PWD}:/out" `
  applehealth
```

Notes:
- No need for `--network host` in typical use. The app only needs outbound internet if you use AI features (ChatGPT/remote Ollama). The default Docker networking is fine.
- Inside Docker, the app auto-detects `/export.xml` and saves outputs to `/out`.
- You can still pass flags if you prefer: `--export /export.xml --out /out`.

Choose from the menu:

1. Analyze Steps
2. Analyze Distance
3. Analyze Heart Rate
4. Analyze Weight
5. Analyze Sleep
6. Analyze Workouts
7. AI: Analyze All Data (OpenAI)
8. AI: Analyze with Claude (Anthropic)
9. AI: Analyze with Gemini (Google)
10. AI: Analyze with Grok (xAI)
11. AI: Analyze with OpenRouter
12. AI: Analyze with Ollama (Local)
13. AI: Analyze with Ollama (Remote)
14. AI Settings
15. Reset Preferences
16. Exit

### 🤖 AI Analysis

The new AI analysis feature (Option 7) will:

- Analyze all your exported health data
- Provide personalized insights using ChatGPT
- Identify patterns and trends
- Suggest potential improvements
- Highlight unusual findings

Notes:
- If you haven’t run any analysis yet, the AI options will trigger the necessary data exports automatically.
- API keys can be provided via `.env` or pasted when prompted in the terminal:
  - ChatGPT (OpenAI): `OPENAI_API_KEY`
  - Claude (Anthropic): `ANTHROPIC_API_KEY`
  - Gemini (Google): `GEMINI_API_KEY`
  - Grok (xAI): `GROK_API_KEY`
  - OpenRouter: `OPENROUTER_API_KEY`
  If not present, the app will ask you to paste your key at runtime.

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

## 📦 Outputs

The tool writes the following per-metric outputs in the chosen output directory:
- CSVs: `steps_data.csv`, `distance_data.csv`, `heart_rate_data.csv`, `weight_data.csv`, `sleep_data.csv`, `workout_data.csv`
- Plots: `steps_plot.png`, `distance_plot.png`, `heart_rate_plot.png`, `weight_plot.png`, `sleep_plot.png`, `workout_plot.png`
- AI analyses (optional): timestamped `.md` files summarizing insights

On macOS/Linux, the app prints a one-line tip to open each saved plot (e.g., `open "./steps_plot.png"`).

AI model preferences
- The tool remembers your last-selected models for each AI provider (OpenAI, Claude, Gemini, Grok, OpenRouter).
- Preferences are stored in `~/.applehealth/ai_prefs.json` by default (override with `APPLEHEALTH_PREFS`).
- The app also remembers your last-used export.xml path and output directory in the same `ai_prefs.json`.

## 🆘 Troubleshooting

- "export.xml not found" error:
  - Use `--export "/absolute/path/to/export.xml"` or provide the directory containing it.
  - In Docker, mount the file: `-v "/absolute/path/to/export.xml":/export.xml`.
  - Paths with spaces must be quoted. On Windows, use double backslashes or quotes.
  - The app will prompt for the path if not provided; look for "Using export file: ...".

- No charts appear in Docker:
  - Expected. Docker runs headless; charts are saved as PNGs in `/out`.
  - Open the saved file on your host (the app prints `open "...png"`).
  - To see interactive charts, run locally (outside Docker).

- No CSV/PNG files found:
  - Make sure you ran one of the analysis options (1–6). AI options will generate them if needed.
  - Check the configured output directory (default: current dir locally, `/out` in Docker).
  - Use `--out "/path/to/output"` to control where files are written.

- OpenAI API key errors:
  - Create `.env` with `OPENAI_API_KEY=...` in your working directory.
  - In Docker, pass envs via `--env-file .env` or `-e OPENAI_API_KEY=...`.
  - Network access is required for ChatGPT; verify your connection.

- Ollama errors (local or external):
  - Local: install Ollama, run `ollama serve`, and `ollama pull deepseek-r1`.
  - External: set `OLLAMA_HOST=http://host:11434` or enter the URL when prompted.
  - If external fails, the tool can fall back to local Ollama.

- Paths with spaces or Windows paths:
  - Quote paths: `"/Users/you/Downloads/apple_health_export 2/export.xml"`.
  - Windows examples are shown for Docker (PowerShell). Use quotes for `--export` and `--out` as well.

- "Is a directory" error for export.xml:
  - This happens when Docker mounts a directory to a path expected to be a file.
  - Use the provided commands that bind the file to `/export.xml`, or pass `--export` pointing to a valid file.

- Step CSV filename confusion:
  - The tool exports both `steps_data.csv` and a compatibility `stepsdata.csv`.

- Useful env vars:
  - `EXPORT_XML` (path to export.xml), `OUTPUT_DIR` (output folder), `OLLAMA_HOST`.

## 📷 Quick Walkthrough (no images)

First run (local), selecting Steps (1):

```
What would you like to analyze?
1. Steps
2. Distance
3. Heart Rate
4. Weight
5. Sleep
6. Workouts
7. Analyze All Data with ChatGPT
8. Analyze with Local LLM (Ollama)
9. Analyze with External LLM (Ollama)
10. Advanced AI Settings
11. Exit
12. Analyze with Claude (Anthropic)
13. Analyze with Gemini (Google)
14. Analyze with Grok (xAI)
15. Analyze with OpenRouter
16. Reset Preferences
Enter your choice (1-11): 1
Using export file: /absolute/path/to/export.xml
Starting to parse HKQuantityTypeIdentifierStepCount...
XML file loaded, searching records...
Found 240292 records
Steps data exported to /.../health_out/steps_data.csv and compatibility file at /.../health_out/stepsdata.csv

Steps Summary:
- Date range: 2016-01-01 to 2025-01-01 (3650 days)
- Total steps: 12,345,678
- Average per day: 3,383 (median 2,950)
- Best day: 2018-03-24 with 46,996 steps
- Days ≥10k steps: 532
- Last 7-day average: 8,421
- CSV: /.../health_out/steps_data.csv
- CSV (compat): /.../health_out/stepsdata.csv
- Plot: /.../health_out/steps_plot.png
Tip: open "/.../health_out/steps_plot.png"
```

You can add your own GIFs or screenshots by placing them under `assets/` and linking to them in this README.

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

[![Star History Chart](https://api.star-history.com/svg?repos=krumjahn/applehealth&type=Date)](https://star-history.com/#krumjahn/applehealth&Date)

---

If you find this tool useful, please consider giving it a star ⭐️


