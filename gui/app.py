import tkinter as tk
from tkinter import ttk
import numpy as np

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import core.utils as utils
import core.enlace_enquadramento as enquadramento
import core.enlace_erros as erros_core
import core.fisica_digital as digital_core
import core.fisica_portadora as portadora_core
import network.comunicacao as net_core

class TelecomSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Comunicação - Camada Física e Enlace")
        self.root.geometry("1300x850")
        self.root.minsize(1100, 750)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TLabelframe.Label', font=('Helvetica', 12, 'bold'), foreground='#333333')
        self.style.configure('TButton', font=('Helvetica', 11, 'bold'), background='#4A90E2', foreground='white')
        self.style.map('TButton', background=[('active', '#357ABD')])
        
        self.gui_queue = None
        self.current_mod_digital = "NRZ-Polar"
        self.current_mod_analog = "ASK"
        self.last_tx_bits = [] 
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=15, pady=15)
        
        self.tab_transmitter = ttk.Frame(self.notebook)
        self.tab_receiver = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_transmitter, text=" 📡 Transmissor / Canal ")
        self.notebook.add(self.tab_receiver, text=" 🖥️ Receptor / Decodificação ")
        
        self._setup_transmitter_tab()
        self._setup_receiver_tab()
        self._start_queue_polling()

    def _setup_transmitter_tab(self):
        controls_frame = ttk.LabelFrame(self.tab_transmitter, text=" Painel de Controle (Transmissão) ", padding=20)
        controls_frame.pack(side='left', fill='y', padx=15, pady=15)
        
        ttk.Label(controls_frame, text="Mensagem de Texto:", font=('Helvetica', 10)).pack(anchor='w', pady=(10,2))
        self.entry_message = ttk.Entry(controls_frame, width=35, font=('Helvetica', 11))
        self.entry_message.pack(anchor='w', pady=5)
        self.entry_message.insert(0, "Hi")
        
        ttk.Label(controls_frame, text="Protocolo de Enquadramento:", font=('Helvetica', 10)).pack(anchor='w', pady=(10,2))
        self.combo_framing = ttk.Combobox(controls_frame, values=["Contagem de Caracteres", "Inserção de Bytes", "Inserção de Bits"], state="readonly", width=32, font=('Helvetica', 10))
        self.combo_framing.current(0)
        self.combo_framing.pack(anchor='w', pady=2)
        
        ttk.Label(controls_frame, text="Controle de Erro (EDC/ECC):", font=('Helvetica', 10)).pack(anchor='w', pady=(10,2))
        self.combo_error = ttk.Combobox(controls_frame, values=["Bit de Paridade Par", "Checksum (8-bit)", "CRC-32 (IEEE 802)", "Código de Hamming"], state="readonly", width=32, font=('Helvetica', 10))
        self.combo_error.current(0)
        self.combo_error.pack(anchor='w', pady=2)
        
        ttk.Label(controls_frame, text="Modulação Digital (Banda Base):", font=('Helvetica', 10)).pack(anchor='w', pady=(10,2))
        self.combo_mod_digital = ttk.Combobox(controls_frame, values=["NRZ-Polar", "Manchester", "Bipolar (AMI)"], state="readonly", width=32, font=('Helvetica', 10))
        self.combo_mod_digital.current(0)
        self.combo_mod_digital.pack(anchor='w', pady=2)

        ttk.Label(controls_frame, text="Modulação Analógica (Portadora):", font=('Helvetica', 10)).pack(anchor='w', pady=(10,2))
        self.combo_mod_analog = ttk.Combobox(controls_frame, values=["ASK", "FSK", "QPSK", "16-QAM"], state="readonly", width=32, font=('Helvetica', 10))
        self.combo_mod_analog.current(0)
        self.combo_mod_analog.pack(anchor='w', pady=2)
        
        ttk.Label(controls_frame, text="Porcentagem de Erro do Canal (%):", font=('Helvetica', 10, 'bold')).pack(anchor='w', pady=(20,2))
        self.slider_noise = tk.Scale(controls_frame, from_=0, to=100, orient='horizontal', length=250, resolution=1, background='#f0f0f0', highlightthickness=0)
        self.slider_noise.set(0)
        self.slider_noise.pack(anchor='w', pady=2)
        
        self.btn_transmit = ttk.Button(controls_frame, text="🚀 TRANSMITIR SINAL", command=self._on_transmit_clicked)
        self.btn_transmit.pack(fill='x', pady=20, ipady=5)
        
        self.plots_tx_frame = ttk.LabelFrame(self.tab_transmitter, text=" Visualização dos Sinais Gerados ", padding=10)
        self.plots_tx_frame.pack(side='right', fill='both', expand=True, padx=15, pady=15)
        
        self.fig_tx = Figure(figsize=(7, 6), dpi=100, facecolor='#f8f9fa')
        self.ax_tx_digital = self.fig_tx.add_subplot(211)
        self.ax_tx_analog = self.fig_tx.add_subplot(212)
        self.fig_tx.tight_layout(pad=4.0)
        
        self.canvas_tx = FigureCanvasTkAgg(self.fig_tx, master=self.plots_tx_frame)
        self.canvas_tx.get_tk_widget().pack(fill='both', expand=True)
        self._clear_tx_plots()

    def _setup_receiver_tab(self):
        report_frame = ttk.LabelFrame(self.tab_receiver, text=" Diagnóstico e Decodificação ", padding=20)
        report_frame.pack(side='left', fill='y', padx=15, pady=15)
        
        ttk.Label(report_frame, text="Mensagem Final Recuperada:", font=("Helvetica", 11, "bold")).pack(anchor='w', pady=2)
        self.lbl_decoded_msg = ttk.Label(report_frame, text="Aguardando...", font=("Courier", 18, "bold"), foreground="#888888")
        self.lbl_decoded_msg.pack(anchor='w', pady=10)
        
        ttk.Label(report_frame, text="Status da Transmissão e Logs:", font=("Helvetica", 11, "bold")).pack(anchor='w', pady=(20, 5))
        self.text_report = tk.Text(report_frame, width=42, height=25, wrap="word", font=("Courier", 10), background="#1e1e1e", foreground="#00ff00")
        self.text_report.pack(anchor='w', pady=2)
        self._update_log_text(">> Sistema Receptor Operacional.\n>> Escutando pacotes na rede...")
        
        self.plots_rx_frame = ttk.LabelFrame(self.tab_receiver, text=" Sinais Capturados no Receptor ", padding=10)
        self.plots_rx_frame.pack(side='right', fill='both', expand=True, padx=15, pady=15)
        
        self.fig_rx = Figure(figsize=(7, 6), dpi=100, facecolor='#f8f9fa')
        self.ax_rx_wave = self.fig_rx.add_subplot(211)
        self.ax_rx_const = self.fig_rx.add_subplot(212)
        self.fig_rx.tight_layout(pad=4.0)
        
        self.canvas_rx = FigureCanvasTkAgg(self.fig_rx, master=self.plots_rx_frame)
        self.canvas_rx.get_tk_widget().pack(fill='both', expand=True)
        self._clear_rx_plots()

    def _clear_tx_plots(self):
        self.ax_tx_digital.clear()
        self.ax_tx_digital.set_title("Sinal Digital (Banda Base)", fontweight='bold')
        self.ax_tx_digital.set_xlabel("Bits / Posição")
        self.ax_tx_digital.set_ylabel("Tensão (V)")
        self.ax_tx_digital.grid(True, linestyle='--', alpha=0.6)
        
        self.ax_tx_analog.clear()
        self.ax_tx_analog.set_title("Onda Portadora Analógica (Banda Passante)", fontweight='bold')
        self.ax_tx_analog.set_xlabel("Amostras (Tempo)")
        self.ax_tx_analog.set_ylabel("Amplitude (V)")
        self.ax_tx_analog.grid(True, linestyle='--', alpha=0.6)
        self.canvas_tx.draw()

    def _clear_rx_plots(self):
        self.ax_rx_wave.clear()
        self.ax_rx_wave.set_title("Sinal Analógico Capturado (Com Ruído do Canal)", fontweight='bold')
        self.ax_rx_wave.set_xlabel("Amostras (Tempo)")
        self.ax_rx_wave.set_ylabel("Amplitude (V)")
        self.ax_rx_wave.grid(True, linestyle='--', alpha=0.6)
        
        self.ax_rx_const.clear()
        self.ax_rx_const.set_title("Análise de Demodulação", fontweight='bold')
        self.ax_rx_const.grid(True, linestyle='--', alpha=0.6)
        self.canvas_rx.draw()

    def _update_log_text(self, text):
        self.text_report.config(state="normal")
        self.text_report.delete("1.0", tk.END)
        self.text_report.insert(tk.END, text)
        self.text_report.config(state="disabled")

    def _on_transmit_clicked(self):
        message_text = self.entry_message.get()
        framing_choice = self.combo_framing.get()
        error_choice = self.combo_error.get()
        self.current_mod_digital = self.combo_mod_digital.get()
        self.current_mod_analog = self.combo_mod_analog.get()
        noise_value = self.slider_noise.get()
        
        if not message_text: return
            
        raw_bits = utils.string_to_bitstream(message_text)
        if raw_bits is None: return
            
        # O SEGREDO DO SUCESSO: Tratar a mensagem inteira como um único pacote dinâmico
        payloads = [raw_bits]
        
        if framing_choice == "Contagem de Caracteres":
            frames = enquadramento.add_character_count_framing(payloads)
        elif framing_choice == "Inserção de Bytes":
            frames = enquadramento.add_byte_stuffing_framing(payloads)
        else:
            frames = enquadramento.add_bit_stuffing_framing(payloads)
            
        protected_frames = []
        for frame in frames:
            if error_choice == "Bit de Paridade Par":
                protected_frames.append(erros_core.add_even_parity(frame))
            elif error_choice == "Checksum (8-bit)":
                protected_frames.append(erros_core.add_checksum(frame))
            elif error_choice == "CRC-32 (IEEE 802)":
                protected_frames.append(erros_core.add_crc32(frame))
            else:
                protected_frames.append(erros_core.add_hamming(frame))
                
        # Como temos apenas 1 pacote, ele já é a nossa fita final
        tx_bits = protected_frames[0]
        self.last_tx_bits = tx_bits 
        
        self._clear_tx_plots()
        
        # 1. GERA E DESENHA O SINAL DIGITAL (BANDA BASE)
        if self.current_mod_digital == "NRZ-Polar":
            digital_signal = digital_core.encode_nrz_polar(tx_bits)
        elif self.current_mod_digital == "Manchester":
            digital_signal = digital_core.encode_manchester(tx_bits)
        else:
            digital_signal = digital_core.encode_bipolar(tx_bits)
            
        self.ax_tx_digital.step(range(len(digital_signal)), digital_signal, where='post', color='#d62728', lw=2)
        self.ax_tx_digital.set_ylim(min(digital_signal)-0.5, max(digital_signal)+0.5)

        # 2. GERA E DESENHA A ONDA ANALÓGICA REAL (PORTADORA)
        if self.current_mod_analog == "ASK":
            analog_signal = portadora_core.encode_ask(tx_bits)
        elif self.current_mod_analog == "FSK":
            analog_signal = portadora_core.encode_fsk(tx_bits)
        elif self.current_mod_analog == "QPSK":
            analog_signal = portadora_core.encode_qpsk(tx_bits)
        else: 
            analog_signal = portadora_core.encode_16qam(tx_bits)
            
        self.ax_tx_analog.plot(analog_signal[:2000], color='#1f77b4', lw=1.5) 
        self.canvas_tx.draw()
        
        import core.canal as canal
        corrupted_signal = canal.inject_gaussian_noise(analog_signal, float(noise_value))
        net_core.send_signal_via_socket(corrupted_signal)

    def _start_queue_polling(self):
        """
        Varredura contínua rodando na thread da tela de 100ms em 100ms.
        """
        if self.gui_queue and not self.gui_queue.empty():
            try:
                corrupted_signal = self.gui_queue.get_nowait()
                self._clear_rx_plots()
                
                self.ax_rx_wave.plot(corrupted_signal[:2000], color='#ff7f0e', lw=1.0)
                
                # --- CAMADA FÍSICA RECEPTORA ---
                if self.current_mod_analog == "ASK":
                    rx_bits = portadora_core.decode_ask(corrupted_signal)
                    recovered_digital = [1 if b else 0 for b in rx_bits]
                    self.ax_rx_const.set_title("Bits Demodulados da Portadora")
                    self.ax_rx_const.step(range(len(recovered_digital[:100])), recovered_digital[:100], where='post', color='#2ca02c', lw=2)
                elif self.current_mod_analog == "FSK":
                    rx_bits = portadora_core.decode_fsk(corrupted_signal)
                    recovered_digital = [1 if b else 0 for b in rx_bits]
                    self.ax_rx_const.set_title("Bits Demodulados da Portadora")
                    self.ax_rx_const.step(range(len(recovered_digital[:100])), recovered_digital[:100], where='post', color='#2ca02c', lw=2)
                elif self.current_mod_analog == "QPSK":
                    rx_bits = portadora_core.decode_qpsk(corrupted_signal)
                    self.ax_rx_const.set_title("Diagrama de Constelação (I / Q)")
                    for j in range(0, len(corrupted_signal), 100):
                        seg = np.array(corrupted_signal[j:j+100])
                        if len(seg) == 100:
                            t = np.linspace(0, 1, 100, endpoint=False)
                            i_pt = np.sum(seg * np.cos(2*np.pi*2*t)) / 50.0
                            q_pt = np.sum(seg * np.sin(2*np.pi*2*t)) / 50.0
                            self.ax_rx_const.scatter(i_pt, q_pt, color='#9467bd', alpha=0.8, s=30)
                else: # 16-QAM
                    rx_bits = portadora_core.decode_16qam(corrupted_signal)
                    self.ax_rx_const.set_title("Diagrama de Constelação (I / Q)")
                    for j in range(0, len(corrupted_signal), 100):
                        seg = np.array(corrupted_signal[j:j+100])
                        if len(seg) == 100:
                            t = np.linspace(0, 1, 100, endpoint=False)
                            i_pt = np.sum(seg * np.cos(2*np.pi*2*t)) / 50.0
                            q_pt = np.sum(seg * np.sin(2*np.pi*2*t)) / 50.0
                            self.ax_rx_const.scatter(i_pt, q_pt, color='#8c564b', alpha=0.8, s=30)
                
                self.canvas_rx.draw()
                
                # --- CAMADA DE ENLACE RECEPTORA (TOTALMENTE ALINHADA) ---
                framing_choice = self.combo_framing.get()
                error_choice = self.combo_error.get()
                
                log_report = f">>> RELATÓRIO DO RECEPTOR <<<\n"
                log_report += f"Demodulação : {self.current_mod_analog}\n"
                
                if self.last_tx_bits:
                    min_len = min(len(self.last_tx_bits), len(rx_bits))
                    bit_errors = sum(1 for b1, b2 in zip(self.last_tx_bits[:min_len], rx_bits[:min_len]) if b1 != b2)
                    log_report += f"Erros Físicos (AWGN): {bit_errors} bits corrompidos\n\n"
                
                log_report += f"[ENLACE] Removendo Proteção: {error_choice}\n"
                
                # Desembrulha a camada de erro da fita inteira de uma vez
                if error_choice == "Bit de Paridade Par":
                    clean, err = erros_core.verify_and_remove_even_parity(rx_bits)
                elif error_choice == "Checksum (8-bit)":
                    clean, err = erros_core.verify_and_remove_checksum(rx_bits)
                elif error_choice == "CRC-32 (IEEE 802)":
                    clean, err = erros_core.verify_and_remove_crc32(rx_bits)
                else:
                    clean, err = erros_core.verify_and_correct_hamming(rx_bits)
                    
                if err: 
                    log_report += f"[ALERTA] Inconsistência matemática detectada!\n"
                else: 
                    log_report += f"[OK] Integridade matemática validada.\n"
                
                quadros_envelopados = [clean]
                
                log_report += f"[ENLACE] Removendo Enquadramento: {framing_choice}\n"
                if framing_choice == "Contagem de Caracteres":
                    raw_payloads = enquadramento.remove_character_count_framing(quadros_envelopados)
                elif framing_choice == "Inserção de Bytes":
                    raw_payloads = enquadramento.remove_byte_stuffing_framing(quadros_envelopados)
                else:
                    raw_payloads = enquadramento.remove_bit_stuffing_framing(quadros_envelopados)
                    
                final_bits = []
                for rp in raw_payloads:
                    final_bits.extend(rp)
                    
                log_report += f"[OK] Payload útil extraído: {len(final_bits)} bits.\n"
                self._update_log_text(log_report)
                
                if final_bits:
                    remainder = len(final_bits) % 8
                    if remainder != 0:
                        final_bits = final_bits[:-remainder]
                        
                    final_text = utils.bitstream_to_string(final_bits)
                    if final_text and final_text.strip():
                        self.lbl_decoded_msg.config(text=f'"{final_text}"', foreground="#2ca02c")
                    else:
                        self.lbl_decoded_msg.config(text="[Sinal Bruto/Não-ASCII]", foreground="#1f77b4")
                else:
                    self.lbl_decoded_msg.config(text="[Sinal Bruto/Vazio]", foreground="#1f77b4")
                    
            except Exception as e:
                print(f"[GUI Queue Error] Erro ao processar polling da fila: {e}")
                self.lbl_decoded_msg.config(text="[Erro de Processamento]", foreground="red")
                
        self.root.after(100, self._start_queue_polling)
