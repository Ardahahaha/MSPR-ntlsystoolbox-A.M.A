import json
import os
from datetime import datetime

def format_result(module_name: str, data: dict):
    timestamp = datetime.now().isoformat()
    output = {
        "module": module_name,
        "timestamp": timestamp,
        "data": data
    }
    
    print(f"\n[SUCCESS] Module {module_name} terminé.")
    
    os.makedirs("reports/json", exist_ok=True)
    filename = f"reports/json/{module_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=4)
    print(f"Rapport généré : {filename}")
