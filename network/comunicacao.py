import socket
import pickle
import queue

HOST = "127.0.0.1"
PORT = 5000

# Chaves que compõem o pacote serializado (pickle) enviado pelo transmissor ao receptor.
# O pacote leva o sinal já corrompido pelo canal e os parâmetros necessários para desfazer o processo.
# A mensagem original não é enviada para manter a simulação coerente com um enlace real.
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
    """Serializa o pacote da transmissão e o envia ao servidor receptor via socket TCP."""
    try:
        # Cria o socket TCP do lado transmissor.
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))

        # Converte o dicionário da transmissão em bytes usando pickle.
        client_socket.sendall(pickle.dumps(pacote))
        client_socket.close()
    except Exception as e:
        print(f"[Transmitter Error] Failed to send data via socket: {e}")


def run_receptor_server(gui_queue: queue.Queue):
    """Mantém o servidor receptor ouvindo pacotes e repassa os dados recebidos para a fila da interface."""
    # Cria o socket TCP do servidor receptor.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reiniciar o programa rapidamente sem erro de porta ocupada.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"[Receiver Server] Listening on {HOST}:{PORT} in background thread...")

    while True:
        try:
            # Bloqueia até chegar uma conexão do transmissor.
            connection, address = server_socket.accept()
            print(f"[Receiver Server] Conexão de {address}")

            # Lê todos os blocos de bytes recebidos antes de tentar desserializar.
            data_buffer = b""
            while True:
                packet = connection.recv(4096)
                if not packet:
                    break
                data_buffer += packet

            if data_buffer:
                # Reconstrói o dicionário Python original a partir do fluxo de bytes.
                pacote = pickle.loads(data_buffer)
                # Enfileira o pacote para a GUI ler com segurança na thread principal.
                gui_queue.put(pacote)

            connection.close()
        except Exception as e:
            print(f"[Receiver Server Error] Exception during socket loop: {e}")
            break
