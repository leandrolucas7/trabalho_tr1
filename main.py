import sys
import os

# Garante que o Python enxergue as pastas core, gui e network na raiz do projeto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
import threading
import queue
from gui.app import TelecomSimulatorApp
from network.comunicacao import run_receptor_server

def main():
    """Inicializa a aplicação principal, cria a interface gráfica e sobe o servidor receptor em uma thread separada."""
    print("[Main] Iniciando o ecossistema do simulador...")

    # 1. Cria a fila segura para troca de mensagens entre a thread do servidor e a thread da interface
    gui_queue = queue.Queue()

    # 2. Inicializa a janela nativa do Tkinter que vai conter toda a aplicação
    root = tk.Tk()

    # 3. Instancia a aplicação gráfica principal e conecta a janela raiz
    app = TelecomSimulatorApp(root)
    app.gui_queue = gui_queue  # Liga a fila ao componente gráfico para receber os pacotes do servidor.

    # 4. Cria e inicia a thread do receptor para ficar ouvindo conexões em segundo plano
    t_receptor = threading.Thread(target=run_receptor_server, args=(gui_queue,))
    t_receptor.daemon = True
    t_receptor.start()

    print("[Main] Interface e servidor rodando com sucesso.")

    # 5. Entrega o controle para o loop principal do Tkinter, que mantém a interface viva
    root.mainloop()

if __name__ == "__main__":
    main()
