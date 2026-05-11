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

file_history = {}
history_lock = threading.Lock()


def sanitize_filename(filename):
    """Return a safe filename or None if invalid."""
    if not filename:
        return None

    clean = os.path.basename(filename.strip())
    if not clean or clean in {'.', '..'}:
        return None

    return clean


def build_filepath(filename):
    """Build absolute path inside server files directory."""
    safe_name = sanitize_filename(filename)
    if not safe_name:
        return None, None
    return safe_name, os.path.join(FILES_DIR, safe_name)


def record_history(filename, user, operation, details=''):
    """Record a file operation in history."""
    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user': user,
        'operation': operation,
        'details': details
    }

    with history_lock:
        file_history.setdefault(filename, []).append(entry)

def ensure_files_dir():
    """Ensure files directory exists"""
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        print(f"✓ Directory '{FILES_DIR}' created")


def authenticate(username, password):
    """Authenticate user"""
    return username == DEFAULT_USER and password == DEFAULT_PASSWORD


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
                    filename = request.get('filename')
                    content = request.get('content', '')
                    
                    filepath = os.path.join(FILES_DIR, filename)
                    with open(filepath, 'w') as f:
                        f.write(content)
                    
                    response = {'status': 'success', 'message': f'File {filename} created on server'}
                    print(f"✓ File created: {filename}")
                
                elif command == 'upload':
                    filename = request.get('filename')
                    content = request.get('content')
                    
                    filepath = os.path.join(FILES_DIR, filename)
                    with open(filepath, 'w') as f:
                        f.write(content)
                    
                    response = {'status': 'success', 'message': f'File {filename} uploaded'}
                    print(f"✓ File uploaded: {filename}")
                
                elif command == 'rename_file':
                    old_name = request.get('old_name')
                    new_name = request.get('new_name')
                    safe_old, old_path = build_filepath(old_name)
                    safe_new, new_path = build_filepath(new_name)

                    if not old_path or not new_path:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    elif not os.path.exists(old_path):
                        response = {'status': 'error', 'message': f'File {safe_old} not found'}
                    elif os.path.exists(new_path):
                        response = {'status': 'error', 'message': f'File {safe_new} already exists'}
                    else:
                        os.rename(old_path, new_path)
                        with history_lock:
                            previous = file_history.pop(safe_old, [])
                            file_history.setdefault(safe_new, []).extend(previous)
                        record_history(safe_new, current_user, 'rename_file', f'{safe_old} -> {safe_new}')
                        response = {'status': 'success', 'message': f'File renamed: {safe_old} -> {safe_new}'}
                        print(f"✓ File renamed: {safe_old} -> {safe_new}")
                
                elif command == 'read_file':
                    filename = request.get('filename')
                    safe_name, filepath = build_filepath(filename)

                    if not filepath:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    elif not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f'File {safe_name} not found'}
                    else:
                        with open(filepath, 'r') as f:
                            content = f.read()
                        record_history(safe_name, current_user, 'read_file')
                        response = {
                            'status': 'success',
                            'message': f'File {safe_name} read successfully',
                            'filename': safe_name,
                            'content': content
                        }
                
                elif command == 'download':
                    filename = request.get('filename')
                    safe_name, filepath = build_filepath(filename)

                    if not filepath:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    elif not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f'File {safe_name} not found'}
                    else:
                        with open(filepath, 'r') as f:
                            content = f.read()
                        record_history(safe_name, current_user, 'download')
                        response = {
                            'status': 'success',
                            'message': f'File {safe_name} ready for download',
                            'filename': safe_name,
                            'content': content
                        }
                
                elif command == 'edit_file':
                    filename = request.get('filename')
                    new_content = request.get('content', '')
                    safe_name, filepath = build_filepath(filename)

                    if not filepath:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    elif not os.path.exists(filepath):
                        response = {'status': 'error', 'message': f'File {safe_name} not found'}
                    else:
                        with open(filepath, 'w') as f:
                            f.write(new_content)
                        record_history(safe_name, current_user, 'edit_file')
                        response = {'status': 'success', 'message': f'File {safe_name} updated'}
                        print(f"✓ File edited: {safe_name}")
                
                elif command == 'see_file_operation_history':
                    filename = request.get('filename')
                    safe_name, _ = build_filepath(filename)

                    if not safe_name:
                        response = {'status': 'error', 'message': 'Invalid filename'}
                    else:
                        with history_lock:
                            history = file_history.get(safe_name, [])

                        if not history:
                            response = {
                                'status': 'success',
                                'message': f'No history available for {safe_name}',
                                'filename': safe_name,
                                'history': []
                            }
                        else:
                            response = {
                                'status': 'success',
                                'message': f'History for {safe_name}',
                                'filename': safe_name,
                                'history': history
                            }
                
                elif command == 'list_files':
                    files = os.listdir(FILES_DIR)
                    response = {'status': 'success', 'files': files}
                    print(f"✓ Files listed: {len(files)} files found")
                
                elif command == 'logout':
                    authenticated = False
                    current_user = None
                    response = {'status': 'success', 'message': 'Logged out'}
                    print(f"✓ User logged out")
                
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
