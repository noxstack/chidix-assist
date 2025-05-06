@socketio.on("webrtc_signal")
def handle_webrtc_signal(data):
    """
    Enhanced WebRTC signaling handler with validation and error handling.
    Forwards signals between peers and maintains connection state.
    """
    try:
        # Validate incoming data
        if not all(key in data for key in ['type', 'target_user', 'room_id']):
            raise ValueError("Missing required signal fields")
            
        signal_type = data['type']
        target_user = data['target_user']
        room_id = data['room_id']
        sender_id = request.sid
        
        # Log the signal (debugging purposes)
        logger.debug(
            f"WebRTC signal received - Type: {signal_type}, "
            f"From: {sender_id}, To: {target_user}, Room: {room_id}"
        )
        
        # Validate room membership
        if room_id not in rooms:
            raise ValueError(f"Room {room_id} does not exist")
            
        if sender_id not in rooms[room_id]['sids']:
            raise ValueError(f"Sender {sender_id} not in room {room_id}")
            
        if target_user not in rooms[room_id]['sids']:
            raise ValueError(f"Target user {target_user} not in room {room_id}")

        # Validate signal type
        valid_signal_types = ['offer', 'answer', 'ice_candidate']
        if signal_type not in valid_signal_types:
            raise ValueError(f"Invalid signal type: {signal_type}")

        # Additional validation for specific signal types
        if signal_type == 'offer' and 'sdp' not in data:
            raise ValueError("Offer missing SDP")
            
        if signal_type == 'answer' and 'sdp' not in data:
            raise ValueError("Answer missing SDP")
            
        if signal_type == 'ice_candidate' and 'candidate' not in data:
            raise ValueError("ICE candidate missing candidate data")

        # Prepare the forwarded signal
        forwarded_signal = {
            'type': signal_type,
            'sender_id': sender_id,
            'room_id': room_id,
            **{k: v for k, v in data.items() if k not in ['type', 'target_user']}
        }

        # Forward to target user
        emit("webrtc_signal", forwarded_signal, room=target_user)
        logger.debug(f"Forwarded {signal_type} to {target_user}")

        # Send acknowledgement to sender
        emit("signal_ack", {
            'status': 'success',
            'type': signal_type,
            'timestamp': datetime.now().isoformat()
        }, room=sender_id)

    except ValueError as ve:
        error_msg = f"WebRTC signal validation failed: {str(ve)}"
        logger.error(error_msg)
        emit("signal_error", {
            'error': error_msg,
            'original_signal': data
        }, room=sender_id)
        
    except Exception as e:
        error_msg = f"Unexpected error processing WebRTC signal: {str(e)}"
        logger.error(error_msg, exc_info=True)
        emit("signal_error", {
            'error': "Internal server error",
            'original_signal': data
        }, room=sender_id)