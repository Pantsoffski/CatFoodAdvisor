import requests

# The payload remains simple. The AI Agent will handle the data retrieval and math via tools.
data = {
    "breed": "mieszaniec",
    "age": 15,
    "health": "nadczynność tarczycy",
    "food_name": "Whiskas 1+ z wołowiną"
}

url = "https://pantsoffski-cat-food-advisor.hf.space/analyze-cat-food"

try:
    print("Sending request to the Agent... (this might take a few seconds as tools are executed)")
    response = requests.post(url, json=data)
    response.raise_for_status()
    
    result = response.json()
    
    print("\n=== AGENT'S FINAL VERDICT ===")
    print(result.get('verdict', 'No verdict generated.'))
    
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    if hasattr(e.response, 'text'):
        print(f"Server details: {e.response.text}")