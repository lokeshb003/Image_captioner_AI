from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import base64
import requests
import os
import traceback
from pdf2image import convert_from_path

app = Flask(__name__)
CORS(app)

GOOGLE_API_KEY = "AIzaSyCLEIBwgSCwCzFtFn6LpUOJcs3K0iAQlnE"

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

# Convert PDF to JPEG and encode the first page
def convert_pdf_to_jpeg(pdf_path):
    try:
        images = convert_from_path(pdf_path, dpi=200)
        if not images:
            raise ValueError("No images found in PDF")

        # Save the first page as a JPEG
        jpeg_path = pdf_path.replace(".pdf", ".jpg")
        images[0].save(jpeg_path, "JPEG")

        # Encode the image to base64
        return encode_image_to_base64(jpeg_path)
    except Exception as e:
        print("Error converting PDF to JPEG:", e)
        raise

# Generate content (API call)
def generate_content(base64_image_data, mime_type="image/jpeg"):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [
                    {"text": "Generate only the school name, place of the school, Student name and Total Marks only. No need for additional Data."},
                    {"inline_data": {"mime_type": mime_type, "data": base64_image_data}}
                ]
            }]
        }
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        # Debugging: Print the entire response
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

# Handle file upload (image or PDF)
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part in request"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        file_path = os.path.join("uploads", file.filename)
        file.save(file_path)

        # Check if the file is an image or PDF
        if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Encode image to base64
            base64_image_data = encode_image_to_base64(file_path)
            response = generate_content(base64_image_data, "image/jpeg")
        elif file.filename.lower().endswith('.pdf'):
            # Convert PDF to JPEG and encode
            base64_image_data = convert_pdf_to_jpeg(file_path)
            response = generate_content(base64_image_data, "image/jpeg")
        else:
            return jsonify({"error": "Unsupported file type"}), 400

        return jsonify(response)

    except Exception as e:
        error_message = str(e)
        error_details = traceback.format_exc()
        return jsonify({"error": error_message, "details": error_details}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

