import os
import csv
import io
import time
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# === CONFIG ===
API_ENDPOINT = "https://api.planhat.com/customfields"
REQUIRED_FIELDS = ["object", "name", "listValues", "type"]

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Planhat Field Magicician</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            margin-bottom: 10px;
        }
        .note {
            text-align: center;
            font-size: 14px;
            margin-bottom: 30px;
        }
        label {
            font-weight: bold;
            display: block;
            margin-bottom: 6px;
        }
        input[type="text"],
        input[type="file"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 6px;
            box-sizing: border-box;
        }
        input[type="submit"] {
            background-color: #007BFF;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
        pre {
            background-color: #eee;
            padding: 20px;
            border-radius: 6px;
            font-size: 14px;
            white-space: pre-wrap;
            margin-top: 30px;
        }
        a {
            color: #007BFF;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h2>Upload Planhat Fields CSV</h2>
    <div class="note">
        Use this template to fill in values:<br>
        <a href="https://docs.google.com/spreadsheets/d/1zAM1HCw3TkICgVET-nleYQA7mNro5VN1dLA6xclfUVc/edit?gid=0#gid=0"
           target="_blank">
            Google Sheet Template
        </a>
    </div>
    <form method="POST" enctype="multipart/form-data">
        <label for="token">Planhat API Token</label>
        <input type="text" name="token" id="token" required>

        <label for="file">CSV File</label>
        <input type="file" name="file" id="file" accept=".csv" required>

        <input type="submit" value="Upload and Run">
    </form>

    <pre>{{ logs }}</pre>
</body>
</html>
"""


@app.route('/ping')
def ping():
    return "pong", 200


def validate_row(row, row_num):
    missing = [f for f in REQUIRED_FIELDS if not row.get(f, "").strip()]
    if missing:
        return False, f"Row {row_num}: Missing fields {missing}"
    return True, ""


def create_custom_field(payload, name_value, token, retries=3):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(API_ENDPOINT, json=payload, headers=headers)
            if resp.ok:
                return f"✅ Created: {name_value}"
            else:
                return f"❌ Error ({resp.status_code}) for '{name_value}': {resp.text}"
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1)
            else:
                return f"⚠️ Network failure after {retries} attempts: {name_value}"


@app.route('/', methods=['GET', 'POST'])
def upload():
    logs = []
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        if not token:
            logs.append("Missing API token.")
            return render_template_string(TEMPLATE, logs="\n".join(logs))

        file = request.files.get('file')
        if not file:
            logs.append("No file uploaded.")
        else:
            stream = io.StringIO(file.stream.read().decode('utf-8'),
                                 newline=None)
            reader = csv.DictReader(stream)
            for i, row in enumerate(reader, start=2):
                ok, msg = validate_row(row, i)
                if not ok:
                    logs.append(msg)
                    continue
                payload = {
                    "parent":
                    row["object"].strip(),
                    "type":
                    row["type"].strip(),
                    "isHidden":
                    False,
                    "isFeatured":
                    True,
                    "name":
                    row["name"].strip(),
                    "listValues": [
                        v.strip() for v in row["listValues"].split(',')
                        if v.strip()
                    ]
                }
                logs.append(
                    create_custom_field(payload, row["name"].strip(), token))

    return render_template_string(TEMPLATE, logs="\n".join(logs))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
