from flask import Flask, request, render_template, send_from_directory, jsonify, url_for
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = app.logger

# Configuration
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB max-size

# Define URL prefix - important for deployment
URL_PREFIX = '/dl'

@app.route(URL_PREFIX + '/')
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
        return render_template('index.html', files=files, url_prefix=URL_PREFIX)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "Error loading files", 500

@app.route(URL_PREFIX + '/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("Upload request received")
        logger.info(f"Request path: {request.path}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Files in request: {list(request.files.keys())}")

        if not request.files:
            logger.error("No files in request")
            return jsonify({'success': False, 'message': 'No files provided'}), 400

        uploaded_files = []
        for key, file in request.files.items():
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    uploaded_files.append(filename)
                    logger.info(f"Successfully saved file: {filename}")
                except Exception as e:
                    logger.error(f"Error saving file {filename}: {e}")
                    return jsonify({'success': False, 'message': f'Error saving file {filename}: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_files)} files',
            'files': uploaded_files
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route(URL_PREFIX + '/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Download error for {filename}: {e}")
        return f"Error downloading file: {str(e)}", 404

# Redirect root to /dl/
@app.route('/')
def root():
    return redirect(URL_PREFIX + '/')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
