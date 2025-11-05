from google import genai
import json

with open('api.json', 'r') as f:
    config = json.load(f)

api_key = config.get('gemini')

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello, how are you?"
)

print(response.text)