import eventlet
eventlet.monkey_patch()  # Must come first for async compatibility

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import base64
from io import BytesIO
from PIL import Image
import pytesseract
from speech_recognition import Recognizer, AudioData
import numpy as np
from transformers import pipeline
import logging
import os

# NOTE: This line is for Windows only. Comment it out for Render/Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = '85ef43b403cc196276d86f1f8ac601e3'

# Configure CORS (important if frontend is hosted separately)
from flask_cors import CORS
CORS(app)

# Configure Socket.IO
socketio = SocketIO(app,
                   cors_allowed_origins="*",
                   engineio_logger=True,
                   logger=True,
                   async_mode='eventlet',
                   ping_timeout=60,
                   ping_interval=25,
                   max_http_buffer_size=100 * 1024 * 1024)  # 100MB

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
rooms = {}
active_translations = {}

# Initialize translation
translator = pipeline("translation", model="Helsinki-NLP/opus-mt-mul-en")
recognizer = Recognizer()

# Socket.IO Handlers
@socketio.on("connect")
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit("connection_response", {"status": "connected", "sid": request.sid})

@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")
    for room_id, room_data in list(rooms.items()):
        if request.sid in room_data['sids']:
            room_data['sids'].remove(request.sid)
            emit("user_left", {"user_id": request.sid}, room=room_id)
            if not room_data['sids']:
                del rooms[room_id]

@socketio.on("create_room")
def handle_create_room(data):
    room_id = data.get('room_id')
    user_id = data.get('user_id', request.sid)

    if room_id in rooms:
        emit("room_error", {"message": "Room already exists"})
        return

    rooms[room_id] = {'users': [user_id], 'sids': [request.sid]}
    join_room(room_id)
    emit("room_created", {"room_id": room_id, "users": [user_id]})
    logger.info(f"Room {room_id} created by {user_id}")

@socketio.on("join_room")
def handle_join_room(data):
    room_id = data.get('room_id')
    user_id = data.get('user_id', request.sid)

    if room_id not in rooms:
        emit("room_error", {"message": "Room does not exist"})
        return

    if user_id in rooms[room_id]['users']:
        emit("room_error", {"message": "User already in room"})
        return

    rooms[room_id]['users'].append(user_id)
    rooms[room_id]['sids'].append(request.sid)
    join_room(room_id)

    emit("user_joined", {"user_id": user_id}, room=room_id)
    emit("room_update", {
        "room_id": room_id,
        "users": rooms[room_id]['users']
    }, room=room_id)
    logger.info(f"User {user_id} joined room {room_id}")

@socketio.on("offer")
def handle_offer(data):
    room_id = data.get('room_id')
    if room_id not in rooms:
        return
    emit("offer", {
        "offer": data['offer'],
        "sender_id": request.sid
    }, room=room_id, skip_sid=request.sid)

@socketio.on("answer")
def handle_answer(data):
    room_id = data.get('room_id')
    if room_id not in rooms:
        return
    emit("answer", {
        "answer": data['answer'],
        "sender_id": request.sid
    }, room=room_id, skip_sid=request.sid)

@socketio.on("ice_candidate")
def handle_ice_candidate(data):
    room_id = data.get('room_id')
    if room_id not in rooms:
        return
    emit("ice_candidate", {
        "candidate": data['candidate'],
        "sender_id": request.sid
    }, room=room_id, skip_sid=request.sid)

@socketio.on("audio_blob")
def handle_audio_blob(data):
    try:
        room_id = data.get('room_id')
        if room_id not in rooms:
            return

        audio_array = np.frombuffer(data['audio'], dtype=np.float32)
        audio_data = AudioData(audio_array.tobytes(), sample_rate=44100, sample_width=4)

        text = recognizer.recognize_google(audio_data)

        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'es')

        translated = translator(text, src_lang=source_lang, tgt_lang=target_lang)[0]['translation_text']

        emit("translation_result", {
            "original": text,
            "translated": translated,
            "source_lang": source_lang,
            "target_lang": target_lang
        }, room=room_id)

        logger.info(f"Translated in room {room_id}: {text} -> {translated}")

    except Exception as e:
        logger.error(f"Audio processing error: {str(e)}")
        emit("translation_error", {"error": str(e)}, room=data.get('room_id'))

@socketio.on("process_ocr")
def handle_process_ocr(data):
    try:
        room_id = data.get('room_id')
        if room_id not in rooms:
            return

        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))

        text = pytesseract.image_to_string(image)

        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'es')

        translated = translator(text, src_lang=source_lang, tgt_lang=target_lang)[0]['translation_text']

        width, height = image.size
        x, y = width // 2, height // 2

        emit("ocr_result", {
            "original": text,
            "translated": translated,
            "x": x,
            "y": y,
            "source_lang": source_lang,
            "target_lang": target_lang
        }, room=room_id)

        logger.info(f"OCR processed in room {room_id}: {text} -> {translated}")

    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        emit("ocr_error", {"error": str(e)}, room=data.get('room_id'))

# Start server using Render-compatible config
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app,
                 host="0.0.0.0",
                 port=port,
                 debug=False,
                 use_reloader=False,
                 log_output=True)
