import sys
import importlib

def check_import(module_name):
    try:
        importlib.import_module(module_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)

critical_modules = {
    "flask": "Flask",
    "ics": "ics",
    "psycopg2": "psycopg2",
    "requests": "requests",
    "apscheduler": "APScheduler",
    "dotenv": "python-dotenv",
    "pytz": "pytz",
    "google.genai": "google-genai"
}

print("=== Slate Reminder Bot: Environment Verification ===\n")
print(f"Python Version: {sys.version}")
print(f"Executable: {sys.executable}")
print("\n--- Search Paths ---")
for path in sys.path:
    print(f"  - {path}")

print("\n--- Dependency Check ---")
all_ok = True
for module, package in critical_modules.items():
    success, msg = check_import(module)
    status = "✅" if success else "❌"
    print(f"{status} {package:15} : {msg}")
    if not success:
        all_ok = False

print("\n--- Summary ---")
if all_ok:
    print("✨ All dependencies are correctly installed in this environment.")
else:
    print("⚠️ Some dependencies are missing!")
    print("\nTo fix this, run the following command in your terminal:")
    print("pip install -r requirements.txt")

input("\nPress Enter to exit...")
