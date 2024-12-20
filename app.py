from flask import Flask, request, render_template, jsonify
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024 * 1024  # 16GB max-size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar', '7z'}

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        app.logger.info('Upload request received')
        app.logger.debug(f'Files: {request.files}')
        app.logger.debug(f'Form: {request.form}')

        # Handle Dropzone's file parameter name
        if 'file' not in request.files:
            for key in request.files:
                if key.startswith('file'):
                    file = request.files[key]
                    break
            else:
                app.logger.error('No file found in request')
                return jsonify({'error': 'No file provided'}), 400
        else:
            file = request.files['file']
        
        notes = request.form.get('notes', '')
        
        # If user submits without selecting a file
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and allowed_file(file.filename):
            # Secure the filename and add timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{secure_filename(file.filename)}"
            
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Save notes if provided (in this example, we'll save them in a txt file)
            if notes:
                notes_filename = f"{timestamp}_{secure_filename(file.filename)}_notes.txt"
                notes_path = os.path.join(app.config['UPLOAD_FOLDER'], notes_filename)
                with open(notes_path, 'w') as f:
                    f.write(notes)
            
            return jsonify({
                'success': True,
                'message': 'File uploaded successfully',
                'filename': filename,
                'notes_saved': bool(notes)
            })
        else:
            return jsonify({'error': 'File type not allowed'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-status', methods=['GET'])
def get_upload_status():
    # Get the list of files in the upload directory
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if not filename.endswith('_notes.txt'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            size = os.path.getsize(file_path)
            upload_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            # Check if notes exist for this file
            notes_filename = f"{filename}_notes.txt"
            notes_path = os.path.join(app.config['UPLOAD_FOLDER'], notes_filename)
            notes = None
            if os.path.exists(notes_path):
                with open(notes_path, 'r') as f:
                    notes = f.read()
            
            files.append({
                'filename': filename,
                'size': size,
                'upload_time': upload_time.strftime('%Y-%m-%d %H:%M:%S'),
                'notes': notes
            })
    
    return jsonify({'files': files})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
