import json
import os
import urllib.request

BASE = os.getenv("API_URL", "http://127.0.0.1:8001")

def check(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as response:
        assert response.status == 200
        print(f"PASS {path}")

def predict():
    payload = json.dumps({
        "surface": 120,
        "bedrooms": 3,
        "age": 10,
        "distance_center": 5.0
    }).encode("utf-8")

    request = urllib.request.Request(
        BASE + "/predict",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
        assert isinstance(result["predicted_price"], (int, float))
        print("PASS /predict :", result["predicted_price"])

check("/health")
check("/metrics")
predict()
print("SMOKE TEST OK")
