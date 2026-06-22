from ccapi import Client

try:
    client = Client()
    print("Ping:", client.ping())
    
    print("Fetching models...")
    models = client.get("model", size=5)
    print(f"Fetched {len(models)} models.")
    for m in models:
        print(f"ID: {m.id}, Name: {m.name}")

except Exception as e:
    print(f"Error: {e}")
