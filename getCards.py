import requests

TOKEN = ""

url = "https://app.privacy.com/api/v2/cards"

params = {
    "cardStates": "OPEN",
    "limit": 1000,
    "offset": 0,
    "sortField": "RECENTLY_USED",
    "sortOrder": "DESC"
}

headers = {
    "accept": "*/*",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0.1 Safari/605.1.15",
    "sec-fetch-dest": "empty",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=3, i",
    "accept-encoding": "gzip, deflate, br",
    "cookie": (
        f'token={TOKEN}; '
    )
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    json_data = response.json()
    cards = json_data.get("data", [])

    extracted_cards = []
    for card in cards:
        card_info = {
            "type": card.get("type"),
            "PAN": card.get("PAN"),
            "CVV": card.get("CVV"),
            "expMonth": card.get("expMonth"),
            "expYear": card.get("expYear")
        }

        # If merchant locked, include strippedHostname from the style object
        if card.get("type") == "MERCHANT_LOCKED":
            style = card.get("style", {})
            if style and "strippedHostname" in style:
                card_info["strippedHostname"] = style.get("strippedHostname")

        extracted_cards.append(card_info)

    print(extracted_cards)
else:
    print("Request failed with status code:", response.status_code)
    print(response.text)
