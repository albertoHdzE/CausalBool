import ccapi
import inspect

try:
    print("Client init:", inspect.signature(ccapi.Client.__init__))
except Exception as e:
    print("Client init error:", e)

try:
    print("load_model sig:", inspect.signature(ccapi.load_model))
except Exception as e:
    print("load_model error:", e)

# Try to see if we can list models or get a public one
print("Client methods:")
for name, _ in inspect.getmembers(ccapi.Client):
    if not name.startswith("_"):
        print(f"  {name}")
