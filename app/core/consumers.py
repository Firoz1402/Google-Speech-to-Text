import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from .pipeline import process_audio_pipeline

connections = {}

class TranslationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        connections[self.channel_name] = None

    async def disconnect(self, close_code):
        connections.pop(self.channel_name, None)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                data = json.loads(text_data)
                
                if 'language' in data:
                    
                    if data['language'] not in ['en', 'hi']:
                        await self.send(json.dumps({'error': 'Invalid language'}))
                        return
                    
                    connections[self.channel_name] = data['language']
                    await self.send(json.dumps({'status': f'Language set to {data["language"]}'}))
                
                elif 'audio' in data:
                    # Handle audio processing
                    source_lang = connections.get(self.channel_name)
                    if not source_lang:
                        await self.send(json.dumps({'error': 'Set language first'}))
                        return
                    
                    audio_bytes = base64.b64decode(data['audio'])
                    target_lang = 'hi' if source_lang == 'en' else 'en'
                    
                    
                    output_audio = await process_audio_pipeline(
                        audio_bytes=audio_bytes,
                        source_lang=source_lang,
                        target_lang=target_lang
                    )
                    
                    # Find target client
                    target_channels = [chan for chan, lang in connections.items() 
                                      if lang == target_lang]
                    
                    if target_channels:
                        
                        await self.channel_layer.send(
                            target_channels[0],
                            {
                                "type": "translation.audio",
                                "audio": output_audio,
                                "language": target_lang
                            }
                        )

        except Exception as e:
            await self.send(json.dumps({'error': str(e)}))

    async def translation_audio(self, event):
    
        await self.send(json.dumps({
            'audio': event['audio'],
            'language': event['language']
        }, ensure_ascii=False))