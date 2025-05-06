# Initialize once at startup
translation_service = TranslationService()

# In your WebRTC handler
@socketio.on("translation_request")
def handle_translation_request(data):
    result = translation_service.translate(
        text=data['text'],
        target_lang=data.get('target_lang', 'es'),
        source_lang=data.get('source_lang')
    )
    
    if result['translated_text']:
        emit("translation_result", {
            "original": data['text'],
            "translated": result['translated_text'],
            "source_lang": result['detected_lang'],
            "target_lang": result['target_lang']
        }, room=data['room_id'])
    else:
        emit("translation_error", {
            "error": "Translation failed",
            "original": data['text']
        }, room=data['room_id'])