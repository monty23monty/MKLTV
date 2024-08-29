from flask_socketio import emit

from config import db, socketio, app


@socketio.on('clock_event')
def handle_clock_event(data):
    emit('update_clock', data, broadcast=True)

# Function to emit score, period, or SOG updates
@socketio.on('update_event')
def handle_update_event(data):
    emit('update_value', data, broadcast=True)