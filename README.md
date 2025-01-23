<<<<<<< HEAD
# Apple Health Data Analyzer

A Python tool that transforms Apple Health export data into insightful visualizations and analytics. Easily track your fitness journey with detailed analysis of steps, workouts, heart rate, sleep, and more. Features specialized support for WHOOP workout data.

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Features

- 📊 Interactive data visualizations for all metrics
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
- xml.etree.ElementTree (included in Python standard library)

## 🛠️ Installation

1. Clone this repository:
```bash
git clone https://github.com/krumjahn/applehealth.git
cd applehealth
```

2. Install required packages:
```bash
pip install -r requirements.txt
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
7. Exit

## 📊 Example Output

```
Workout Summary:
Total days with workouts: 145
Average daily workout time: 1.25 hours
Total time recorded: 181.5 hours
Average heart rate: 132.7 BPM
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

This tool processes your health data locally on your machine. No data is sent to external servers or stored anywhere else.

## ⚠️ Limitations

- Currently only supports Apple Health export XML format
- WHOOP integration limited to workout data
- Sleep analysis assumes data is in standard Apple Health format

## 🔜 Roadmap

- [ ] Add support for more data types
- [ ] Enhanced visualization options
- [ ] Statistical analysis features
- [ ] Export capabilities
- [ ] Configuration options

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apple Health for providing comprehensive health data export
- WHOOP for workout tracking capabilities
- Contributors and users of this tool

## 📧 Contact

- Create an issue for bug reports or feature requests
- Pull requests are welcome

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=krumjahn/applehealth&type=Date)](https://star-history.com/#krumjahn/applehealth&Date)

---

If you find this tool useful, please consider giving it a star ⭐️
=======
# Apple Health Data Analyzer

A Python tool that transforms Apple Health export data into insightful visualizations and analytics. Easily track your fitness journey with detailed analysis of steps, workouts, heart rate, sleep, and more. Features specialized support for WHOOP workout data.

# Examples of charts you can generate

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

![workouts](https://github.com/user-attachments/assets/358638fe-776b-407d-922e-7538058e89d8)
![heartrate](https://github.com/user-attachments/assets/f3bf7837-d657-4ef3-844b-18b434353947)
![Figure_1](https://github.com/user-attachments/assets/64364c2d-081f-42d2-8209-48cab57db659)
![distance](https://github.com/user-attachments/assets/b21d08d0-e518-4343-9a4f-030c96624b62)


## 🚀 Features

- 📊 Interactive data visualizations for all metrics
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
- xml.etree.ElementTree (included in Python standard library)

## 🛠️ Installation

1. Clone this repository:
```bash
git clone https://github.com/krumjahn/applehealth.git
cd apple-health-analyzer
```

2. Install required packages:
```bash
pip install -r requirements.txt
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
7. Exit

## 📊 Example Output

```
Workout Summary:
Total days with workouts: 145
Average daily workout time: 1.25 hours
Total time recorded: 181.5 hours
Average heart rate: 132.7 BPM
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

This tool processes your health data locally on your machine. No data is sent to external servers or stored anywhere else.

## ⚠️ Limitations

- Currently only supports Apple Health export XML format
- WHOOP integration limited to workout data
- Sleep analysis assumes data is in standard Apple Health format

## 🔜 Roadmap

- [ ] Add support for more data types
- [ ] Enhanced visualization options
- [ ] Statistical analysis features
- [ ] Export capabilities
- [ ] Configuration options

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Apple Health for providing comprehensive health data export
- WHOOP for workout tracking capabilities
- Contributors and users of this tool

## 📧 Contact

- Create an issue for bug reports or feature requests
- Pull requests are welcome

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=krumjahn/applehealth&type=Date)](https://star-history.com/#krumjahn/applehealth&Date)

---

If you find this tool useful, please consider giving it a star ⭐️
>>>>>>> ef4e9e43dec7509dff97e99221bae2e3249a114d
