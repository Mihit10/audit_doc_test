import os
import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from processing.processor import process
from processing.report_generator import generate_report

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports', 'dcb')
PHOTOS_DIR = os.path.join(REPORTS_DIR, 'photos')

os.makedirs(PHOTOS_DIR, exist_ok=True)

@app.route('/api/audits/add-and-generate', methods=['POST'])
def add_and_generate():
    try:
        # Generate a simulated audit_id to group photos
        audit_id = str(uuid.uuid4())
        
        # We only care about form data in this isolated environment
        data = request.form.to_dict()
        
        photo_metadata = request.form.get('photo_metadata')
        if photo_metadata:
            # Create a dedicated directory for this request's photos
            audit_photos_dir = os.path.join(PHOTOS_DIR, audit_id)
            os.makedirs(audit_photos_dir, exist_ok=True)
            
            # Save metadata for debugging/logging purposes
            with open(os.path.join(audit_photos_dir, 'metadata.json'), 'w') as f:
                f.write(photo_metadata)
                
            # Save files
            for file in request.files.getlist('photo_files'):
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(audit_photos_dir, filename))
            
            # Pass the metadata and directory to the processor
            data['photo_metadata'] = json.loads(photo_metadata)
            data['photo_dir'] = audit_photos_dir

        # Process the metadata (attach recommendations, format for template)
        processed = process(data)

        # Generate DOCX report
        report_path = generate_report(processed)

        return jsonify({
            "message": "Report generated successfully",
            "audit_id": audit_id,
            "report_path": report_path
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
