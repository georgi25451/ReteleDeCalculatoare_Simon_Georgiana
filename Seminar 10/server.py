import socket
import json
import os
import threading
from datetime import datetime

# Configuration
SERVER_HOST = 'localhost'
SERVER_PORT = 5000
FILES_DIR = 'files'
DEFAULT_USER = 'student'
DEFAULT_PASSWORD = '1234'

history_lock = threading.Lock()
operation_history = {}


def ensure_files_dir():
    """Ensure files directory exists"""
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"✓ Directory '{FILES_DIR}' created")


def authenticate(username, password):
    """Authenticate user"""
    return username == DEFAULT_USER and password == DEFAULT_PASSWORD


def normalize_filename(filename):
    """Validate and normalize a filename so clients cannot access paths outside FILES_DIR."""
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError('Invalid filename')

    filename = filename.strip()

    if '/' in filename or '\\' in filename or filename in ('.', '..') or '..' in filename:
        raise ValueError('Invalid filename. Use only the file name, without folders')

    return filename


def get_file_path(filename):
    """Return the full safe path for a file from FILES_DIR."""
    safe_name = normalize_filename(filename)
    return os.path.join(FILES_DIR, safe_name)


def add_history(filename, operation, user, details=''):
    """Add an operation to a file's history on the server."""
    safe_name = normalize_filename(filename)
    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'operation': operation,
        'user': user or 'unknown',
        'details': details
    }

    with history_lock:
        operation_history.setdefault(safe_name, []).append(entry)


def rename_history(old_name, new_name, user):
    """Move a file history from the old name to the new name and record the rename."""
    old_name = normalize_filename(old_name)
    new_name = normalize_filename(new_name)
    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'operation': 'rename',
        'user': user or 'unknown',
        'details': f'Renamed from {old_name} to {new_name}'
    }

    with history_lock:
        old_history = operation_history.pop(old_name, [])
        old_history.append(entry)
        operation_history[new_name] = old_history


def format_history(filename):
    """Return a readable history message for a file."""
    safe_name = normalize_filename(filename)

    with history_lock:
        entries = operation_history.get(safe_name, [])

    if not entries:
        return f"No operation history found for '{safe_name}'."

    lines = [f"Operation history for '{safe_name}':"]
    for index, entry in enumerate(entries, 1):
        details = entry.get('details', '')
        detail_text = f" - {details}" if details else ''
        lines.append(
            f"{index}. [{entry.get('timestamp', 'unknown')}] "
            f"{entry.get('operation', 'unknown')} by {entry.get('user', 'unknown')}"
            f"{detail_text}"
        )

    return '\n'.join(lines)


def get_server_files():
    """Return only regular files from the server files directory."""
    ensure_files_dir()
    return sorted([
        file_name for file_name in os.listdir(FILES_DIR)
        if os.path.isfile(os.path.join(FILES_DIR, file_name))
    ])


