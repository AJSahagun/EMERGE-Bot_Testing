# EMERGE Objective 2 Testing

A tool for load testing EMERGE chatbot for objective 2 by simulating concurrent user conversations with peak load capabilities.

## Overview

This tool allows you to:

1. Run single conversation tests to verify functionality
2. Perform **peak load tests** with configurable ramp-up periods
3. Simulate thousands of users with realistic conversation patterns
4. Generate detailed performance metrics with real-time monitoring
5. Automatically handle rate limiting with retry logic

## Requirements

- Python 3.8+
- Required packages:
  - requests
  - pandas
  - python-dotenv
  - concurrent.futures

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
python main.py --mode single --file EMERGE_SyntheticData-sample-data_botRequest.csv
```

### Running a Peak Load Test
To run a 20-minute test with 15-minute ramp-up to 600 RPM and 5-minute peak:
```bash
python main.py --mode load --file EMERGE_SyntheticData-sample-data_botRequest.csv \
  --ramp-up 15 \
  --peak-duration 5 \
  --peak-rpm 600
```

### Command Line Options
| Option | Description | Default |
|--------|-------------|---------|
| `--mode` | Test mode (`single` or `load`) | `single` |
| `--file` | Path to CSV dataset | `dataset.csv` |
| `--ramp-up` | Ramp-up duration in minutes | 15 |
| `--peak-duration` | Peak duration in minutes | 5 |
| `--peak-rpm` | Target peak requests per minute | 600 |
| `--process-time` | Avg conversation time (seconds) | 30 |
| `--machine-id` | Machine ID for distributed testing | 0 |
| `--total-machines` | Total machines in distributed setup | 1 |

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

**Note:** The tool automatically handles small datasets by repeating entries as needed.

## Key Features

- **Peak Load Testing**: Simulate gradual ramp-up followed by sustained peak traffic
- **Smart Retry Logic**: Automatic retries with exponential backoff for failed requests
- **Real-time Monitoring**: Live RPM tracking and progress updates every 5 seconds
- **Distributed Testing**: Support for multi-machine load generation
- **Conversation Realism**: 
  - 11 API calls per conversation
  - Natural request spacing (2s between messages)
  - Full conversation lifecycle simulation

## Performance Considerations

- **Hidden Requests**: Each conversation generates 11 API calls (1 user + 1 conversation + 9 messages)
- **Rate Limit Calculation**: 
  ```python
  Safe RPM = (100 RPS * 60) / 11 ≈ 545 RPM
  ```
- **Resource Guidelines**:
  - 600 RPM requires ~5 machines (depending on specs)
  - 8GB RAM/node recommended for high load tests
  - Network bandwidth: ~1MB/s per 1000 RPM


### Dataset Limitations
- The tool automatically handles datasets smaller than required test size
- Minimum recommended dataset: 50 unique records
