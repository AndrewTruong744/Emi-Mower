from firebase_admin import auth as firebase_auth

from src.config.socketio import logger, sio

# Figure out how to handle mower socket connections and authentication.
# The mower will need to authenticate with Firebase as well,
# but it might use a different method (like a service account or a pre-shared token).
# For now, we'll focus on the user connection.

@sio.event
async def connect(sid, environ, auth=None):
    if not auth or 'token' not in auth:
        logger.warning(f"Connection refused for {sid}: No token provided.")
        return False # Returning False rejects the connection automatically

    try:
        # Verify the Firebase token sent from the client
        id_token = auth['token']
        decoded_token = firebase_auth.verify_id_token(id_token)

        # You now have the verified user's details!
        uid = decoded_token['uid']
        logger.info(f"Firebase User {uid} successfully authenticated on sid: {sid}")

        # Save user data into the socket session for later use
        await sio.save_session(sid, {'user_id': uid})

        await sio.join_room(sid, room=uid)

    except Exception as e:
        logger.warning(f"Connection refused: Invalid Firebase token. {e}")
        return False

    await sio.emit("welcome", {"message": "Connected!", "sid": sid}, to=sid)
