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
import core.canal as canal
import network.comunicacao as net_core

class TelecomSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Comunicação - Laboratório de Camada Física e Enlace")
        self.root.geometry("1400x900")
        self.root.minsize(1300, 800)
        
        self._apply_modern_theme()
        
        self.gui_queue = None
        self.last_tx_bits = [] 
        
        # Notebook (Abas) com estilo limpo
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.tab_transmitter = ttk.Frame(self.notebook)
        self.tab_receiver = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_transmitter, text=" TRANSMISSOR / CANAL ")
        self.notebook.add(self.tab_receiver, text=" RECEPTOR / DECODIFICAÇÃO ")
        
        self._setup_transmitter_tab()
        self._setup_receiver_tab()
        self._start_queue_polling()

    def _apply_modern_theme(self):
        """Aplica um tema moderno, limpo e profissional sem emojis."""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        bg_color = '#f8f9fa'
        text_color = '#2c3e50'
        accent_color = '#3498db'
        
        self.root.configure(bg=bg_color)
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TNotebook', background=bg_color, borderwidth=0)
        self.style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[15, 5], background='#e9ecef', foreground=text_color)
        self.style.map('TNotebook.Tab', background=[('selected', '#ffffff')], foreground=[('selected', accent_color)])
        
        self.style.configure('TLabelframe', background=bg_color, borderwidth=1, bordercolor='#dee2e6')
        self.style.configure('TLabelframe.Label', font=('Segoe UI', 11, 'bold'), background=bg_color, foreground=text_color)
        self.style.configure('TLabel', font=('Segoe UI', 10), background=bg_color, foreground=text_color)
        
        self.style.configure('TButton', font=('Segoe UI', 10, 'bold'), background=accent_color, foreground='white', borderwidth=0, padding=8)
        self.style.map('TButton', background=[('active', '#2980b9')])
        
        self.style.configure('TCombobox', font=('Segoe UI', 10))
        self.style.configure('TEntry', font=('Segoe UI', 10), padding=5)

    def _setup_transmitter_tab(self):
        # --- PAINEL ESQUERDO (CONTROLES) ---
        controls_frame = ttk.LabelFrame(self.tab_transmitter, text=" Configurações de Transmissão ", padding=20)
        controls_frame.pack(side='left', fill='y', padx=10, pady=10)
        
        ttk.Label(controls_frame, text="Mensagem de Texto:").pack(anchor='w', pady=(5,2))
        self.entry_message = ttk.Entry(controls_frame, width=35)
        self.entry_message.pack(anchor='w', pady=2)
        self.entry_message.insert(0, "Ola!")
        
        ttk.Label(controls_frame, text="Enquadramento:").pack(anchor='w', pady=(15,2))
        self.combo_framing = ttk.Combobox(controls_frame, values=["Contagem de Caracteres", "Inserção de Bytes", "Inserção de Bits"], state="readonly", width=33)
        self.combo_framing.current(0)
        self.combo_framing.pack(anchor='w', pady=2)
        
        ttk.Label(controls_frame, text="Detecção/Correção de Erro (EDC):").pack(anchor='w', pady=(15,2))
        self.combo_error = ttk.Combobox(controls_frame, values=["Bit de Paridade Par", "Checksum (8-bit)", "CRC-32 (IEEE 802)", "Código de Hamming"], state="readonly", width=33)
        self.combo_error.current(2)
        self.combo_error.pack(anchor='w', pady=2)
        
        ttk.Label(controls_frame, text="Modulação Digital (Banda Base):").pack(anchor='w', pady=(15,2))
        self.combo_mod_digital = ttk.Combobox(controls_frame, values=["NRZ-Polar", "Manchester", "Bipolar (AMI)"], state="readonly", width=33)
        self.combo_mod_digital.current(0)
        self.combo_mod_digital.pack(anchor='w', pady=2)

        ttk.Label(controls_frame, text="Modulação Analógica (Portadora):").pack(anchor='w', pady=(15,2))
        self.combo_mod_analog = ttk.Combobox(controls_frame, values=["Nenhum", "ASK", "FSK", "QPSK", "16-QAM"], state="readonly", width=33)
        self.combo_mod_analog.current(4) # Padrão 16-QAM
        self.combo_mod_analog.pack(anchor='w', pady=2)
        
        # O Gatilho Inteligente do Roadmap
        self.combo_mod_analog.bind("<<ComboboxSelected>>", self._on_analog_changed)
        
        # --- RUÍDO GAUSSIANO ---
        noise_frame = ttk.LabelFrame(controls_frame, text=" Parâmetros do Canal AWGN ", padding=10)
        noise_frame.pack(fill='x', pady=20)
        
        grid_frame = ttk.Frame(noise_frame)
        grid_frame.pack(fill='x')
        
        ttk.Label(grid_frame, text="Média (μ):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.entry_media = ttk.Entry(grid_frame, width=10)
        self.entry_media.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.entry_media.insert(0, "0.0")

        ttk.Label(grid_frame, text="Desvio (σ):").grid(row=0, column=2, sticky='w', padx=(15,5), pady=5)
        self.entry_desvio = ttk.Entry(grid_frame, width=10)
        self.entry_desvio.grid(row=0, column=3, sticky='w', padx=5, pady=5)
        self.entry_desvio.insert(0, "0.5")
        
        self.btn_transmit = ttk.Button(controls_frame, text="TRANSMITIR", command=self._on_transmit_clicked)
        self.btn_transmit.pack(fill='x', pady=20, ipady=8)
        
        # --- PAINEL DIREITO (GRÁFICOS) ---
        self.plots_tx_frame = ttk.LabelFrame(self.tab_transmitter, text=" Visualização dos Sinais Gerados ", padding=10)
        self.plots_tx_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        self.fig_tx = Figure(figsize=(7, 6), dpi=100, facecolor='#ffffff')
        self.ax_tx_digital = self.fig_tx.add_subplot(211)
        self.ax_tx_analog = self.fig_tx.add_subplot(212)
        self.fig_tx.tight_layout(pad=4.0)
        
        self.canvas_tx = FigureCanvasTkAgg(self.fig_tx, master=self.plots_tx_frame)
        self.canvas_tx.get_tk_widget().pack(fill='both', expand=True)
        
        self._on_analog_changed() # Aplica a regra logo na inicialização
        self._clear_tx_plots()

    def _setup_receiver_tab(self):
        report_frame = ttk.LabelFrame(self.tab_receiver, text=" Histórico e Decodificação ", padding=15)
        report_frame.pack(side='left', fill='y', padx=10, pady=10)
        
        ttk.Label(report_frame, text="Saída de Texto (Recuperada):", font=("Segoe UI", 10, "bold")).pack(anchor='w', pady=2)
        self.lbl_decoded_msg = ttk.Label(report_frame, text="Aguardando...", font=("Courier", 16, "bold"), foreground="#7f8c8d")
        self.lbl_decoded_msg.pack(anchor='w', pady=(5, 15))
        
        ttk.Label(report_frame, text="Log do Pipeline (Passo a Passo):", font=("Segoe UI", 10, "bold")).pack(anchor='w', pady=2)
        self.text_report = tk.Text(report_frame, width=50, height=30, wrap="word", font=("Courier", 9), background="#1e272e", foreground="#2ecc71", insertbackground="white")
        self.text_report.pack(anchor='w', pady=2, fill='y', expand=True)
        self._update_log_text(">> Sistema Operacional.\n>> Aguardando transmissão...")
        
        self.plots_rx_frame = ttk.LabelFrame(self.tab_receiver, text=" Sinais Capturados no Receptor ", padding=10)
        self.plots_rx_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        self.fig_rx = Figure(figsize=(7, 6), dpi=100, facecolor='#ffffff')
        self.ax_rx_top = self.fig_rx.add_subplot(211)
        self.ax_rx_bot = self.fig_rx.add_subplot(212)
        self.fig_rx.tight_layout(pad=4.0)
        
        self.canvas_rx = FigureCanvasTkAgg(self.fig_rx, master=self.plots_rx_frame)
        self.canvas_rx.get_tk_widget().pack(fill='both', expand=True)
        self._clear_rx_plots()

    def _on_analog_changed(self, event=None):
        """Regra do Roadmap: Analógico selecionado trava Digital em NRZ-Polar."""
        selecao = self.combo_mod_analog.get()
        if selecao == "Nenhum":
            self.combo_mod_digital.config(state="readonly")
        else:
            self.combo_mod_digital.set("NRZ-Polar")
            self.combo_mod_digital.config(state="disabled")

    def _clear_tx_plots(self):
        self.ax_tx_digital.clear()
        self.ax_tx_digital.set_title("Sinal Digital (Banda Base)", fontweight='bold')
        self.ax_tx_digital.set_xlabel("Bits / Posição")
        self.ax_tx_digital.set_ylabel("Tensão (V)")
        self.ax_tx_digital.grid(True, linestyle=':', alpha=0.7)
        
        self.ax_tx_analog.clear()
        self.ax_tx_analog.set_title("Onda Portadora Analógica (Banda Passante)", fontweight='bold')
        self.ax_tx_analog.set_xlabel("Amostras (Tempo)")
        self.ax_tx_analog.set_ylabel("Amplitude (V)")
        self.ax_tx_analog.grid(True, linestyle=':', alpha=0.7)
        self.canvas_tx.draw()

    def _clear_rx_plots(self):
        self.ax_rx_top.clear()
        self.ax_rx_top.set_title("Sinal Capturado do Canal", fontweight='bold')
        self.ax_rx_top.grid(True, linestyle=':', alpha=0.7)
        
        self.ax_rx_bot.clear()
        self.ax_rx_bot.set_title("Demodulação / Constelação", fontweight='bold')
        self.ax_rx_bot.grid(True, linestyle=':', alpha=0.7)
        self.canvas_rx.draw()

    def _update_log_text(self, text):
        self.text_report.config(state="normal")
        self.text_report.delete("1.0", tk.END)
        self.text_report.insert(tk.END, text)
        self.text_report.see(tk.END)
        self.text_report.config(state="disabled")

    def _on_transmit_clicked(self):
        message_text = self.entry_message.get()
        if not message_text: return
        
        try:
            media = float(self.entry_media.get())
            desvio = float(self.entry_desvio.get())
        except ValueError:
            self._update_log_text("[ERRO] Média e Desvio devem ser valores numéricos.")
            return

        framing_choice = self.combo_framing.get()
        error_choice = self.combo_error.get()
        mod_digital = self.combo_mod_digital.get()
        mod_analog = self.combo_mod_analog.get()
            
        raw_bits = utils.string_to_bitstream(message_text)
        if raw_bits is None: return
            
        # Enquadramento
        payloads = [raw_bits]
        if framing_choice == "Contagem de Caracteres": frames = enquadramento.add_character_count_framing(payloads)
        elif framing_choice == "Inserção de Bytes": frames = enquadramento.add_byte_stuffing_framing(payloads)
        else: frames = enquadramento.add_bit_stuffing_framing(payloads)
            
        # EDC/ECC
        protected_frames = []
        for frame in frames:
            if error_choice == "Bit de Paridade Par": protected_frames.append(erros_core.add_even_parity(frame))
            elif error_choice == "Checksum (8-bit)": protected_frames.append(erros_core.add_checksum(frame))
            elif error_choice == "CRC-32 (IEEE 802)": protected_frames.append(erros_core.add_crc32(frame))
            else: protected_frames.append(erros_core.add_hamming(frame))
                
        tx_bits = protected_frames[0]
        self.last_tx_bits = tx_bits 
        self._clear_tx_plots()
        
        # --- MODULAÇÃO DIGITAL ---
        if mod_digital == "NRZ-Polar": digital_signal = digital_core.encode_nrz_polar(tx_bits)
        elif mod_digital == "Manchester": digital_signal = digital_core.encode_manchester(tx_bits)
        else: digital_signal = digital_core.encode_bipolar(tx_bits)
            
        self.ax_tx_digital.step(range(len(digital_signal)), digital_signal, where='post', color='#e74c3c', lw=2)
        self.ax_tx_digital.set_ylim(min(digital_signal)-0.5, max(digital_signal)+0.5)

        # --- PACOTE INTELIGENTE (ENVIO) ---
        payload_data = {
            "mod_digital": mod_digital,
            "mod_analog": mod_analog,
            "framing_choice": framing_choice,
            "error_choice": error_choice
        }

        if mod_analog == "Nenhum": # Transmissão via CABO
            self.ax_tx_analog.clear()
            self.ax_tx_analog.text(0.5, 0.5, 'Transmissão Baseband (Cabo)\nOnda Portadora Desativada', horizontalalignment='center', verticalalignment='center', fontsize=12, color='#7f8c8d')
            
            noisy_signal = canal.inject_gaussian_noise(digital_signal, media, desvio)
            payload_data["clean_signal"] = digital_signal
            payload_data["noisy_signal"] = noisy_signal
            payload_data["tx_mode"] = "Cabo"
        else: # Transmissão via AR
            if mod_analog == "ASK": analog_signal = portadora_core.encode_ask(digital_signal)
            elif mod_analog == "FSK": analog_signal = portadora_core.encode_fsk(digital_signal)
            elif mod_analog == "QPSK": analog_signal = portadora_core.encode_qpsk(digital_signal)
            else: analog_signal = portadora_core.encode_16qam(digital_signal)
            
            self.ax_tx_analog.plot(analog_signal[:2000], color='#2980b9', lw=1.5) 
            
            noisy_signal = canal.inject_gaussian_noise(analog_signal, media, desvio)
            payload_data["clean_signal"] = analog_signal
            payload_data["noisy_signal"] = noisy_signal
            payload_data["tx_mode"] = "Ar"
            
        self.canvas_tx.draw()
        net_core.send_signal_via_socket(payload_data)

    def _start_queue_polling(self):
        if self.gui_queue and not self.gui_queue.empty():
            try:
                payload = self.gui_queue.get_nowait()
                self._process_received_payload(payload)
            except Exception as e:
                print(f"[GUI Error] Erro no polling: {e}")
                
        self.root.after(100, self._start_queue_polling)

    def _process_received_payload(self, payload):
        self._clear_rx_plots()
        
        clean_signal = payload["clean_signal"]
        noisy_signal = payload["noisy_signal"]
        tx_mode = payload["tx_mode"]
        mod_digital = payload["mod_digital"]
        mod_analog = payload["mod_analog"]
        framing_choice = payload["framing_choice"]
        error_choice = payload["error_choice"]
        
        log = "===== HISTÓRICO DE DECODIFICAÇÃO =====\n\n"
        log += f"[+] Meio: {tx_mode} | Digital: {mod_digital} | Portadora: {mod_analog}\n\n"
        
        # --- 1. OVERLAY DE SINAIS (O Efeito UAU) ---
        self.ax_rx_top.set_title("Canal AWGN: Sinal Original vs. Sinal Recebido")
        if tx_mode == "Cabo":
            self.ax_rx_top.step(range(len(clean_signal[:150])), clean_signal[:150], where='post', color='#bdc3c7', alpha=0.6, lw=3, label="Original (Limpo)")
            self.ax_rx_top.step(range(len(noisy_signal[:150])), noisy_signal[:150], where='post', color='#d35400', alpha=0.9, lw=1.5, label="Recebido (Ruído)")
            self.ax_rx_top.legend(loc="upper right", fontsize=8)
            
            if mod_digital == "NRZ-Polar": rx_bits = digital_core.decode_nrz_polar(noisy_signal)
            elif mod_digital == "Manchester": rx_bits = digital_core.decode_manchester(noisy_signal)
            else: rx_bits = digital_core.decode_bipolar(noisy_signal)
            
            self.ax_rx_bot.set_title("Bits Decididos (Limiar de Tensão)")
            bits_int = [1 if b else 0 for b in rx_bits]
            self.ax_rx_bot.step(range(len(bits_int[:100])), bits_int[:100], where='post', color='#27ae60', lw=2)
            
        else:
            self.ax_rx_top.plot(clean_signal[:1500], color='#bdc3c7', alpha=0.6, lw=2.5, label="Original (Limpo)")
            self.ax_rx_top.plot(noisy_signal[:1500], color='#d35400', alpha=0.9, lw=1.0, label="Recebido (Ruído)")
            self.ax_rx_top.legend(loc="upper right", fontsize=8)
            
            if mod_analog == "ASK": rx_dig = portadora_core.decode_ask(noisy_signal)
            elif mod_analog == "FSK": rx_dig = portadora_core.decode_fsk(noisy_signal)
            elif mod_analog == "QPSK": 
                rx_dig = portadora_core.decode_qpsk(noisy_signal)
                self._plot_constellation(noisy_signal)
            else: 
                rx_dig = portadora_core.decode_16qam(noisy_signal)
                self._plot_constellation(noisy_signal)
            
            if mod_analog in ["ASK", "FSK"]:
                self.ax_rx_bot.set_title("Tensão Recuperada da Portadora")
                self.ax_rx_bot.step(range(len(rx_dig[:100])), rx_dig[:100], where='post', color='#27ae60', lw=2)
                
            # Pipeline Físico: Analógico entrega Tensão para a Digital
            rx_bits = digital_core.decode_nrz_polar(rx_dig)
        
        self.canvas_rx.draw()
        
        # --- LOG VERBOSO (PASSO A PASSO) ---
        bits_display = "".join(["1" if b else "0" for b in rx_bits])
        log += f"[1] Camada Física -> Bits Brutos ({len(rx_bits)} bits):\n"
        log += f"    {bits_display[:60]}...\n\n"
        
        if self.last_tx_bits:
            min_len = min(len(self.last_tx_bits), len(rx_bits))
            bit_errors = sum(1 for b1, b2 in zip(self.last_tx_bits[:min_len], rx_bits[:min_len]) if b1 != b2)
            log += f"[!] Taxa de Erro Físico (BER): {bit_errors} bits corrompidos\n\n"
        
        log += f"[2] Camada de Enlace -> Verificação ({error_choice}):\n"
        if error_choice == "Bit de Paridade Par": clean, err = erros_core.verify_and_remove_even_parity(rx_bits)
        elif error_choice == "Checksum (8-bit)": clean, err = erros_core.verify_and_remove_checksum(rx_bits)
        elif error_choice == "CRC-32 (IEEE 802)": clean, err = erros_core.verify_and_remove_crc32(rx_bits)
        else: clean, err = erros_core.verify_and_correct_hamming(rx_bits)
            
        if err: log += f"    -> ALERTA: Inconsistência matemática detectada!\n\n"
        else: log += f"    -> OK: Integridade de bloco validada.\n\n"
        
        quadros_envelopados = [clean]
        
        log += f"[3] Desenquadramento -> Extração ({framing_choice}):\n"
        if framing_choice == "Contagem de Caracteres": raw_payloads = enquadramento.remove_character_count_framing(quadros_envelopados)
        elif framing_choice == "Inserção de Bytes": raw_payloads = enquadramento.remove_byte_stuffing_framing(quadros_envelopados)
        else: raw_payloads = enquadramento.remove_bit_stuffing_framing(quadros_envelopados)
            
        final_bits = []
        for rp in raw_payloads: final_bits.extend(rp)
            
        payload_display = "".join(["1" if b else "0" for b in final_bits])
        log += f"    -> Payload útil ({len(final_bits)} bits):\n"
        log += f"    {payload_display[:60]}...\n\n"
        
        # --- ASCII DECODE ---
        if final_bits:
            remainder = len(final_bits) % 8
            if remainder != 0: final_bits = final_bits[:-remainder]
                
            final_text = utils.bitstream_to_string(final_bits)
            if final_text and final_text.strip():
                self.lbl_decoded_msg.config(text=f'{final_text}', foreground="#27ae60")
                log += f"[4] Tradução ASCII -> SUCESSO."
            else:
                self.lbl_decoded_msg.config(text="[Sinal Ilegível]", foreground="#e67e22")
                log += f"[4] Tradução ASCII -> FALHA (Dados não-ASCII)."
        else:
            self.lbl_decoded_msg.config(text="[Vazio]", foreground="#e74c3c")
            log += f"[4] Tradução ASCII -> FALHA (Payload Vazio)."
            
        self._update_log_text(log)

    def _plot_constellation(self, corrupted_signal):
        self.ax_rx_bot.set_title("Diagrama de Constelação (I / Q)", fontweight='bold')
        for j in range(0, len(corrupted_signal), 100):
            seg = np.array(corrupted_signal[j:j+100])
            if len(seg) == 100:
                t = np.linspace(0, 1, 100, endpoint=False)
                i_pt = np.sum(seg * np.cos(2*np.pi*2*t)) / 50.0
                q_pt = np.sum(seg * np.sin(2*np.pi*2*t)) / 50.0
                self.ax_rx_bot.scatter(i_pt, q_pt, color='#8e44ad', alpha=0.7, s=25)