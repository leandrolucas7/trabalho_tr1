import socket
import pickle
import queue

HOST = "127.0.0.1"
PORT = 5000

# Chaves do pacote serializado (pickle) enviado pelo transmissor ao receptor.
# Contém o sinal corrompido + parâmetros de protocolo para o processo reverso.
# NÃO inclui mensagem original, bitstream bruto nem sinal limpo de referência.
PACOTE_CHAVES = (
    "noisy_signal",
    "framing_choice",
    "error_choice",
    "mod_digital",
    "mod_analog",
    "tx_mode",
    "protected_bit_count",
    "media",
    "desvio",
)


def send_signal_via_socket(pacote: dict):
    """
    Transmissor (cliente TCP): serializa via pickle um pacote com o sinal recebido
    pelo canal AWGN e os parâmetros de protocolo necessários ao processo reverso
    no receptor (enquadramento, EDC, modulações).
    """
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        client_socket.sendall(pickle.dumps(pacote))
        client_socket.close()
    except Exception as e:
        print(f"[Transmitter Error] Failed to send data via socket: {e}")


def run_receptor_server(gui_queue: queue.Queue):
    """
    Receptor (servidor TCP): roda em thread separada (daemon), desserializa o
    pacote pickle e o repassa à GUI via fila thread-safe.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"[Receiver Server] Listening on {HOST}:{PORT} in background thread...")

    while True:
        try:
            connection, address = server_socket.accept()
            print(f"[Receiver Server] Conexão de {address}")

            data_buffer = b""
            while True:
                packet = connection.recv(4096)
                if not packet:
                    break
                data_buffer += packet

            if data_buffer:
                pacote = pickle.loads(data_buffer)
                gui_queue.put(pacote)

            connection.close()
        except Exception as e:
            print(f"[Receiver Server Error] Exception during socket loop: {e}")
            break
