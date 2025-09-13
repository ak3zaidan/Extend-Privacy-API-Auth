import json
import requests

# === GLOBALS ===
TOKEN = ""
CARD_TYPE = "CATEGORY_LOCKED"  # MERCHANT_LOCKED, SINGLE_USE, or CATEGORY_LOCKED
MERCHANT_HOSTNAME = "amazon.com"
CATEGORY_NAME = "Dining"  # Only used if CARD_TYPE is CATEGORY_LOCKED

url = "https://app.privacy.com/api/v2/cards"

# === All possible categories ===
CATEGORY_REQUESTS = {
    "Dining": {
        "merchantCategory": "664e5bd83078810a31188699",
        "type": "UNLOCKED",
        "memo": "food1",
        "meta": {"customStyle": {"bgColor": "F1B32C", "icon": "🍔"}}
    },
    "Entertainment": {
        "merchantCategory": "664e5bf13078816b3018869e",
        "type": "UNLOCKED",
        "memo": "a",
        "meta": {"customStyle": {"bgColor": "82BCF6", "icon": "🎭"}}
    },
    "Groceries": {
        "merchantCategory": "664e5bf930788143241886a0",
        "type": "UNLOCKED",
        "memo": "f",
        "meta": {"customStyle": {"bgColor": "9CDE7D", "icon": "🥬"}}
    },
    "Health and Wellness": {
        "merchantCategory": "664e5c01307881b1f71886a5",
        "type": "UNLOCKED",
        "memo": "d",
        "meta": {"customStyle": {"bgColor": "420B6D", "icon": "🧬"}}
    },
    "Pets and Veterinary Services": {
        "merchantCategory": "664e5c09307881a2111886aa",
        "type": "UNLOCKED",
        "memo": "g",
        "meta": {"customStyle": {"bgColor": "C193EF", "icon": "🦮"}}
    },
    "Retail": {
        "merchantCategory": "664e5c11307881b8d91886af",
        "type": "UNLOCKED",
        "memo": "f",
        "meta": {"customStyle": {"bgColor": "8CD0CC", "icon": "🛍️"}}
    },
    "Sports and Fitness": {
        "merchantCategory": "664e5c193078816a531886b1",
        "type": "UNLOCKED",
        "memo": "g",
        "meta": {"customStyle": {"bgColor": "10003D", "icon": "🎾"}}
    },
    "Subscriptions and Utilities": {
        "merchantCategory": "664e5c223078815e621886b8",
        "type": "UNLOCKED",
        "memo": "h",
        "meta": {"customStyle": {"bgColor": "6474AF", "icon": "📱"}}
    },
    "Travel and Transportation": {
        "merchantCategory": "664e5c2b3078813dc51886ba",
        "type": "UNLOCKED",
        "memo": "c",
        "meta": {"customStyle": {"bgColor": "2EA3AA", "icon": "🏖️"}}
    },
    "Automotive and Fuel": {
        "merchantCategory": "664e5c3330788102db1886bc",
        "type": "UNLOCKED",
        "memo": "v",
        "meta": {"customStyle": {"bgColor": "8FA3BA", "icon": "🛞"}}
    },
    "Cleaning, Repair and Maintenance": {
        "merchantCategory": "664e5c3b30788170af1886be",
        "type": "UNLOCKED",
        "memo": "b",
        "meta": {"customStyle": {"bgColor": "FB8AA5", "icon": "🧼"}}
    },
    "Digital Goods": {
        "merchantCategory": "664e5c4230788108f61886c0",
        "type": "UNLOCKED",
        "memo": "v",
        "meta": {"customStyle": {"bgColor": "676D83", "icon": "🎮"}}
    },
    "Education": {
        "merchantCategory": "664e5c4e307881fcd61886c9",
        "type": "UNLOCKED",
        "memo": "b",
        "meta": {"customStyle": {"bgColor": "9191F7", "icon": "📚"}}
    },
    "Home and Construction": {
        "merchantCategory": "664e5c57307881a9d41886cb",
        "type": "UNLOCKED",
        "memo": "v",
        "meta": {"customStyle": {"bgColor": "48935D", "icon": "🏡"}}
    },
    "Nonprofit and Social Organizations": {
        "merchantCategory": "664e5c613078816e371886cd",
        "type": "UNLOCKED",
        "memo": "v",
        "meta": {"customStyle": {"bgColor": "000000", "icon": "🎗️"}}
    },
    "Professional Services": {
        "merchantCategory": "664e5c7a3078811c371886cf",
        "type": "UNLOCKED",
        "memo": "v",
        "meta": {"customStyle": {"bgColor": "C8B1CE", "icon": "💼"}}
    }
}

# === Build payload and calculate Content-Length ===
if CARD_TYPE == "MERCHANT_LOCKED":
    payload_dict = {
        "type": CARD_TYPE,
        "memo": "Gen Card X",
        "meta": {"hostname": MERCHANT_HOSTNAME}
    }
elif CARD_TYPE == "CATEGORY_LOCKED":
    if CATEGORY_NAME not in CATEGORY_REQUESTS:
        raise ValueError(f"Unknown category '{CATEGORY_NAME}'. Available: {list(CATEGORY_REQUESTS)}")
    payload_dict = CATEGORY_REQUESTS[CATEGORY_NAME]
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
    card = response.json()
    card_info = {
        "type": card.get("type"),
        "PAN": card.get("PAN"),
        "CVV": card.get("CVV"),
        "expMonth": card.get("expMonth"),
        "expYear": card.get("expYear")
    }

    if card.get("type") == "MERCHANT_LOCKED":
        style = card.get("style", {})
        if style and "strippedHostname" in style:
            card_info["strippedHostname"] = style.get("strippedHostname")

    print("Card Info:", card_info)

except json.JSONDecodeError:
    print("Failed to parse JSON response")
    print(response.text)
