import collections.abc
import collections
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping

import ccapi
import inspect

client = ccapi.Client()
print("--- Client.search help ---")
try:
    print(inspect.signature(client.search))
    print(client.search.__doc__)
except:
    pass

print("--- Trying search ---")
try:
    results = client.search(model="boolean") # Guessing parameter
    print(results)
except Exception as e:
    print(f"Search failed: {e}")

try:
    # Try generic search or listing
    # Maybe client.get('/api/public/models')?
    # The client has a .get method
    pass
except:
    pass
