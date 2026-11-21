"""Key Diagnostic Tool for TypoPilot.

Run this script to see exactly what key events Windows detects when you press your keyboard buttons.
"""

import sys
import time
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

print("=" * 60)
print("       TypoPilot - Keyboard Key Diagnostic Tool")
print("=" * 60)
print("Please press F2 (or Fn + F2) on your keyboard now...")
print("Press Ctrl + C to exit anytime.")
print("=" * 60)
print()

def on_press(key):
    try:
        if key == Key.f2:
            print("[SUCCESS] DETECTED: Standard 'F2' Key! (TypoPilot trigger works!)")
        elif hasattr(key, "name") and "f2" in key.name.lower():
            print(f"[SUCCESS] DETECTED: {key} (Matches F2!)")
        else:
            # Check if it was a multimedia or brightness key
            name = getattr(key, "name", str(key))
            print(f"[DETECTED KEY]: {name}")
            if "brightness" in name or "media" in name or "volume" in name:
                print("  --> NOTE: Your laptop is in Multimedia mode!")
                print("  --> To send real F2, press: [Fn + F2] together!")
    except Exception as e:
        print(f"Error: {e}")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
