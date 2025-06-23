import requests
import json
import uuid
import os
import time

# --- Configuration ---
# The base URL of your deployed FastAPI application
BASE_URL = os.environ.get("API_BASE_URL", "https://gemini-adk-demo-d-1033076280634.europe-west1.run.app")

# In a real application, this would come from your authentication system
USER_EMAIL = "default_user@example.com"
USER_NAME = "Default User"

HEADERS = {
    "Content-Type": "application/json",
    "X-User-Email": USER_EMAIL,
    "X-User-Name": USER_NAME,
}

def create_session(session_id: str):
    """Creates a new session for the agent."""
    print(f"\n--- Creating session: {session_id} ---")
    endpoint = f"{BASE_URL}/apps/gemini_adk_demo/users/{USER_EMAIL}/sessions/{session_id}"
    try:
        response = requests.post(endpoint, headers=HEADERS, json={"state": {}})
        response.raise_for_status()
        print("✅ Session created successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"--- ❌ ERROR creating session ---")
        print(f"An error occurred: {e}")
        if e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return False

def run_agent(prompt: str):
    """
    Sends a prompt to the main agent endpoint and prints the non-streaming response.
    """
    session_id = f"test-session-{uuid.uuid4()}"
    if not create_session(session_id):
        return None

    print(f"\n{'='*20}\n🚀 Running agent with prompt: '{prompt}'\n{'='*20}")

    # Add a unique request ID to prevent caching issues on the server
    headers = HEADERS.copy()
    headers["X-Request-ID"] = str(uuid.uuid4())

    payload = {
        "app_name": "gemini_adk_demo",
        "user_id": USER_EMAIL,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": prompt}]
        },
        "streaming": False,
    }

    endpoint = f"{BASE_URL}/run_sse"

    try:
        with requests.post(endpoint, headers=headers, json=payload, timeout=120, stream=True) as response:
            response.raise_for_status()
            print("\n--- 📡 Backend Response (Streaming) ---")
            full_response_text = ""
            buffer = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data:'):
                        buffer += decoded_line[len('data:'):].strip()
                        while buffer:
                            try:
                                # Find the end of the first JSON object
                                json_data, index = json.JSONDecoder().raw_decode(buffer)
                                print(json.dumps(json_data, indent=2))
                                if "content" in json_data and "parts" in json_data["content"]:
                                    for part in json_data["content"]["parts"]:
                                        if "text" in part:
                                            full_response_text += part["text"]
                                # Remove the parsed JSON object from the buffer
                                buffer = buffer[index:].strip()
                            except json.JSONDecodeError:
                                # Incomplete JSON object, break and wait for more data
                                break
                    elif "error" in decoded_line:
                        print(f"Stream Error: {decoded_line}")
                        buffer = "" # Clear buffer on stream error

            print("\n--- ✅ Final Assistant Response ---")
            print(full_response_text if full_response_text else "[No text response received]")
            print("-" * 30)
            return full_response_text

    except requests.exceptions.RequestException as e:
        print(f"\n--- ❌ ERROR ---")
        print(f"An error occurred while calling the backend: {e}")
        if e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        print("-" * 15)
        return None

def get_user_id_by_email(email: str) -> int:
    """Retrieves the user ID for a given email address."""
    print(f"\n--- Getting user ID for: {email} ---")
    endpoint = f"{BASE_URL}/users/by_email/{email}"
    try:
        response = requests.get(endpoint, headers=HEADERS)
        response.raise_for_status()
        user_id = response.json()["id"]
        print(f"✅ User ID found: {user_id}")
        return user_id
    except requests.exceptions.RequestException as e:
        print(f"--- ❌ ERROR getting user ID ---")
        print(f"An error occurred: {e}")
        if e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return None

def purge_user_data(user_id: int):
    """Purges all data for a user."""
    print(f"\n--- Purging data for user: {user_id} ---")
    endpoint = f"{BASE_URL}/users/{user_id}/purge"
    try:
        response = requests.delete(endpoint, headers=HEADERS)
        response.raise_for_status()
        print("✅ User data purged successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"--- ❌ ERROR purging user data ---")
        print(f"An error occurred: {e}")
        if e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response content: {e.response.text}")
        return False

def test_add_task():
    """Tests adding a task via the agent."""
    prompt = "go to asiscs store on saturday at 3 pm and buy new running shoes"
    run_agent(prompt)
    time.sleep(15)  # Increased delay
    prompt = "go swimming with jules tomorrow at 7:30 pm after work"
    run_agent(prompt)

def test_update_task():
    """Tests updating a task via the agent."""
    prompt = "actually, let's move the deadline of our swimming task to 8:30 pm so we can grab dinner before"
    run_agent(prompt)

def test_add_input_log():
    """Tests adding an input log via the agent."""
    prompt = "I just had a great idea for a new project about sustainable farming."
    run_agent(prompt)

def test_update_background_info():
    """Tests updating background information via the agent."""
    prompt = "my name is mike, i am 30 year old male living in munich, germany"
    run_agent(prompt)
    time.sleep(15)  # Increased delay
    prompt = """
    My values are:
    - Self-improvement
    - Taking good care of my health
    - Being kind to strangers

    My challenges are:
    - Plan ahead more proactively

    My goals are:
    - Workout every day for at least 30 minutes
    - Do 2 weeks of video journaling every day
    - Publish a Youtube video every week until I have 100 subscribers
    """
    run_agent(prompt)

def test_list_tasks():
    """Tests listing tasks via the agent."""
    prompt = "Please list my open tasks."
    run_agent(prompt)

def test_daily_journal():
    """Tests adding a daily journal entry."""
    prompt = "just went to the forest for a walk and recorded my daily vlog"
    run_agent(prompt)

def test_add_more_tasks():
    """Tests adding more tasks."""
    prompts = [
        "Publish ADK demo MVP as a public GitHub repository latest today 12:00 pm.",
        "Film the video for the ADK demo MVP during my lunch break at 12:30 pm.",
    ]
    for prompt in prompts:
        run_agent(prompt)
        time.sleep(10)

def test_add_more_logs():
    """Tests adding more input logs."""
    prompts = [
        "I am currently checking the simple examples in the ADK official GitHub repo, specifically the personalized shopping, financial advisor, and brand search optimization demos.",
        "I was thinking maybe I can also just implement a simple debate system with my Life Tracker for the ADK hackathon?",
    ]
    for prompt in prompts:
        run_agent(prompt)
        time.sleep(10)

if __name__ == "__main__":
    print("🤖 Starting backend service test script...")

    # --- Test Suite ---
    # You can comment/uncomment the tests you want to run.

    # Purge user data before running tests
    user_id = get_user_id_by_email(USER_EMAIL)
    if user_id:
        purge_user_data(user_id)

    # Test 1: Add a new task
    test_add_task()
    time.sleep(10)

    # Test 2: Update a task
    test_update_task()
    time.sleep(10)

    # Test 3: Add a new input log
    test_add_input_log()
    time.sleep(10)

    # Test 4: Update background info
    test_update_background_info()
    time.sleep(10)

    # Test 5: List tasks
    test_list_tasks()
    time.sleep(10)

    # Test 6: Daily journal
    test_daily_journal()
    time.sleep(10)

    # Test 7: Add more tasks
    test_add_more_tasks()
    time.sleep(10)

    # Test 8: Add more logs
    test_add_more_logs()

    print("\n✅ Test script finished.")
