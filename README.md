# Apple Health A.I. Data Analyzer 🍎🤖

**Privacy-First Health Intelligence: Turn your Apple Health exports into actionable insights with DeepSeek-R1, ChatGPT, and local LLMs.**

[![GitHub stars](https://img.shields.io/github/stars/krumjahn/applehealth.svg?style=social)](https://github.com/krumjahn/applehealth/stargazers)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![DeepSeek-R1 Supported](https://img.shields.io/badge/DeepSeek--R1-Local%20AI-blueviolet)](https://ollama.com/library/deepseek-r1)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-ff6b35.svg)](https://clawhub.ai/krumjahn/apple-health-export-analyzer)

---

### 🚀 **Tired of the CLI?**
**Get the Pro Version:** For instant, interactive analysis and one-click exports without touching a terminal, visit **[applehealthdata.com](https://applehealthdata.com)**.

---

## 🧐 What is this?
This is an open-source technical toolkit for solopreneurs, researchers, and biohackers who want to **own their health data**. 

It transforms the complex Apple Health `export.xml` into clean **CSV/JSON** datasets and provides a direct bridge to **AI reasoning engines**. Whether you want to use ChatGPT or run **100% private local analysis with DeepSeek-R1**, this tool handles the heavy lifting of data parsing and visualization.

## ✨ Key Features
- 💍 **Smart Ring Integration**: Unified analysis for **Oura**, **Whoop**, and **Samsung Ring** via Apple Health sync.
- 🧠 **DeepSeek-R1 & Local AI**: Run 100% private health audits using Ollama (no data leaves your machine).
- 📊 **Automated Visualizations**: Instantly generate charts for heart rate cycles, sleep patterns, and workout intensity.
- 📤 **High-Fidelity Export**: XML → CSV/JSON conversion that preserves all metadata (Record, Workout, ActivitySummary).
- 🔄 **WHOOP Integration**: Specialized support for augmenting Apple Health data with WHOOP metrics.
- 🧪 **Multi-Model Support**: Native support for ChatGPT, Claude, Gemini, Grok, and LM Studio.

## 🛠️ "Steal My System": From 8 Years of Data to Actionable Training
I used this exact tool to analyze 8 years of my own fitness history. Here’s the system:
1. **The Pattern**: I discovered that my most active days (40k+ steps) almost never coincided with gym sessions—they were work-related.
2. **The Optimization**: I used the AI Analyzer to identify "Heart Rate Cycles" (3-4 week recovery dips) to automate my deload weeks.
3. **The Result**: A training plan that finally matches my biology instead of a generic app's schedule.
[Read the full case study here](https://rumjahn.com/how-i-used-a-i-to-analyze-8-years-of-apple-health-fitness-data-to-uncover-actionable-insights/).

## ⚡ Quick Start (The "Builder" Way)

```bash
# 1) Clone the repo
git clone https://github.com/krumjahn/applehealth.git && cd applehealth

# 2) Run the auto-bootstrapper (it handles venv and dependencies)
./run
```

**For Private AI Analysis (DeepSeek-R1):**
1. Install [Ollama](https://ollama.ai).
2. Run `ollama pull deepseek-r1`.
3. Launch this tool and select **Option 8 (Local LLM)**.

## 🦞 OpenClaw Support

This repo now has a published OpenClaw skill:

**[Install from ClawHub: Apple Health Export Analyzer](https://clawhub.ai/krumjahn/apple-health-export-analyzer)**

Use it if you want OpenClaw to:
- verify your Apple Health export setup
- generate a daily health brief from `export.xml`
- compare your steps and sleep over the last 7 days
- create a weekly summary with workouts and heart rate context
- help you set up a recurring daily health message

Example prompts:

```text
Use the Apple Health Export Analyzer skill. Verify my setup and give me my latest daily health brief with 3 suggestions.

Use the Apple Health Export Analyzer skill. Compare my steps and sleep over the last 7 days.

Use the Apple Health Export Analyzer skill. Generate a weekly summary from my Apple Health export.
```

## 🤖 Instructions for AI Agents
*If you are an AI Agent (Claude Code, Windsurf, OpenClaw) helping a user analyze health data:*
1. Clone this repo into the user's workspace.
2. Direct the user to place their `export.xml` in the root.
3. Call `python src/applehealth.py --export ./export.xml --out ./analysis` to generate the CSV datasets.
4. Read the resulting `.csv` files to provide personalized medical/fitness coaching.

### 🦞 Local OpenClaw Workflow

```text
skills/apple-health-export-analyzer
```

The skill includes concrete scripts for:
- verifying the local repo and `export.xml` setup
- generating a daily Apple Health brief
- comparing recent step and sleep trends
- generating a weekly summary

Example:

```bash
python skills/apple-health-export-analyzer/scripts/check_setup.py --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
python skills/apple-health-export-analyzer/scripts/daily_brief.py --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
```

## 📋 Requirements & Tech Stack
- **Language**: Python 3.6+
- **Data**: Pandas, XML.ElementTree
- **Viz**: Matplotlib
- **AI**: OpenAI, Anthropic, Google, and Ollama APIs

## 🐳 Docker (The "No-Setup" Way)
If you have Docker installed, you can run the analyzer without installing Python or dependencies locally:

```bash
# 1) Build the image
docker build -t applehealth .

# 2) Run the container (mount your export.xml and an output folder)
docker run -it \
  -v "/path/to/your/export.xml:/export.xml" \
  -v "$(pwd)/out:/out" \
  applehealth
```

## 🌟 Visuals & Charts
![xml-csv-logo](assets/xml-csv-logo.png)
![workouts](https://github.com/user-attachments/assets/6c373d3e-e038-4428-a8be-7c86c973a662)
![heartrate](https://github.com/user-attachments/assets/7f739661-f822-49e7-b79c-209c5164ecdc)
![lm-ollama-support](assets/lm-ollama-support.png)

## 🤝 Contributing & Community
Join our community of builders! If you improve the parser or add a new visualization, please submit a PR.

**[Join my community](https://nas.io/rumjahn)** for updates, experiments, and AI-builder workflows.

---
If you find this tool useful, **please give it a star ⭐️** to help others find it!

[![Star History Chart](https://api.star-history.com/svg?repos=krumjahn/applehealth&type=Date)](https://star-history.com/#krumjahn/applehealth&Date)
