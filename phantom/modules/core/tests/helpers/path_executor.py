"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Path Executor Helper

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

import sys
import pickle
import base64
from pathlib import Path


def execute_path_operation():
    """
    Executes Path or file operations based on serialized request data.

    Reads a base64-encoded, pickled request from sys.argv[1], performs the
    requested operation (Path method call or file I/O), and outputs a
    base64-encoded, pickled response containing the result or error.

    Request format (pickled dict):
        - type: 'path' or 'file'
        - path: Path string to operate on
        - method: Method name to call
        - args: Positional arguments tuple
        - kwargs: Keyword arguments dict

    Response format (pickled dict):
        - success: Boolean indicating operation success
        - result: Operation result (if successful)
        - error: Error message (if failed)
        - method: Method name that was called
    """
    if len(sys.argv) != 2:
        error_response = {'success': False, 'error': 'Invalid arguments'}
        print(base64.b64encode(pickle.dumps(error_response)).decode())
        sys.exit(1)

    try:
        # Deserialize the request from command-line argument
        encoded_request = sys.argv[1]
        request = pickle.loads(base64.b64decode(encoded_request))

        # Extract operation parameters
        operation_type = request.get('type', 'path')
        path_str = request.get('path', '')
        method_name = request.get('method', '')
        args = request.get('args', ())
        kwargs = request.get('kwargs', {})

        # Handle file operations (read, write, append)
        if operation_type == 'file':
            if method_name == 'read':
                with open(path_str, 'r') as f:
                    result = f.read()
                response = {'success': True, 'result': result, 'method': method_name}
            elif method_name == 'write':
                content = args[0] if args else kwargs.get('data', '')
                with open(path_str, 'w') as f:
                    f.write(content)
                response = {'success': True, 'result': None, 'method': method_name}
            elif method_name == 'append':
                content = args[0] if args else kwargs.get('data', '')
                with open(path_str, 'a') as f:
                    f.write(content)
                response = {'success': True, 'result': None, 'method': method_name}
            else:
                response = {'success': False, 'error': f"Unknown file operation: {method_name}"}
        else:
            # Handle Path operations (exists, mkdir, read_text, etc.)
            path_obj = Path(path_str)

            if not hasattr(path_obj, method_name):
                response = {'success': False, 'error': f"Method {method_name} not found on Path"}
            else:
                # Dynamically call the requested Path method
                method = getattr(path_obj, method_name)
                result = method(*args, **kwargs)

                # Serialize Path objects and iterables for transmission
                if isinstance(result, Path):
                    result = str(result)
                elif hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                    result = list(result)
                    result = [str(p) if isinstance(p, Path) else p for p in result]

                response = {'success': True, 'result': result, 'method': method_name}

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc(file=sys.stderr)
        response = {'success': False, 'error': error_msg}

    # Serialize and output the response
    print(base64.b64encode(pickle.dumps(response)).decode())


if __name__ == '__main__':
    execute_path_operation()
