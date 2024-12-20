from flask import Flask, request, render_template, send_from_directory, jsonify
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = app.logger

# Configuration
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
logger.info(f"Upload folder path: {UPLOAD_FOLDER}")

if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        logger.info(f"Created upload directory at {UPLOAD_FOLDER}")
    except Exception as e:
        logger.error(f"Failed to create upload directory: {e}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB max-size

# For production behind a proxy
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

@app.route('/')
@app.route('/dl')  # Add additional route for /dl path
def index():
    try:
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                size = os.path.getsize(file_path)
                upload_time = datetime.fromtimestamp(os.path.getctime(file_path))
                files.append({
                    'name': filename,
                    'size': size,
                    'upload_time': upload_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.error(f"Error processing file {filename}: {e}")
        return render_template('index.html', files=files)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "Error loading files", 500

# Ensure upload endpoint works from any path
@app.route('/upload', methods=['POST'])
@app.route('/dl/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("Upload request received")
        logger.debug(f"Files in request: {request.files}")
        logger.debug(f"Request headers: {request.headers}")

        if not request.files:
            logger.error("No files in request")
            return jsonify({'success': False, 'message': 'No files provided'}), 400

        uploaded_files = []
        for key, file in request.files.items():
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    logger.info(f"Processing file: {filename}")
                    
                    # Ensure upload directory exists
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                        logger.info("Created upload directory")
                    
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logger.debug(f"Saving file to: {file_path}")
                    
                    # Test write permissions
                    try:
                        with open(file_path, 'wb') as test_file:
                            test_file.write(b'test')
                        os.remove(file_path)
                        logger.info("Write permission test successful")
                    except Exception as e:
                        logger.error(f"Write permission test failed: {e}")
                        return jsonify({'success': False, 'message': f'Server write permission error: {str(e)}'}), 500
                    
                    # Save the actual file
                    file.save(file_path)
                    uploaded_files.append(filename)
                    logger.info(f"Successfully saved file: {filename}")
                except Exception as e:
                    logger.error(f"Error saving file {filename}: {e}")
                    return jsonify({'success': False, 'message': f'Error saving file {filename}: {str(e)}'}), 500

        if uploaded_files:
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {len(uploaded_files)} files',
                'files': uploaded_files
            })
        else:
            return jsonify({'success': False, 'message': 'No valid files uploaded'}), 400

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error for {filename}: {e}")
        return f"Error downloading file: {str(e)}", 404

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
