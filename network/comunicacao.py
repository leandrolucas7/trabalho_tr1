import socket
import pickle
import queue

# Standard network settings for local simulation
HOST = '127.0.0.1'  # localhost
PORT = 5000        # Communication port

def send_signal_via_socket(signal_data: list[float] | list[int]):
    """
    Transmitter side (Client): Opens a temporary socket, connects to the 
    background server, serializes the signal list using pickle, and transmits it.
    """
    try:
        # Create a standard TCP Socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        
        # Serialize the numeric signal array (with or without noise) into raw bytes
        serialized_data = pickle.dumps(signal_data)
        
        # Send everything through the pipe
        client_socket.sendall(serialized_data)
        client_socket.close()
    except Exception as e:
        print(f"[Transmitter Error] Failed to send data via socket: {e}")


def run_receptor_server(gui_queue: queue.Queue):
    """
    Receiver side (Server): This function runs inside a background Daemon Thread.
    It blocks on listen mode waiting for incoming signal data chunks from the socket.
    When data arrives, it deserializes it and drops it inside the GUI queue thread-safely.
    """
    # Create and bind the server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR prevents the "Address already in use" error when restarting the app fast
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"[Receiver Server] Listening on {HOST}:{PORT} in background thread...")

    while True:
        try:
            # Code blocks here waiting for the transmitter connection (Thread safe!)
            connection, address = server_socket.accept()
            
            data_buffer = b""
            while True:
                packet = connection.recv(4096)
                if not packet:
                    break
                data_buffer += packet
                
            if data_buffer:
                # Reconstruct the original Python list of numbers out of raw network bytes
                received_signal = pickle.loads(data_buffer)
                
                # Push the data safely into the queue so the Tkinter UI thread can read it
                gui_queue.put(received_signal)
                
            connection.close()
        except Exception as e:
            print(f"[Receiver Server Error] Exception during socket loop: {e}")
            break
