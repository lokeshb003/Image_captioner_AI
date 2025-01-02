from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import base64
import requests
import os
import traceback

app = Flask(__name__)
CORS(app)

GOOGLE_API_KEY = ""

# Create uploads folder if not exists
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Encode image to base64
def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        print("Error in encoding image to base64:", e)
        raise

# Generate content (API call)
def generate_content(base64_image_data):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [
                    {"text": "Caption this image."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64_image_data}}
                ]
            }]
        }
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        print("API Response:", response_json)

        # Extract the desired text
        candidates = response_json.get("candidates", [])
        if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
            text = candidates[0]["content"]["parts"][0]["text"]
            return {"text": text}

        return {"error": "Invalid API response structure"}
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return {"error": "Failed to communicate with the API", "details": str(e)}

# Serve the HTML frontend
@app.route('/')
def index():
    return render_template('index.html')

# Handle the image upload
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No file part in request"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Save file to a temporary location
        img_path = os.path.join("uploads", file.filename)
        file.save(img_path)

        # Encode image to base64
        base64_image_data = encode_image_to_base64(img_path)

        # Make API call
        response = generate_content(base64_image_data)
        return jsonify(response)

    except Exception as e:
        error_message = str(e)
        error_details = traceback.format_exc()
        return jsonify({"error": error_message, "details": error_details}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
