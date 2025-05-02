import requests
import pandas as pd
import random
import time
import concurrent.futures
import argparse
import os
from dotenv import find_dotenv, load_dotenv
from datetime import datetime, timezone

# Set-up env var
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Constants
WEBHOOK_URL_KEY = os.getenv("WEBHOOK_URL_KEY")
BASE_URL = f"https://chat.botpress.cloud/{WEBHOOK_URL_KEY}"
REQUEST_INTERVAL = 2  # seconds interval between requests
PROCESS_TIME = 30  # seconds average per conversation flow
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
HIDDEN_MULTIPLIER = 11


def load_dataset(file_path):
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None


def create_user(name):
    url = f"{BASE_URL}/users"
    payload = {"name": name}
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating user: {e}")
        return None


def create_conversation(user_key):
    url = f"{BASE_URL}/conversations"
    payload = {
        "type": "text",
        "text": "hi",
    }
    headers = {
        "accept": "application/json",
        "x-user-key": user_key,
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating conversation: {e}")
        return None


def send_message(user_key, conversation_id, message):
    url = f"{BASE_URL}/messages"
    payload = {
        "payload": {
            "type": "text",
            "text": message
        },
        "conversationId": conversation_id
    }
    headers = {
        "accept": "application/json",
        "x-user-key": user_key,
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        return None


def list_messages(user_key, conversation_id):
    url = f"{BASE_URL}/conversations/{conversation_id}/messages"

    headers = {
        "accept": "application/json",
        "x-user-key": user_key,
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error listing messages: {e}")
        return None


def complete_conversation_flow(incident_data, show_history=False):
    try:
        # Step 1: Create user
        user_name = f"User_{random.randint(1000, 9999)}"
        user_response = create_user(user_name)
        if not user_response:
            return False

        user_key = user_response.get("key")

        # Step 2: Create conversation
        conv_response = create_conversation(user_key)
        if not conv_response:
            return False

        conversation_id = conv_response.get("conversation", {}).get("id")

        # Helper function to send message with interval
        def send_with_interval(message):
            send_message(user_key, conversation_id, message)
            time.sleep(REQUEST_INTERVAL)

        send_with_interval("Hi")  # Initialize conversation
        send_with_interval("Tagalog")  # Choose language
        send_with_interval(  # Personal info
            f"{incident_data['name']}, {incident_data['phoneNumber']}, {incident_data['dateAndTime']}"
        )
        send_with_interval(incident_data['incidentType'])  # Incident type
        send_with_interval(incident_data['incidentSubType'])  # Subtype
        send_with_interval(incident_data['reportDescription'])  # Description
        send_with_interval(incident_data['address'])  # Address
        send_with_interval(incident_data['landmark'])  # Landmark
        send_with_interval("Tama")  # Confirmation

        if show_history:
            print(list_messages(user_key, conversation_id))

        return True
    except Exception as e:
        print(f"Error in conversation flow: {e}")
        return False


def run_single_test(dataset):
    if dataset is None or len(dataset) == 0:
        print("No data available in the dataset.")
        return

    random_incident = dataset.sample(1).iloc[0].to_dict()
    print("Starting single test with data:")
    print(random_incident)

    start_time = time.time()
    success = complete_conversation_flow(random_incident, show_history=False)
    elapsed_time = time.time() - start_time

    if success:
        print(f"Test completed successfully in {elapsed_time:.2f} seconds.")
    else:
        print("Test failed.")


def execute_with_retry(fn, *args):
    for attempt in range(MAX_RETRIES):
        result = fn(*args)
        if result is not None:
            return True
        time.sleep(INITIAL_BACKOFF * (2 ** attempt))
    return False


def run_load_test(dataset, ramp_duration_minutes=15, peak_duration_minutes=5, peak_rpm=600):
    if dataset is None or len(dataset) == 0:
        print("No data available in the dataset.")
        return

    total_duration_minutes = ramp_duration_minutes + peak_duration_minutes
    print(f"Starting peak load test: {ramp_duration_minutes} minutes ramp-up to {peak_rpm} RPM, "
          f"followed by {peak_duration_minutes} minutes peak")

    # Calculate total requests
    ramp_duration_seconds = ramp_duration_minutes * 60
    total_requests_ramp = int((peak_rpm * ramp_duration_seconds) / 120)  # Integral of linear ramp-up
    total_requests_peak = peak_rpm * peak_duration_minutes
    total_requests = total_requests_ramp + total_requests_peak

    # Prepare dataset
    full_dataset = pd.concat([dataset] * (total_requests // len(dataset) + 1))
    full_dataset = full_dataset.sample(n=total_requests, replace=True)
    incident_data_list = full_dataset.to_dict('records')

    successful_requests = 0
    failed_requests = 0
    start_time = time.time()
    end_time = start_time + (total_duration_minutes * 60)

    # Calculate max workers based on peak RPM
    peak_rps = peak_rpm / 60
    max_workers = int(peak_rps * PROCESS_TIME) + 50  # Buffer
    batch_size = min(max_workers, 100)

    print(f"Using {max_workers} concurrent workers with batch size {batch_size}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        request_count = 0
        last_report_time = time.time()

        while time.time() < end_time and request_count < total_requests:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # Calculate target requests based on elapsed time
            if elapsed_time <= ramp_duration_seconds:
                # Ramp-up phase
                current_rpm = (peak_rpm / ramp_duration_seconds) * elapsed_time
                target_requests = int((peak_rpm * elapsed_time ** 2) / (2 * ramp_duration_seconds * 60))
            else:
                # Peak phase
                current_rpm = peak_rpm
                peak_elapsed = min(elapsed_time - ramp_duration_seconds, peak_duration_minutes * 60)
                target_requests = total_requests_ramp + int(peak_rpm * peak_elapsed / 60)

            requests_to_send = max(0, target_requests - request_count)

            if requests_to_send > 0:
                # Submit batch of requests
                batch = min(requests_to_send, batch_size, total_requests - request_count)
                futures = []

                for _ in range(batch):
                    incident_data = incident_data_list[request_count]
                    futures.append(executor.submit(execute_with_retry, complete_conversation_flow, incident_data))
                    request_count += 1

                # Process completed futures
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        successful_requests += 1
                    else:
                        failed_requests += 1

            # Progress reporting every 5 seconds
            if current_time - last_report_time >= 5:
                current_minute = int(elapsed_time // 60)
                print(f"[{current_minute:02d}:{int(elapsed_time % 60):02d}] "
                      f"RPM: {current_rpm:.0f} | "
                      f"Sent: {request_count}/{total_requests} | "
                      f"Success: {successful_requests} | "
                      f"Failed: {failed_requests}")
                last_report_time = current_time

            time.sleep(0.1)  # Prevent CPU overuse

    total_time = time.time() - start_time
    print("\nLoad test completed")
    print(f"Start time: {datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat()}")
    print(f"End time: {datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat()}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Successful requests: {successful_requests} ({successful_requests / total_requests:.1%})")
    print(f"Failed requests: {failed_requests} ({failed_requests / total_requests:.1%})")
    print(f"Effective RPM: {successful_requests / (total_time / 60):.1f}")


def main():
    parser = argparse.ArgumentParser(description='Chatbot Load Testing Tool')
    parser.add_argument('--mode', choices=['single', 'load'], default='single',
                        help='Test mode: single for one test, load for load testing')
    parser.add_argument('--file', default='EMERGE_SyntheticData-sample-data_botRequest-Trimmed.csv',
                        help='Path to the CSV dataset file')
    parser.add_argument('--ramp-up', type=int, default=15,
                        help='Ramp-up duration in minutes (default: 15)')
    parser.add_argument('--peak-duration', type=int, default=5,
                        help='Peak duration in minutes (default: 5)')
    parser.add_argument('--peak-rpm', type=int, default=600,
                        help='Peak requests per minute (default: 600)')
    parser.add_argument('--process-time', type=int, default=30,
                        help='Average process time per conversation in seconds (default: 30)')

    args = parser.parse_args()

    # Update process time if specified
    global PROCESS_TIME
    PROCESS_TIME = args.process_time

    dataset = load_dataset(args.file)
    if dataset is None:
        return

    if args.mode == 'single':
        run_single_test(dataset)
    else:
        run_load_test(
            dataset,
            ramp_duration_minutes=args.ramp_up,
            peak_duration_minutes=args.peak_duration,
            peak_rpm=args.peak_rpm
        )


if __name__ == "__main__":
    main()
