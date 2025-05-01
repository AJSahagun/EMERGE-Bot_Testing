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
REQUEST_INTERVAL = 2  # 2-second interval between requests
PROCESS_TIME = 30  # 30 seconds average per conversation flow


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


def run_load_test(dataset, duration_minutes=30, requests_per_minute=600):
    if dataset is None or len(dataset) == 0:
        print("No data available in the dataset.")
        return

    print(f"Starting load test: {requests_per_minute} requests per minute for {duration_minutes} minutes")

    total_requests = duration_minutes * requests_per_minute
    requests_per_second = requests_per_minute / 60

    full_dataset = pd.concat([dataset] * (total_requests // len(dataset) + 1))
    full_dataset = full_dataset.sample(n=total_requests, replace=False)
    incident_data_list = full_dataset.to_dict('records')

    successful_requests = 0
    failed_requests = 0
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    # Calculate required concurrency based on 30-second process time
    # For 600 RPM (10 per second) with 30-second processes, we need 300 concurrent workers
    # Formula: workers = rate_per_second * process_time
    max_workers = int(requests_per_second * PROCESS_TIME) + 50  # Add buffer
    batch_size = min(max_workers, 100)  # Limit batch size to prevent overwhelming system

    print(f"Using {max_workers} concurrent workers with batch size {batch_size}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        request_count = 0
        batch_start_time = time.time()

        while time.time() < end_time and (successful_requests + failed_requests) < total_requests:
            # Throttle submission rate to match target RPM
            current_time = time.time()
            elapsed_time = current_time - start_time
            target_requests = int(elapsed_time * requests_per_second)
            requests_to_send = target_requests - request_count

            if requests_to_send > 0:
                # Submit batch of requests
                batch = min(requests_to_send, batch_size, total_requests - request_count)
                futures = []

                for i in range(batch):
                    if request_count < total_requests:
                        incident_data = incident_data_list[request_count]
                        futures.append(executor.submit(complete_conversation_flow, incident_data))
                        request_count += 1

                # Process completed futures
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        successful_requests += 1
                    else:
                        failed_requests += 1

                # Throttle and progress reporting
                batch_elapsed = time.time() - batch_start_time
                current_minute = int(elapsed_time // 60)

                print(f"Minute {current_minute + 1}/{duration_minutes} - "
                      f"Successful: {successful_requests}, Failed: {failed_requests}, "
                      f"Submitted: {request_count}/{total_requests}")

                batch_start_time = time.time()

            # Prevent CPU over utilization while waiting for the right time to send the next batch
            time.sleep(0.1)

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
    parser.add_argument('--duration', type=int, default=30,
                        help='Duration of load test in minutes (default: 30)')
    parser.add_argument('--rpm', type=int, default=600,
                        help='Requests per minute for load testing (default: 600)')
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
        run_load_test(dataset, args.duration, args.rpm)


if __name__ == "__main__":
    main()
