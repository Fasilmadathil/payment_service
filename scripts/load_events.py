import requests
import json
from time import sleep

URL = "https://payment-service-o236.onrender.com/events/"

with open("data/sample_events.json") as f:
    events = json.load(f)

for i, event in enumerate(events):
    response = requests.post(URL, json=event)

    try:
        data = response.json()
    except:
        print("Error:", event["event_id"], response.text)
        continue

    status = data.get("status")

    if response.status_code != 200:
        print("Error:", event["event_id"], response.text)

    elif status == "success":
        pass  # don't spam logs

    elif status in ["blocked", "stale", "invalid"]:
        print("Ignored:", event["event_id"], "-", data.get("message"))

    elif status == "duplicate":
        print("Duplicate:", event["event_id"])

    else:
        print("Unknown:", event["event_id"], data)

    if i % 100 == 0:
        print(f"Processed {i} events")

    sleep(0.001)