from .services import stt_processing, translate_text, tts_processing

async def process_audio_pipeline(audio_bytes, source_lang, target_lang):
    
    transcript = await stt_processing(audio_bytes, source_lang)
    
    translated_text = await translate_text(transcript,source_lang, target_lang)
    
    output_audio = await tts_processing(translated_text, target_lang)
    
    return output_audio