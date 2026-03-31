import json
import ctypes
import os

def load_config():
    with open('../config/settings.json', 'r') as f:
        return json.load(f)

def run_vault():
    config = load_config()
    print(f"Starting {config['app_name']} vault engine...")
    
    # In a real scenario, we would load the compiled .so/.dll here
    # lib = ctypes.CDLL('./core/encryptor.so')
    print("Connecting to C-Core for AES-256 processing...")

if __name__ == "__main__":
    run_vault()