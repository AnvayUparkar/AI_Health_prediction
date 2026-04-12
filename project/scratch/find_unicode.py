
import os

target_char = "\U0001f4e8" # 📧

def find_char(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if target_char in content:
                            print(f"FOUND in {path}")
                except Exception:
                    pass

find_char("c:\\Users\\Anvay Uparkar\\Hackathon projects\\AI_Health_prediction\\project")