def handle_client(conn, addr):
    """Handle client connection"""
    print(f"\n🔗 Client connected from {addr}")
    authenticated = False
    current_user = None

    try:
        while True:
            # Receive request
            request_data = conn.recv(4096).decode('utf-8')
            if not request_data:
                break

            try:
                request = json.loads(request_data)
                command = request.get('command')

                print(f"📨 Command received: {command}")

                # Authentication
                if command == 'login':
                    username = request.get('username')
                    password = request.get('password')

                    if authenticate(username, password):
                        authenticated = True
                        current_user = username
                        response = {'status': 'success', 'message': f'Welcome {username}!'}
                        print(f"✓ User {username} authenticated")
                    else:
                        response = {'status': 'error', 'message': 'Invalid credentials'}
                        print(f"✗ Authentication failed for user {username}")

                elif not authenticated:
                    response = {'status': 'error', 'message': 'Not authenticated. Use login first'}

                # File operations
                elif command == 'create_file':
                    filename = normalize_filename(request.get('filename'))
                    content = request.get('content', '')

                    filepath = get_file_path(filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)

                    add_history(filename, 'create', current_user, 'File created on server')
                    response = {'status': 'success', 'message': f'File {filename} created on server'}
                    print(f"✓ File created: {filename}")

                elif command == 'upload':
                    filename = normalize_filename(request.get('filename'))
                    content = request.get('content', '')

                    filepath = get_file_path(filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)

                    add_history(filename, 'upload', current_user, 'File uploaded from client')
                    response = {'status': 'success', 'message': f'File {filename} uploaded'}
                    print(f"✓ File uploaded: {filename}")

                elif command == 'rename_file':
                    old_name = normalize_filename(request.get('old_name'))
                    new_name = normalize_filename(request.get('new_name'))

                    old_path = get_file_path(old_name)
                    new_path = get_file_path(new_name)

                    if not os.path.exists(old_path):
                        response = {'status': 'error', 'message': f"File '{old_name}' does not exist"}
                    elif os.path.exists(new_path):
                        response = {'status': 'error', 'message': f"File '{new_name}' already exists"}
                    else:
                        os.rename(old_path, new_path)
                        rename_history(old_name, new_name, current_user)
                        response = {
                            'status': 'success',
                            'message': f"File renamed from '{old_name}' to '{new_name}'"
                        }
                        print(f"✓ File renamed: {old_name} -> {new_name}")

                elif command == 'read_file':
                    filename = normalize_filename(request.get('filename'))
                    filepath = get_file_path(filename)

                    if not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f"File '{filename}' does not exist"}
                    else:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        add_history(filename, 'read', current_user, 'File content read from client')
                        response = {
                            'status': 'success',
                            'message': f"File '{filename}' read successfully",
                            'filename': filename,
                            'content': content
                        }
                        print(f"✓ File read: {filename}")

                elif command == 'download':
                    filename = normalize_filename(request.get('filename'))
                    filepath = get_file_path(filename)

                    if not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f"File '{filename}' does not exist"}
                    else:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()

                        add_history(filename, 'download', current_user, 'File downloaded by client')
                        response = {
                            'status': 'success',
                            'message': f"File '{filename}' downloaded successfully",
                            'filename': filename,
                            'content': content
                        }
                        print(f"✓ File downloaded: {filename}")

                elif command == 'edit_file':
                    filename = normalize_filename(request.get('filename'))
                    content = request.get('content', '')
                    filepath = get_file_path(filename)

                    if not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f"File '{filename}' does not exist"}
                    else:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)

                        add_history(filename, 'edit', current_user, 'File content replaced')
                        response = {'status': 'success', 'message': f"File '{filename}' edited successfully"}
                        print(f"✓ File edited: {filename}")

                elif command == 'see_file_operation_history':
                    filename = normalize_filename(request.get('filename'))
                    filepath = get_file_path(filename)

                    if not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f"File '{filename}' does not exist"}
                    else:
                        history_message = format_history(filename)
                        response = {'status': 'success', 'message': history_message}
                        print(f"✓ History displayed for: {filename}")

                elif command == 'list_files':
                    files = get_server_files()
                    response = {'status': 'success', 'files': files}
                    print(f"✓ Files listed: {len(files)} files found")

                elif command == 'logout':
                    authenticated = False
                    current_user = None
                    response = {'status': 'success', 'message': 'Logged out'}
                    print("✓ User logged out")

                else:
                    response = {'status': 'error', 'message': f'Unknown command: {command}'}

            except Exception as e:
                response = {'status': 'error', 'message': str(e)}
                print(f"✗ Error: {str(e)}")

            # Send response
            conn.send(json.dumps(response).encode('utf-8'))

    except Exception as e:
        print(f"✗ Connection error: {str(e)}")
    finally:
        conn.close()
        print(f"🔌 Client disconnected from {addr}")


def start_server():
    """Start FTP server"""
    ensure_files_dir()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)

    print("=" * 60)
    print("🚀 FTP SERVER STARTED")
    print("=" * 60)
    print(f"Host: {SERVER_HOST}")
    print(f"Port: {SERVER_PORT}")
    print(f"Files Directory: {FILES_DIR}")
    print(f"Default User: {DEFAULT_USER}")
    print(f"Default Password: {DEFAULT_PASSWORD}")
    print("=" * 60)

    try:
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\n\n⛔ Server shutting down...")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_server()
