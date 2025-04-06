from flask import Flask, request, jsonify
from app import app
import os
import base64
import json
import requests


def load_phrases(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

PHRASES = load_phrases(os.path.join(os.path.dirname(__file__), "phrases.txt"))

def load_normalization(filepath):
    import json
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

NORMALIZATION_ENTRIES = load_normalization(os.path.join(os.path.dirname(__file__), "normalization.json"))

@app.route('/transcribe-english', methods=['POST'])
def transcribe_english():
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["file"]
    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({"error": "Empty audio file"}), 400

    # Base64-encode the audio content
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    # Payload for the Speech-to-Text API (V1 endpoint)
    payload = {
        "config": {
            "encoding": "LINEAR16",         # Adjust this if your audio is in a different format
            "sampleRateHertz": 48000,       # Update according to your audio file's sample rate
            "languageCode": "en-US",        # Use one valid language code (change as needed)
            "enableAutomaticPunctuation": True,
            "model":"latest_long",
            "speechContexts": [
                {"phrases": PHRASES, "boost": 40.0}
            ],
            "transcriptNormalization": {
            "entries": NORMALIZATION_ENTRIES
        }
        },
        "audio": {"content": audio_base64},
    }

    
    API_KEY = app.config.get("GCP_API_KEY")
    
    if not API_KEY:
        return jsonify({"error": "API key not configured"}), 500

    endpoint = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"
    response = requests.post(endpoint, json=payload)

    
    if response.status_code != 200:
        return jsonify({"error": "Speech API error", "status_code": response.status_code, "details": response.text}), response.status_code

    try:
        result = response.json()
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to decode JSON from Speech API", "response_text": response.text}), 500

    
    transcripts = []
    for res in result.get("results", []):
        alternatives = res.get("alternatives", [])
        if alternatives:
            transcripts.append(alternatives[0].get("transcript", ""))

    confidence = result['results'][0]['alternatives'][0]['confidence']

    return jsonify({"transcripts": transcripts, "Confidence": confidence})


@app.route('/transcribe-hindi', methods=['POST'])
def transcribe_hindi():
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["file"]
    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({"error": "Empty audio file"}), 400

    # Base64-encode the audio content
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    # Payload for the Speech-to-Text API (V1 endpoint)
    payload = {
        "config": {
            "encoding": "LINEAR16",         # Adjust this if your audio is in a different format
            "sampleRateHertz": 48000,       # Update according to your audio file's sample rate
            "languageCode": "hi-IN",        # Use one valid language code (change as needed)
            "enableAutomaticPunctuation": True,
            "model":"latest_long",
            "speechContexts": [
                {"phrases": PHRASES, "boost": 40.0}
            ],
            "transcriptNormalization": {
            "entries": NORMALIZATION_ENTRIES
        }
        },
        "audio": {"content": audio_base64},
    }

    
    API_KEY = app.config.get("GCP_API_KEY")

    if not API_KEY:
        return jsonify({"error": "API key not configured"}), 500

    endpoint = f"https://speech.googleapis.com/v1/speech:recognize?key={API_KEY}"
    response = requests.post(endpoint, json=payload)

    
    if response.status_code != 200:
        return jsonify({"error": "Speech API error", "status_code": response.status_code, "details": response.text}), response.status_code

    try:
        result = response.json()
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to decode JSON from Speech API", "response_text": response.text}), 500

    
    transcripts = []
    for res in result.get("results", []):
        alternatives = res.get("alternatives", [])
        if alternatives:
            transcripts.append(alternatives[0].get("transcript", ""))

    confidence = result['results'][0]['alternatives'][0]['confidence']
    return jsonify({"transcripts": transcripts, "Confidence": confidence})