import os
import requests
import base64
import tempfile
import subprocess
from django.core.validators import ValidationError
import magic  
import json
import aiohttp
import re
from functools import lru_cache

GCP_API_KEY = os.getenv('GCP_API_KEY')


def detect_audio_format(audio_bytes):
    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(audio_bytes)
    
    format_map = {
        'audio/webm': 'WEBM_OPUS',
        'audio/mpeg': 'MP3',
        'audio/wav': 'LINEAR16',
        'audio/ogg': 'OGG_OPUS'
    }
    
    return format_map.get(file_type, 'MP3')

def validate_audio(audio_bytes):
    """Validate audio using temporary file"""
    try:
        print(f"Validating audio size: {len(audio_bytes)} bytes")
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", 
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", tmp.name],
                capture_output=True,
                text=True,
                check=True
            )
            
            duration = float(result.stdout.strip())
            print(f"Validated duration: {duration}s")
            if duration > 60:
                raise ValidationError("Audio exceeds 1 minute limit")
                
    except subprocess.CalledProcessError as e:
        raise ValidationError(f"FFprobe error: {e.stderr}")
    finally:
        tmp.close()

        
def load_phrases(lang):
    try:
        file_path = f"../app/phrases/{lang}_phrases.txt"
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Phrase file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading phrases: {str(e)}")
        return []
    
def load_normalization_rules(lang):
    try:
        with open(f"../app/phrases/normalization_{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    
async def stt_processing(audio_bytes, language):
    validate_audio(audio_bytes)
    endpoint = "https://speech.googleapis.com/v1/speech:recognize"
    audio_format = detect_audio_format(audio_bytes)
    
    config = {
        "encoding": audio_format.upper(),  # Now dynamic
        "sampleRateHertz": 48000,
        "languageCode": "en-US" if language == "en" else "hi-IN",
        "audioChannelCount": 1,
        "enableAutomaticPunctuation": True
    }
    
    phrases = load_phrases(language)
    # English-specific enhancements
    if language == "en":
        config.update({
            "useEnhanced": True,
            "model": "latest_long",
            "speechContexts": [{
            "phrases": phrases,
                "boost": 40.0  # Increase phrase priority
            }],
            "transcriptNormalization": {
            "entries": load_normalization_rules(language)
        }
        })
    # Hindi configuration
    else:
        if phrases:
            config["speechContexts"] = [{
                "phrases": phrases,
                "boost": 15.0
            }]

    
    audio = {"content": base64.b64encode(audio_bytes).decode("utf-8")}
    
    response = requests.post(
        f"{endpoint}?key={GCP_API_KEY}",
        json={"config": config, "audio": audio}
    )
    
    if response.status_code != 200:
        raise Exception(f"STT Error: {response.text}")
    print("STT Response:")
    print(response.json()['results'][0]['alternatives'][0]['transcript'])
    return response.json()['results'][0]['alternatives'][0]['transcript']


# Translation 


GLOSSARY_PATH = "../app/phrases/glossary.json"
PHRASES_DIR = "../app/phrases/"

def load_glossary(source_lang, target_lang):
    """Load and cache glossary terms for language pair"""
    glossary = {
        "en-hi": ["Vatika", "Udyogi"],
        "hi-en": ["वाटिका", "उद्योगी"]
    }
    lang_key = f"{source_lang}-{target_lang}"
    return glossary.get(lang_key, [])

def load_normalization_rules(lang):
    """Load and validate normalization rules"""
    try:
        with open(f"{PHRASES_DIR}/normalization_{lang}.json", "r", encoding="utf-8") as f:
            rules = json.load(f)
            return [r for r in rules if validate_rule(r)]
    except FileNotFoundError:
        print(f"No normalization rules for {lang}")
        return []
    except Exception as e:
        print(f"Error loading normalization: {str(e)}")
        return []

def validate_rule(rule):
    """Ensure rule has required fields"""
    return isinstance(rule, dict) and 'search' in rule and 'replace' in rule

def create_placeholders(text, glossary_terms):
    """Replace glossary terms with temporary placeholders"""
    placeholder_map = {}

    # Sort terms by length descending to prevent partial matches
    sorted_terms = sorted(glossary_terms, key=len, reverse=True)

    # Case-insensitive pattern with word boundaries
    pattern = re.compile(
        r'(?i)\b(' + '|'.join(map(re.escape, sorted_terms)) + r')\b',
        flags=re.UNICODE
    )

    def replacer(match):
        original = match.group(0)
        placeholder = f"##GLOSSARY_{len(placeholder_map)}##"
        placeholder_map[placeholder] = original
        return placeholder

    protected_text = pattern.sub(replacer, text)
    return protected_text, placeholder_map

def restore_terms(text, placeholder_map):
    """Restore original terms from placeholders"""
    for placeholder, term in placeholder_map.items():
        text = text.replace(placeholder, term)
    return text

def apply_normalization(text, rules):
    """Apply post-translation normalization safely"""
    try:
        for rule in rules:
            try:
                compiled = re.compile(rule['search'], flags=re.IGNORECASE)
                text = compiled.sub(rule['replace'], text)
            except re.error as e:
                print(f"Invalid regex {rule['search']}: {str(e)}")
        return text
    except Exception as e:
        print(f"Normalization failed: {str(e)}")
        return text

async def translate_text(text, source_lang, target_lang):
    """Enhanced translation with glossary preservation using Gemini prompt"""
    try:
        # 1. Load linguistic resources
        glossary = load_glossary(source_lang, target_lang)
        norm_rules = load_normalization_rules(target_lang)

        # 2. Protect glossary terms
        protected_text, placeholders = create_placeholders(text, glossary)
        print(f"Protected text: {protected_text}")

        # 3. Construct translation prompt
        prompt = (
            f"Translate the following text from {source_lang} to {target_lang}. "
            f"Ensure that the following terms remain unchanged: {', '.join(glossary)}.\n"
            f"Text: {protected_text}"
        )

        gemini_endpoint = "https://api.gemini.com/translate"
        headers = {
            "Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "max_tokens": 1000
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(gemini_endpoint, headers=headers, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Gemini API Error: {await response.text()}")

                result = await response.json()
                translated = result.get('text', '').strip()

        # 4. Restore and normalize
        restored = restore_terms(translated, placeholders)
        normalized = apply_normalization(restored, norm_rules)

        print(f"Final translation: {normalized}")
        return normalized

    except Exception as e:
        print(f"Translation failed: {str(e)}")
        raise


#For TTS

async def tts_processing(text, language):
    endpoint = "https://texttospeech.googleapis.com/v1/text:synthesize"
    
    voice_config = {
        "languageCode": "en-US" if language == "en" else "hi-IN",
        "name": "en-US-Neural2-J" if language == "en" else "hi-IN-Neural2-D"
    }
    print("in TTS Now")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{endpoint}?key={GCP_API_KEY}",  
            json={
                "input": {"text": text},
                "voice": voice_config,
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": 1.0,
                    "pitch": 0.0
                }
            }
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"TTS Error: {error}")
            
            data = await response.json()
            
            return data['audioContent']