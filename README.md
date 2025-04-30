# EMERGE Objective 2 Testing

A tool for load testing EMERGE chatbot for objective 2 by simulating concurrent user conversations.

## Overview

This tool allows you to:

1. Run single conversation tests to verify functionality
2. Perform load tests with configurable concurrency to test system capacity
3. Simulate hundreds of users interacting with your chatbot simultaneously
4. Generate detailed performance metrics

## Requirements

- Python 3.8+
- Required packages:
  - requests
  - pandas
  - python-dotenv

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/AJSahagun/EMERGE-Bot_Testing.git
   cd EMERGE-Bot_Testing
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your Botpress webhook URL key:
   ```
   WEBHOOK_URL_KEY=your-webhook-url-key
   ```

## Usage

### Running a Single Test

To run a single test conversation with random data from your dataset:

```bash
python main.py --mode single --file your_dataset.csv
```

### Running a Load Test

To run a load test with 600 requests per minute for 1 hour:

```bash
python main.py --mode load --file your_dataset.csv --rpm 600 --duration 60
```

### Command Line Options

- `--mode`: Test mode (`single` or `load`)
- `--file`: Path to your CSV dataset
- `--duration`: Duration of load test in minutes (default: 60)
- `--rpm`: Requests per minute for load testing (default: 600)
- `--process-time`: Average time (in seconds) for one complete conversation flow (default: 30)

## Input Dataset Format

The tool expects a CSV file with the following columns:
- `name`: User's name
- `phoneNumber`: User's phone number
- `dateAndTime`: Date and time of incident
- `incidentType`: Type of incident
- `incidentSubType`: Sub-type of incident
- `reportDescription`: Description of the incident
- `address`: Address of the incident
- `landmark`: Nearby landmark

Example:
```
name,phoneNumber,dateAndTime,incidentType,incidentSubType,reportDescription,address,landmark
Juan Dela Cruz,09123456789,2023-01-01 10:00,Fire,House Fire,Small fire in kitchen,123 Main St,Near City Hall
```

## Key Features

- **Configurable Concurrency**: Automatically calculates the optimal number of threads based on process time and target RPM
- **Detailed Metrics**: Provides success rate, failure rate, and effective RPM at the end of testing
- **Progress Monitoring**: Shows real-time progress during load testing
- **Realistic Conversation Flow**: Simulates complete user conversations including language selection and data input

## Performance Considerations

- For 600 RPM with 30-second conversation flows, approximately 300 concurrent workers are needed
- Adjust the `--process-time` parameter if your average conversation duration changes
- Monitor system resources during testing as high concurrency can be resource-intensive

## Troubleshooting

If you encounter rate limiting or connection errors:
- Reduce the RPM target
- Increase the REQUEST_INTERVAL constant in the code
- Ensure your system has sufficient resources for the desired concurrency