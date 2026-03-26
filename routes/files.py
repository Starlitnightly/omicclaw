"""
Files Routes - File Management API Endpoints
=============================================
Flask blueprint for file system operations.
"""

import logging
import base64
import mimetypes
import shutil
from pathlib import Path
from flask import Blueprint, request, jsonify

from utils.file_helpers import (
    resolve_browse_path,
    is_allowed_text_file,
    is_image_file,
)


# Create blueprint
bp = Blueprint('files', __name__)


def _is_desktop_app_path(path: Path) -> bool:
    normalized = str(path.resolve()).replace('\\', '/').lower()
    return ".app/contents/" in normalized or normalized.endswith(".app")


def _default_absolute_browser_root(file_root: Path) -> Path:
    launch_root = Path(file_root).resolve()
    if _is_desktop_app_path(launch_root):
        return Path.home().resolve()
    return launch_root


@bp.route('/list', methods=['GET'])
def list_files():
    """List files and directories at given path."""
    rel_path = request.args.get('path', '')
    try:
        target = resolve_browse_path(bp.file_root, rel_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if not target.exists() or not target.is_dir():
        return jsonify({'error': 'Directory not found'}), 404

    entries = []
    for entry in target.iterdir():
        try:
            item = {
                'name': entry.name,
                'type': 'dir' if entry.is_dir() else 'file',
                'size': entry.stat().st_size if entry.is_file() else None,
                'ext': entry.suffix.lower() if entry.is_file() else None
            }
            entries.append(item)
        except Exception:
            continue

    entries.sort(key=lambda x: (0 if x['type'] == 'dir' else 1, x['name'].lower()))
    if target == bp.file_root:
        rel, parent = '', ''
    else:
        rel = str(target.relative_to(bp.file_root))
        p = target.parent
        # When parent IS file_root, relative_to() returns '.' — normalise to ''
        parent = '' if p == bp.file_root else str(p.relative_to(bp.file_root))

    return jsonify({
        'path': rel,
        'parent': parent,
        'entries': entries,
        'root_abs': str(bp.file_root),          # absolute server root (for display)
        'current_abs': str(target),              # absolute current dir (for display)
    })


@bp.route('/list_abs', methods=['GET'])
def list_files_abs():
    """List files at an absolute path (no file_root restriction). Used by the server file browser modal."""
    abs_path = request.args.get('abspath', '').strip()
    if abs_path:
        target = Path(abs_path).resolve()
    else:
        target = _default_absolute_browser_root(bp.file_root)

    if not target.exists() or not target.is_dir():
        return jsonify({'error': 'Directory not found'}), 404

    entries = []
    try:
        for entry in target.iterdir():
            try:
                entries.append({
                    'name': entry.name,
                    'type': 'dir' if entry.is_dir() else 'file',
                    'size': entry.stat().st_size if entry.is_file() else None,
                    'ext': entry.suffix.lower() if entry.is_file() else None,
                })
            except Exception:
                continue
    except PermissionError:
        return jsonify({'error': 'Permission denied'}), 403

    entries.sort(key=lambda x: (0 if x['type'] == 'dir' else 1, x['name'].lower()))

    parent = target.parent
    is_fs_root = (target == parent)  # True when already at filesystem root

    return jsonify({
        'current_abs': str(target),
        'parent_abs': '' if is_fs_root else str(parent),
        'file_root_abs': str(bp.file_root),
        'user_home_abs': str(Path.home().resolve()),
        'is_fs_root': is_fs_root,
        'entries': entries,
    })


@bp.route('/open', methods=['POST'])
def open_file():
    """Open a file and return its contents."""
    data = request.json if request.json else {}
    rel_path = data.get('path', '')
    try:
        target = resolve_browse_path(bp.file_root, rel_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if not target.exists() or not target.is_file():
        return jsonify({'error': 'File not found'}), 404

    try:
        # Handle Jupyter notebooks
        if target.suffix.lower() == '.ipynb':
            try:
                import nbformat
            except ImportError:
                return jsonify({'error': '需要安装 nbformat 才能导入 .ipynb 文件'}), 400

            with open(target, 'r', encoding='utf-8', errors='ignore') as handle:
                raw = handle.read()

            if not raw.strip():
                nb = nbformat.v4.new_notebook()
                nb.cells = [nbformat.v4.new_code_cell(source='')]
                with open(target, 'w', encoding='utf-8') as handle:
                    nbformat.write(nb, handle)
            else:
                nb = nbformat.reads(raw, as_version=4)

            cells = []
            for cell in nb.cells:
                if cell.cell_type not in ('code', 'markdown'):
                    continue
                source = cell.source
                if isinstance(source, list):
                    source = ''.join(source)
                outputs = []
                if cell.cell_type == 'code':
                    for output in cell.get('outputs', []):
                        outputs.append(output)
                cells.append({
                    'cell_type': cell.cell_type,
                    'source': source,
                    'outputs': outputs
                })

            return jsonify({
                'type': 'notebook',
                'name': target.name,
                'path': str(target.relative_to(bp.file_root)),
                'cells': cells
            })

        # Handle image files
        if is_image_file(target):
            mime_type = mimetypes.guess_type(target.name)[0] or 'image/png'
            with open(target, 'rb') as handle:
                encoded = base64.b64encode(handle.read()).decode('ascii')
            return jsonify({
                'type': 'image',
                'name': target.name,
                'path': str(target.relative_to(bp.file_root)),
                'mime': mime_type,
                'content': encoded
            })

        # Handle text files
        if not is_allowed_text_file(target):
            return jsonify({'error': 'Unsupported file type'}), 400

        with open(target, 'r', encoding='utf-8', errors='ignore') as handle:
            content = handle.read()

        return jsonify({
            'type': 'text',
            'name': target.name,
            'path': str(target.relative_to(bp.file_root)),
            'ext': target.suffix.lower(),
            'content': content
        })

    except Exception as e:
        logging.error(f"File open failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/save', methods=['POST'])
def save_file():
    """Save file contents."""
    data = request.json if request.json else {}
    rel_path = data.get('path', '')
    file_type = data.get('type', '')

    try:
        target = resolve_browse_path(bp.file_root, rel_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    try:
        # Handle notebook files
        if file_type == 'notebook':
            if target.suffix.lower() != '.ipynb':
                return jsonify({'error': 'Notebook must be .ipynb'}), 400

            try:
                import nbformat
            except ImportError:
                return jsonify({'error': '需要安装 nbformat 才能保存 .ipynb 文件'}), 400

            cells_payload = data.get('cells', [])
            nb = nbformat.v4.new_notebook()
            nb_cells = []

            for cell in cells_payload:
                cell_type = cell.get('cell_type', 'code')
                source = cell.get('source', '')
                outputs = cell.get('outputs', []) if isinstance(cell.get('outputs', []), list) else []

                nb_outputs = []
                for output in outputs:
                    try:
                        nb_outputs.append(nbformat.from_dict(output))
                    except Exception:
                        continue

                if cell_type == 'markdown':
                    nb_cells.append(nbformat.v4.new_markdown_cell(source=source))
                elif cell_type == 'raw':
                    nb_cells.append(nbformat.v4.new_raw_cell(source=source))
                else:
                    nb_cells.append(nbformat.v4.new_code_cell(
                        source=source,
                        outputs=nb_outputs,
                        execution_count=None
                    ))

            nb.cells = nb_cells
            with open(target, 'w', encoding='utf-8') as handle:
                nbformat.write(nb, handle)
            return jsonify({'success': True})

        # Handle text files
        if file_type == 'text':
            if not is_allowed_text_file(target):
                return jsonify({'error': 'Unsupported file type'}), 400

            content = data.get('content', '')
            with open(target, 'w', encoding='utf-8') as handle:
                handle.write(content)
            return jsonify({'success': True})

        return jsonify({'error': 'Invalid file type'}), 400

    except Exception as e:
        logging.error(f"File save failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/create', methods=['POST'])
def create_file_or_folder():
    """Create a new file or folder."""
    data = request.json if request.json else {}
    rel_path = data.get('path', '')
    item_type = data.get('type', 'file')

    try:
        target = resolve_browse_path(bp.file_root, rel_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if target.exists():
        return jsonify({'error': 'Path already exists'}), 400

    try:
        if item_type == 'folder':
            target.mkdir(parents=True, exist_ok=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=False)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Create failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/delete', methods=['POST'])
def delete_file_or_folder():
    """Delete a file or folder."""
    data = request.json if request.json else {}
    rel_path = data.get('path', '')

    try:
        target = resolve_browse_path(bp.file_root, rel_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if not target.exists():
        return jsonify({'error': 'Path not found'}), 404

    if target == bp.file_root or str(target).startswith(str(bp.file_root / '.')):
        return jsonify({'error': 'Refusing to delete'}), 400

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Delete failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/rename', methods=['POST'])
def rename_file_or_folder():
    """Rename a file or folder."""
    data = request.json if request.json else {}
    src_path = data.get('src', '')
    dst_path = data.get('dst', '')

    try:
        src = resolve_browse_path(bp.file_root, src_path)
        dst = resolve_browse_path(bp.file_root, dst_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if not src.exists():
        return jsonify({'error': 'Source not found'}), 404
    if dst.exists():
        return jsonify({'error': 'Target exists'}), 400

    try:
        src.rename(dst)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Rename failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/copy', methods=['POST'])
def copy_file_or_folder():
    """Copy a file or folder."""
    data = request.json if request.json else {}
    src_path = data.get('src', '')
    dst_path = data.get('dst', '')

    try:
        src = resolve_browse_path(bp.file_root, src_path)
        dst = resolve_browse_path(bp.file_root, dst_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if not src.exists():
        return jsonify({'error': 'Source not found'}), 404
    if dst.exists():
        return jsonify({'error': 'Target exists'}), 400

    try:
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Copy failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/move', methods=['POST'])
def move_file_or_folder():
    """Move a file or folder."""
    data = request.json if request.json else {}
    src_path = data.get('src', '')
    dst_path = data.get('dst', '')

    try:
        src = resolve_browse_path(bp.file_root, src_path)
        dst = resolve_browse_path(bp.file_root, dst_path)
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 400

    if not src.exists():
        return jsonify({'error': 'Source not found'}), 404
    if dst.exists():
        return jsonify({'error': 'Target exists'}), 400

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Move failed: {e}")
        return jsonify({'error': str(e)}), 500


# Initialize blueprint with dependencies (will be set by app.py)
bp.file_root = None
