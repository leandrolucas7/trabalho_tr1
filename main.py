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
    print("[Main] Iniciando o ecossistema do simulador...")
    
    # 1. Cria a fila segura para comunicação entre threads
    gui_queue = queue.Queue()
    
    # 2. Inicializa a janela nativa do Tkinter
    root = tk.Tk()
    
    # 3. Instancia a aplicação da GUI
    app = TelecomSimulatorApp(root)
    app.gui_queue = gui_queue  # Conecta a fila à GUI
    
    # 4. Cria e dispara a Thread do Receptor (Servidor) em background
    t_receptor = threading.Thread(target=run_receptor_server, args=(gui_queue,))
    t_receptor.daemon = True
    t_receptor.start()
    
    print("[Main] Interface e servidor rodando com sucesso.")
    
    # 5. Entrega o controle para o laço de renderização do Tkinter
    root.mainloop()

if __name__ == "__main__":
    main()
