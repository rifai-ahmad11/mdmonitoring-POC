from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import threading
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# Thread-safe data storage
data_store = {}
next_id = 1
data_lock = threading.Lock()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/urine-data', methods=['POST'])
def receive_data():
    global next_id
    try:
        data = request.json
        
        # Validasi struktur dasar
        required_fields = ['results', 'abnormal_flags']
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': 'Data tidak valid: hasil atau flag abnormal tidak ada'
            }), 400
            
        # Validasi format tanggal
        if 'date_time' not in data:
            data['date_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            try:
                datetime.strptime(data['date_time'], "%Y-%m-%d %H:%M")
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD HH:MM'
                }), 400
        
        with data_lock:
            # Generate ID dan simpan data
            data_id = str(next_id)
            data['id'] = data_id
            data['sample_no'] = data.get('sample_no', "N/A")
            data['patient_id'] = data.get('patient_id', "")
            
            data_store[data_id] = data
            next_id += 1
            
            # Kirim update real-time
            socketio.emit('new_data', {
                'id': data_id,
                'data': data,
                'type': 'new'
            })
            
        return jsonify({
            'status': 'success',
            'id': data_id,
            'timestamp': data['date_time']
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Kesalahan server: {str(e)}'
        }), 500

@app.route('/urine-data/<data_id>', methods=['GET'])
def get_single_data(data_id):
    with data_lock:
        data = data_store.get(data_id)
        if data:
            return jsonify({'status': 'success', 'data': data}), 200
        return jsonify({'status': 'error', 'message': 'Data tidak ditemukan'}), 404

@app.route('/api/all-data', methods=['GET'])
def get_all_data():
    with data_lock:
        return jsonify({
            'status': 'success',
            'count': len(data_store),
            'data': data_store
        }), 200

@app.route('/api/manual-input', methods=['POST'])
def manual_input():
    """Endpoint untuk testing tanpa alat fisik"""
    global next_id
    try:
        # Generate sample data
        sample_data = {
            "date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sample_no": f"TEST-{next_id:03d}",
            "patient_id": "SAMPLE-DATA",
            "results": {
                "ubg": "Normal 3.4umol/L",
                "bil": "Neg",
                "ket": "Neg",
                "bld": "1+ Ca25 Ery/uL",
                "pro": "Trace",
                "nit": "Pos",
                "leu": "Neg",
                "glu": "Neg",
                "sg": ">=1.030",
                "ph": "5.5"
            },
            "abnormal_flags": {
                "bld": True,
                "pro": True,
                "nit": True,
                "leu": False,
                "glu": False
            }
        }

        with data_lock:
            data_id = str(next_id)
            sample_data['id'] = data_id
            data_store[data_id] = sample_data
            next_id += 1

            socketio.emit('new_data', {
                'id': data_id,
                'data': sample_data,
                'type': 'new'
            })

        return jsonify({
            'status': 'success',
            'id': data_id,
            'timestamp': sample_data['date_time']
        }), 201

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Kesalahan server: {str(e)}'
        }), 500

if __name__ == '__main__':
    socketio.run(
        app,
        host='0.0.0.0',
        port=8080,
        debug=True,
        allow_unsafe_werkzeug=True
    )

