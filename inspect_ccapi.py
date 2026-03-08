import ccapi
import inspect

print("ccapi dir:", dir(ccapi))

# Try to find a Client or similar class
for name, obj in inspect.getmembers(ccapi):
    if inspect.isclass(obj):
        print(f"Class: {name}")
    elif inspect.isfunction(obj):
        print(f"Function: {name}")
