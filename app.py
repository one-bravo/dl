from flask import Flask, request, render_template, send_from_directory, jsonify, redirect
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
import sys
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Set up logging to stdout for DigitalOcean
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

# Configuration
try:
    # For DigitalOcean, use /tmp directory for uploads
    UPLOAD_FOLDER = '/tmp/uploads'
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.logger.info(f"Using upload folder: {UPLOAD_FOLDER}")
except Exception as e:
    app.logger.error(f"Error setting up upload folder: {e}")
    # Fallback to current directory
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.logger.info(f"Using fallback upload folder: {UPLOAD_FOLDER}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB max-size

@app.route('/')
def root():
    return redirect('/dl/')

@app.route('/dl/')
def index():
    try:
        app.logger.info("Loading index page")
        files = []
        
        # Check if upload directory exists
        if not os.path.exists(UPLOAD_FOLDER):
            app.logger.warning("Upload folder doesn't exist, creating it")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(UPLOAD_FOLDER, 'test.txt')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            app.logger.info("Write permission test successful")
        except Exception as e:
            app.logger.error(f"Write permission test failed: {e}")
            return render_template('index.html', 
                                files=[], 
                                error="Server configuration error: No write permissions")
        
        # List files
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                try:
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        upload_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        files.append({
                            'name': filename,
                            'size': size,
                            'upload_time': upload_time.strftime('%Y-%m-%d %H:%M:%S')
                        })
                except Exception as e:
                    app.logger.error(f"Error processing file {filename}: {e}")
                    continue
        
        app.logger.info(f"Found {len(files)} files")
        return render_template('index.html', files=files)
    
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', 
                             files=[], 
                             error=f"Server error: {str(e)}")

@app.route('/dl/upload', methods=['POST'])
def upload_file():
    try:
        app.logger.info("Upload request received")
        if not request.files:
            app.logger.warning("No files in request")
            return jsonify({'success': False, 'message': 'No files provided'}), 400

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        uploaded_files = []
        for key, file in request.files.items():
            if file and file.filename:
                try:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    app.logger.info(f"Saving file to {file_path}")
                    file.save(file_path)
                    uploaded_files.append(filename)
                    app.logger.info(f"Successfully saved file: {filename}")
                except Exception as e:
                    app.logger.error(f"Error saving file {filename}: {e}")
                    return jsonify({
                        'success': False,
                        'message': f'Error saving file {filename}: {str(e)}'
                    }), 500

        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_files)} files',
            'files': uploaded_files
        })

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/dl/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Download error for {filename}: {e}")
        return f"Error downloading file: {str(e)}", 404

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
