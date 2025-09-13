import json
import requests

# === GLOBALS ===
TOKEN = ""
CARD_TYPE =  "MERCHANT_LOCKED" # or "SINGLE_USE"
MERCHANT_HOSTNAME = "amazon.com"

url = "https://app.privacy.com/api/v2/cards"

# === Build payload and calculate Content-Length ===
if CARD_TYPE == "MERCHANT_LOCKED":
    payload_dict = {
        "type": CARD_TYPE,
        "memo": "Gen Card X",
        "meta": {"hostname": MERCHANT_HOSTNAME}
    }
else:
    payload_dict = {
        "type": CARD_TYPE,
        "memo": "Gen Card X"
    }

payload_str = json.dumps(payload_dict, separators=(',', ':'))
content_length = str(len(payload_str.encode('utf-8')))

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "origin": "https://app.privacy.com",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0.1 Safari/605.1.15",
    "content-length": content_length,
    "sec-fetch-dest": "empty",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=3, i",
    "accept-encoding": "gzip, deflate, br",
    "cookie": f"token={TOKEN};"
}

# === Send request ===
response = requests.post(
    url,
    headers=headers,
    data=payload_str,
    verify=False
)

print("Status:", response.status_code)

# === Extract card info ===
try:
    card = response.json()  # parse JSON
    card_info = {
        "type": card.get("type"),
        "PAN": card.get("PAN"),
        "CVV": card.get("CVV"),
        "expMonth": card.get("expMonth"),
        "expYear": card.get("expYear")
    }

    # If merchant locked, also include strippedHostname if available
    if card.get("type") == "MERCHANT_LOCKED":
        style = card.get("style", {})
        if style and "strippedHostname" in style:
            card_info["strippedHostname"] = style.get("strippedHostname")

    print("Card Info:", card_info)

except json.JSONDecodeError:
    print("Failed to parse JSON response")
    print(response.text)
