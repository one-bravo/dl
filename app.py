from flask import Flask, request, render_template, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB max-size

@app.route('/')
def index():
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        size = os.path.getsize(file_path)
        upload_time = datetime.fromtimestamp(os.path.getctime(file_path))
        files.append({
            'name': filename,
            'size': size,
            'upload_time': upload_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        uploaded_files = []
        for key, file in request.files.items():
            if key.startswith('file'):
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    uploaded_files.append(filename)
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_files)} files',
            'files': uploaded_files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
