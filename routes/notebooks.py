"""
Notebooks Routes - Jupyter Notebook Import/Export API Endpoints
================================================================
Flask blueprint for notebook file operations.
"""

import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename


# Create blueprint
bp = Blueprint('notebooks', __name__)


@bp.route('/upload', methods=['POST'])
def upload_notebook():
    """Upload and import a Jupyter notebook file."""
    file = request.files.get('file')
    if file is None or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400
    if not file.filename.endswith('.ipynb'):
        return jsonify({'error': 'File must be .ipynb format'}), 400

    try:
        try:
            import nbformat
        except ImportError:
            return jsonify({'error': '需要安装 nbformat 才能导入 .ipynb 文件'}), 400

        raw = file.read().decode('utf-8', errors='ignore')
        nb = nbformat.reads(raw, as_version=4)
        cells = []
        for cell in nb.cells:
            if cell.cell_type not in ('code', 'markdown'):
                continue
            source = cell.source
            cells.append({
                'cell_type': cell.cell_type,
                'source': source,
                'outputs': []
            })
        return jsonify({'cells': cells, 'filename': file.filename})
    except Exception as e:
        logging.error(f"Notebook upload failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/list', methods=['GET'])
def list_notebooks():
    """List available notebook files."""
    try:
        files = []
        for name in os.listdir(bp.state.notebook_root):
            if name.endswith('.ipynb') and os.path.isfile(os.path.join(bp.state.notebook_root, name)):
                files.append(name)
        files.sort()
        return jsonify({'files': files, 'root': bp.state.notebook_root})
    except Exception as e:
        logging.error(f"Notebook list failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/open', methods=['POST'])
def open_notebook():
    """Open an existing notebook file."""
    data = request.json if request.json else {}
    filename = data.get('filename', '')
    if not filename or not filename.endswith('.ipynb'):
        return jsonify({'error': 'Invalid filename'}), 400
    safe_name = secure_filename(filename)
    notebook_path = os.path.abspath(os.path.join(bp.state.notebook_root, safe_name))
    if not notebook_path.startswith(os.path.abspath(bp.state.notebook_root) + os.sep):
        return jsonify({'error': 'Invalid path'}), 400
    if not os.path.exists(notebook_path):
        return jsonify({'error': 'Notebook not found'}), 404

    try:
        try:
            import nbformat
        except ImportError:
            return jsonify({'error': '需要安装 nbformat 才能导入 .ipynb 文件'}), 400

        with open(notebook_path, 'r', encoding='utf-8', errors='ignore') as handle:
            nb = nbformat.read(handle, as_version=4)
            cells = []
            for cell in nb.cells:
                if cell.cell_type not in ('code', 'markdown'):
                    continue
                cells.append({
                    'cell_type': cell.cell_type,
                    'source': cell.source,
                    'outputs': []
                })
            return jsonify({'cells': cells, 'filename': filename})
    except Exception as e:
        logging.error(f"Notebook open failed: {e}")
        return jsonify({'error': str(e)}), 500


# Initialize blueprint with dependencies (will be set by app.py)
bp.state = None
