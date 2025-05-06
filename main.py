from flask import Flask, request, render_template_string
import csv
import requests
import time
import io

app = Flask(__name__)

# === CONFIG ===
API_ENDPOINT = "https://api.planhat.com/customfields"
BEARER_TOKEN = "your_planhat_token_here"  # Replace this or load from env

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

REQUIRED_FIELDS = ["object", "name", "listValues", "type"]

def validate_row(row, row_num):
    missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
    if missing:
        return False, f"Row {row_num}: Missing fields {missing}"
    return True, ""

def create_custom_field(payload, name_value, retries=3):
    for attempt in range(retries):
        try:
            response = requests.post(API_ENDPOINT, json=payload, headers=HEADERS)
            if response.ok:
                return f"✅ Created: {name_value}"
            else:
                return f"❌ Error ({response.status_code}) for '{name_value}': {response.text}"
        except requests.RequestException as e:
            time.sleep(1)
    return f"⚠️ Failed after retries: {name_value}"

@app.route('/', methods=['GET', 'POST'])
def upload():
    result_logs = []
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            result_logs.append("No file uploaded.")
        else:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            for row_num, row in enumerate(reader, start=2):
                is_valid, msg = validate_row(row, row_num)
                if not is_valid:
                    result_logs.append(msg)
                    continue
                payload = {
                    "parent": row["object"].strip(),
                    "type": row["type"].strip(),
                    "isHidden": False,
                    "isFeatured": True,
                    "name": row["name"].strip(),
                    "listValues": [v.strip() for v in row["listValues"].split(",") if v.strip()]
                }
                result_logs.append(create_custom_field(payload, row["name"]))
    return render_template_string("""
        <h2>Upload CSV File</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <input type="submit" value="Upload and Run">
        </form>
        <hr>
        <pre>{{ logs }}</pre>
    """, logs="\n".join(result_logs))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)
