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


C = {
    "bg":        "#f0f2f5",
    "card":      "#ffffff",
    "border":    "#dde1e7",
    "text":      "#1a2332",
    "muted":     "#6c757d",
    "accent":    "#2563eb",
    "accent_h":  "#1d4ed8",
    "success":   "#16a34a",
    "warning":   "#d97706",
    "danger":    "#dc2626",
    "step_bg":   "#f8fafc",
    "arrow":     "#94a3b8",
    "plot_bg":   "#fafafa",
    "grid":      "#e2e8f0",
    "entry_bg":  "#ffffff",
}

STEP_COLORS = ["#dbeafe", "#dcfce7", "#fef9c3", "#fce7f3", "#ede9fe", "#ffedd5", "#f0fdf4"]

FRAMING_VALUES = ["Contagem de Caracteres", "Inserção de Bytes", "Inserção de Bits"]
ERROR_VALUES = ["Bit de Paridade Par", "Checksum (8-bit)", "CRC-32 (IEEE 802)", "Código de Hamming"]
DIGITAL_VALUES = ["NRZ-Polar", "Manchester", "Bipolar (AMI)"]
ANALOG_VALUES = ["Nenhum", "ASK", "FSK", "QPSK", "16-QAM"]


class TelecomSimulatorApp:
    def __init__(self, root):
        """Cria a janela principal, aplica o tema visual, monta as abas e inicia a leitura assíncrona da fila do receptor."""
        self.root = root
        self.root.title("Mayday - Simulador OSI")
        self.root.geometry("1500x920")
        self.root.minsize(1280, 780)

        self._apply_theme()

        self.gui_queue = None

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=16)

        self.tab_transmitter = ttk.Frame(self.notebook)
        self.tab_receiver = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_transmitter, text="  Transmissor  ")
        self.notebook.add(self.tab_receiver, text="  Receptor  ")

        self._setup_transmitter_tab()
        self._setup_receiver_tab()
        self._start_queue_polling()

    # ── Tema ──────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        """Configura o tema visual do Tkinter e padroniza a aparência dos widgets."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.root.configure(bg=C["bg"])
        self.style.configure("TFrame", background=C["bg"])
        self.style.configure("TNotebook", background=C["bg"], borderwidth=0)
        self.style.configure(
            "TNotebook.Tab", font=("Segoe UI", 10, "bold"),
            padding=[18, 6], background="#e2e8f0", foreground=C["text"],
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", C["card"])],
            foreground=[("selected", C["accent"])],
        )
        self.style.configure("TLabelframe", background=C["bg"], borderwidth=1, relief="solid")
        self.style.configure(
            "TLabelframe.Label", font=("Segoe UI", 10, "bold"),
            background=C["bg"], foreground=C["text"],
        )
        self.style.configure("TLabel", font=("Segoe UI", 10), background=C["bg"], foreground=C["text"])
        self.style.configure(
            "Accent.TButton", font=("Segoe UI", 10, "bold"),
            background=C["accent"], foreground="white", borderwidth=0, padding=10,
        )
        self.style.map("Accent.TButton", background=[("active", C["accent_h"])])
        self.style.configure("TCombobox", font=("Segoe UI", 10))

    def _make_entry(self, parent, width=30, initial=""):
        """Cria um campo de texto simples com estilo consistente e cursor visível."""
        entry = tk.Entry(
            parent, width=width, font=("Segoe UI", 10),
            bg=C["entry_bg"], fg=C["text"],
            insertbackground=C["text"], insertwidth=2,
            relief="solid", borderwidth=1,
            highlightthickness=1, highlightcolor=C["accent"],
            highlightbackground=C["border"],
        )
        if initial:
            entry.insert(0, initial)
        return entry

    # ── Utilitários ───────────────────────────────────────────────────────────

    @staticmethod
    def _bits_str(bits: list[bool], max_len: int = 64) -> str:
        """Converte uma lista de bits em uma string compacta de 0 e 1 para exibição na interface."""
        s = "".join("1" if b else "0" for b in bits)
        if len(s) > max_len:
            return s[:max_len] + f"…  (+{len(s) - max_len} bits)"
        return s

    @staticmethod
    def _signal_stats(signal) -> str:
        """Resume um sinal numérico informando quantidade de amostras e estatísticas básicas."""
        arr = np.array(signal, dtype=float)
        if len(arr) == 0:
            return "vazio"
        return f"{len(arr)} amostras  |  min={arr.min():.2f}  max={arr.max():.2f}  média={arr.mean():.3f}"

    def _make_scrollable(self, parent):
        """Cria um container com rolagem vertical para listas de etapas ou blocos longos."""
        outer = ttk.Frame(parent)
        canvas = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def _on_mousewheel(event):
            """Desloca a área rolável com base na direção e intensidade da roda do mouse."""
            # Ajusta o deslocamento da rolagem conforme o movimento da roda do mouse.
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_event):
            """Ativa a captura global da roda do mouse enquanto o ponteiro estiver sobre a área rolável."""
            # Ativa a captura da roda do mouse quando o ponteiro entra na área rolável.
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(_event):
            """Desativa a captura global da roda do mouse quando o ponteiro sai da área rolável."""
            # Remove a captura ao sair da área para não interferir em outros widgets.
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        return outer, inner

    def _render_pipeline_steps(self, container, steps: list[dict]):
        """Desenha a sequência de etapas do pipeline em cartões visuais com texto explicativo."""
        for widget in container.winfo_children():
            widget.destroy()

        for i, step in enumerate(steps):
            bg = STEP_COLORS[i % len(STEP_COLORS)]
            card = tk.Frame(
                container, bg=bg, highlightbackground=C["border"],
                highlightthickness=1, padx=12, pady=10,
            )
            card.pack(fill="x", pady=(0, 2))

            header = tk.Frame(card, bg=bg)
            header.pack(fill="x")
            tk.Label(
                header, text=f" {step['num']} ", bg=C["accent"], fg="white",
                font=("Segoe UI", 9, "bold"), padx=4,
            ).pack(side="left")
            tk.Label(
                header, text=step["title"], bg=bg, fg=C["text"],
                font=("Segoe UI", 10, "bold"), anchor="w",
            ).pack(side="left", padx=8)

            if step.get("badge"):
                tk.Label(
                    header, text=step["badge"], bg=step.get("badge_color", C["muted"]),
                    fg="white", font=("Segoe UI", 8, "bold"), padx=6, pady=1,
                ).pack(side="right")

            tk.Label(
                card, text=step["detail"], bg=bg, fg=C["text"],
                font=("Segoe UI", 9), anchor="w", justify="left", wraplength=520,
            ).pack(fill="x", pady=(6, 0))

            if step.get("mono"):
                mono = tk.Text(
                    card, height=step.get("mono_lines", 2), wrap="none",
                    font=("Courier New", 9), bg="#1e293b", fg="#e2e8f0",
                    relief="flat", padx=8, pady=6, insertbackground="#e2e8f0",
                )
                mono.insert("1.0", step["mono"])
                mono.config(state="disabled")
                mono.pack(fill="x", pady=(6, 0))

            if i < len(steps) - 1:
                tk.Label(container, text="▼", bg=C["bg"], fg=C["arrow"], font=("Segoe UI", 11)).pack(pady=2)

    def _add_protocol_combos(self, parent):
        """Cria e organiza os seletores de protocolo usados apenas no painel do transmissor."""
        combos = {}

        ttk.Label(parent, text="Enquadramento:").pack(anchor="w")
        combos["framing"] = ttk.Combobox(parent, values=FRAMING_VALUES, state="readonly", width=28)
        combos["framing"].current(0)
        combos["framing"].pack(fill="x", pady=(2, 10))

        ttk.Label(parent, text="Resistência a Erros (EDC):").pack(anchor="w")
        combos["error"] = ttk.Combobox(parent, values=ERROR_VALUES, state="readonly", width=28)
        combos["error"].current(2)
        combos["error"].pack(fill="x", pady=(2, 10))

        ttk.Label(parent, text="Modulação Digital:").pack(anchor="w")
        combos["digital"] = ttk.Combobox(parent, values=DIGITAL_VALUES, state="readonly", width=28)
        combos["digital"].current(0)
        combos["digital"].pack(fill="x", pady=(2, 10))

        ttk.Label(parent, text="Modulação Portadora:").pack(anchor="w")
        combos["analog"] = ttk.Combobox(parent, values=ANALOG_VALUES, state="readonly", width=28)
        combos["analog"].current(0)
        combos["analog"].pack(fill="x", pady=(2, 4))

        lock_lbl = ttk.Label(
            parent, text="", foreground=C["muted"], font=("Segoe UI", 8),
        )
        lock_lbl.pack(anchor="w", pady=(0, 6))
        combos["lock_lbl"] = lock_lbl

        def on_analog_change(_event=None):
            """Sincroniza o estado da modulação digital com a escolha da modulação portadora."""
            if combos["analog"].get() == "Nenhum":
                combos["digital"].config(state="readonly")
                lock_lbl.config(text="")
            else:
                combos["digital"].set("NRZ-Polar")
                combos["digital"].config(state="disabled")
                lock_lbl.config(
                    text="ℹ  Com portadora ativa, digital trava em NRZ-Polar.",
                    foreground=C["accent"],
                )

        combos["analog"].bind("<<ComboboxSelected>>", on_analog_change)
        on_analog_change()
        return combos

    def _update_rx_protocol_info(self, pacote: dict):
        """Atualiza a área lateral com os parâmetros de protocolo recebidos pelo receptor."""
        linhas = [
            f"Enquadramento: {pacote['framing_choice']}",
            f"EDC: {pacote['error_choice']}",
            f"Digital: {pacote['mod_digital']}",
            f"Portadora: {pacote['mod_analog']}",
            f"Meio: {pacote['tx_mode']}",
            f"Ruído aplicado: μ={pacote.get('media', 0)}, σ={pacote.get('desvio', 0)}",
        ]
        self.lbl_rx_protocol.config(text="\n".join(linhas))

    # ── Aba Transmissor ───────────────────────────────────────────────────────

    def _setup_transmitter_tab(self):
        """Monta o painel do transmissor com entrada de mensagem, seletores de protocolo, ruído e gráficos."""
        paned = ttk.PanedWindow(self.tab_transmitter, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        ctrl_outer = ttk.LabelFrame(paned, text=" Configurações ", padding=14)
        paned.add(ctrl_outer, weight=0)

        ttk.Label(ctrl_outer, text="Mensagem:").pack(anchor="w")
        self.entry_message = self._make_entry(ctrl_outer, width=32, initial="Rumo ao Hexa!")
        self.entry_message.pack(fill="x", pady=(2, 10))

        self.tx_combos = self._add_protocol_combos(ctrl_outer)

        noise_frame = ttk.LabelFrame(ctrl_outer, text=" Ruído ", padding=10)
        noise_frame.pack(fill="x", pady=(8, 14))

        nf = ttk.Frame(noise_frame)
        nf.pack(fill="x")
        ttk.Label(nf, text="μ:").grid(row=0, column=0, sticky="w", padx=2)
        self.entry_media = self._make_entry(nf, width=8, initial="0.0")
        self.entry_media.grid(row=0, column=1, padx=4)
        ttk.Label(nf, text="σ:").grid(row=0, column=2, sticky="w", padx=(10, 2))
        self.entry_desvio = self._make_entry(nf, width=8, initial="0.0")
        self.entry_desvio.grid(row=0, column=3, padx=4)

        self.btn_transmit = ttk.Button(
            ctrl_outer, text="▶  TRANSMITIR", style="Accent.TButton",
            command=self._on_transmit_clicked,
        )
        self.btn_transmit.pack(fill="x", ipady=4)

        mid_paned = ttk.PanedWindow(paned, orient="vertical")
        paned.add(mid_paned, weight=3)

        pipe_frame = ttk.LabelFrame(mid_paned, text=" Pipeline de Transmissão ", padding=8)
        mid_paned.add(pipe_frame, weight=2)
        scroll_outer, self.tx_pipeline_container = self._make_scrollable(pipe_frame)
        scroll_outer.pack(fill="both", expand=True)
        self._render_pipeline_steps(self.tx_pipeline_container, [{
            "num": "—", "title": "Aguardando transmissão",
            "detail": "Configure os parâmetros e clique em TRANSMITIR para visualizar cada etapa.",
        }])

        plots_frame = ttk.LabelFrame(mid_paned, text=" Sinais a Enviar ", padding=8)
        mid_paned.add(plots_frame, weight=3)

        self.fig_tx = Figure(figsize=(8, 5), dpi=100, facecolor=C["plot_bg"])
        self.ax_tx_digital = self.fig_tx.add_subplot(211)
        self.ax_tx_carrier = self.fig_tx.add_subplot(212)
        self.fig_tx.subplots_adjust(hspace=0.45, left=0.08, right=0.97, top=0.93, bottom=0.10)
        self.canvas_tx = FigureCanvasTkAgg(self.fig_tx, master=plots_frame)
        self.canvas_tx.get_tk_widget().pack(fill="both", expand=True)
        self._clear_tx_plots()

    # ── Aba Receptor ──────────────────────────────────────────────────────────

    def _setup_receiver_tab(self):
        """Monta o painel do receptor, exibindo a mensagem recuperada, estatísticas e gráficos de recepção."""
        paned = ttk.PanedWindow(self.tab_receiver, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        ctrl_outer = ttk.LabelFrame(paned, text=" Receptor ", padding=14)
        paned.add(ctrl_outer, weight=0)

        proto_frame = ttk.LabelFrame(ctrl_outer, text=" Parâmetros recebidos", padding=10)
        proto_frame.pack(fill="x", pady=(0, 12))

        self.lbl_rx_protocol = ttk.Label(
            proto_frame,
            text="Aguardando pacote via socket…",
            foreground=C["muted"], font=("Segoe UI", 9), justify="left",
            wraplength=250,
        )
        self.lbl_rx_protocol.pack(anchor="w")

        status_frame = ttk.LabelFrame(ctrl_outer, text=" Resultado ", padding=10)
        status_frame.pack(fill="x")

        ttk.Label(status_frame, text="Mensagem Recuperada:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.lbl_decoded_msg = ttk.Label(
            status_frame, text="Aguardando sinal…",
            font=("Courier New", 13, "bold"), foreground=C["muted"],
            wraplength=250, justify="left",
        )
        self.lbl_decoded_msg.pack(anchor="w", pady=(4, 10))

        info = tk.Frame(status_frame, bg=C["step_bg"], highlightbackground=C["border"], highlightthickness=1)
        info.pack(fill="x")
        self.lbl_rx_signal = tk.Label(
            info, text="Sinal recebido: —", bg=C["step_bg"], fg=C["text"],
            font=("Segoe UI", 9), anchor="w", padx=10, pady=4,
            wraplength=250, justify="left",
        )
        self.lbl_rx_signal.pack(fill="x")
        self.lbl_edc = tk.Label(
            info, text="EDC: —", bg=C["step_bg"], fg=C["text"],
            font=("Segoe UI", 9), anchor="w", padx=10, pady=4,
            wraplength=250, justify="left",
        )
        self.lbl_edc.pack(fill="x")
        self.lbl_decode = tk.Label(
            info, text="Decodificação: —", bg=C["step_bg"], fg=C["text"],
            font=("Segoe UI", 9, "bold"), anchor="w", padx=10, pady=4,
            wraplength=250, justify="left",
        )
        self.lbl_decode.pack(fill="x")

        mid_paned = ttk.PanedWindow(paned, orient="vertical")
        paned.add(mid_paned, weight=3)

        pipe_frame = ttk.LabelFrame(mid_paned, text=" Pipeline de Recepção ", padding=8)
        mid_paned.add(pipe_frame, weight=2)
        scroll_outer, self.rx_pipeline_container = self._make_scrollable(pipe_frame)
        scroll_outer.pack(fill="both", expand=True)
        self._render_pipeline_steps(self.rx_pipeline_container, [{
            "num": "—", "title": "Aguardando pacote via socket",
            "detail": (
                "O servidor TCP (thread separada) desserializa o pacote pickle enviado "
                "pelo transmissor: sinal corrompido + parâmetros de protocolo para "
                "demodulação, EDC e desenquadramento. A mensagem original não é enviada."
            ),
        }])

        plots_frame = ttk.LabelFrame(mid_paned, text=" Sinais Recebidos e Decodificados ", padding=8)
        mid_paned.add(plots_frame, weight=3)

        self.fig_rx = Figure(figsize=(8, 5), dpi=100, facecolor=C["plot_bg"])
        self.ax_rx_signal = self.fig_rx.add_subplot(211)
        self.ax_rx_decoded = self.fig_rx.add_subplot(212)
        self.fig_rx.subplots_adjust(hspace=0.45, left=0.08, right=0.97, top=0.93, bottom=0.10)
        self.canvas_rx = FigureCanvasTkAgg(self.fig_rx, master=plots_frame)
        self.canvas_rx.get_tk_widget().pack(fill="both", expand=True)
        self._clear_rx_plots()

    # ── Gráficos ──────────────────────────────────────────────────────────────

    def _style_axis(self, ax, title, xlabel, ylabel):
        """Aplica o estilo visual padrão a um eixo do Matplotlib."""
        ax.set_facecolor(C["plot_bg"])
        ax.set_title(title, fontsize=10, fontweight="bold", color=C["text"], pad=8)
        ax.set_xlabel(xlabel, fontsize=9, color=C["muted"])
        ax.set_ylabel(ylabel, fontsize=9, color=C["muted"])
        ax.tick_params(labelsize=8, colors=C["muted"])
        ax.grid(True, linestyle="--", alpha=0.5, color=C["grid"])
        for spine in ax.spines.values():
            spine.set_color(C["border"])

    def _clear_tx_plots(self):
        """Limpa os gráficos do transmissor e exibe mensagens de estado vazio."""
        self.ax_tx_digital.clear()
        self._style_axis(self.ax_tx_digital, "Modulação Digital (banda base)", "Amostras", "Tensão (V)")
        self.ax_tx_digital.text(
            0.5, 0.5, "Nenhum sinal gerado", transform=self.ax_tx_digital.transAxes,
            ha="center", va="center", color=C["muted"], fontsize=11,
        )
        self.ax_tx_carrier.clear()
        self._style_axis(self.ax_tx_carrier, "Modulação Portadora (desativada)", "Amostras", "Amplitude (V)")
        self.ax_tx_carrier.text(
            0.5, 0.5, "Selecione uma modulação portadora\npara visualizar a onda analógica",
            transform=self.ax_tx_carrier.transAxes, ha="center", va="center",
            color=C["muted"], fontsize=10,
        )
        self.canvas_tx.draw()

    def _clear_rx_plots(self):
        """Limpa os gráficos do receptor e exibe mensagens de aguardando dados."""
        self.ax_rx_signal.clear()
        self._style_axis(self.ax_rx_signal, "Sinal recebido via socket", "Amostras", "Amplitude")
        self.ax_rx_signal.text(
            0.5, 0.5, "Aguardando sinal…", transform=self.ax_rx_signal.transAxes,
            ha="center", va="center", color=C["muted"], fontsize=11,
        )
        self.ax_rx_decoded.clear()
        self._style_axis(self.ax_rx_decoded, "Bits decodificados (camada física)", "Posição do bit", "Valor lógico")
        self.ax_rx_decoded.text(
            0.5, 0.5, "Aguardando decodificação…", transform=self.ax_rx_decoded.transAxes,
            ha="center", va="center", color=C["muted"], fontsize=11,
        )
        self.canvas_rx.draw()

    def _plot_digital_signal(self, ax, signal, color="#2563eb", label="Sinal digital", max_pts=300):
        """Plota um sinal digital em formato de degrau para facilitar a leitura dos bits."""
        sig = signal[:max_pts]
        ax.step(np.arange(len(sig)), sig, where="post", color=color, lw=1.8, label=label, alpha=0.9)
        if len(signal) > max_pts:
            ax.annotate(
                f"… {len(signal)} amostras totais",
                xy=(max_pts - 1, sig[-1]), fontsize=8, color=C["muted"],
            )
        if len(sig) > 0:
            margin = max(abs(min(sig)), abs(max(sig)), 0.5) * 0.3
            ax.set_ylim(min(sig) - margin, max(sig) + margin)

    def _plot_waveform(self, ax, signal, color="#2563eb", label="Sinal", max_pts=2000, step=False):
        """Plota uma forma de onda contínua ou em degrau, dependendo do contexto."""
        sig = signal[:max_pts]
        x = np.arange(len(sig))
        if step:
            ax.step(x, sig, where="post", color=color, lw=1.5, label=label, alpha=0.85)
        else:
            ax.plot(x, sig, color=color, lw=1.2, label=label, alpha=0.85)
        if len(signal) > max_pts:
            ax.annotate(
                f"… {len(signal)} amostras totais",
                xy=(0.98, 0.02), xycoords="axes fraction",
                ha="right", fontsize=8, color=C["muted"],
            )

    def _plot_received_signal(self, ax, noisy_signal, tx_mode, mod_analog):
        """Plota o sinal recebido pelo receptor, ajustando o tipo de visualização conforme o meio de transmissão."""
        max_pts = 250 if tx_mode == "Cabo" else 2000
        step = tx_mode == "Cabo"
        self._plot_waveform(
            ax, noisy_signal, color="#2563eb",
            label="Sinal recebido", max_pts=max_pts, step=step,
        )
        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        meio = "banda base (cabo)" if tx_mode == "Cabo" else mod_analog
        ax.set_title(
            f"Sinal recebido via socket — {meio}",
            fontsize=10, fontweight="bold", color=C["text"], pad=8,
        )

    def _plot_decoded_bits(self, ax, rx_bits, max_bits=120):
        """Mostra os bits decodificados na camada física para comparação visual com a recepção."""
        n = min(len(rx_bits), max_bits)
        rx_trim = rx_bits[:n]
        rx_int = [1 if b else 0 for b in rx_trim]
        ax.step(np.arange(n), rx_int, where="post", color="#16a34a", lw=1.8, label="Bits decodificados")
        ax.set_title(
            f"Bits decodificados — {len(rx_bits)} bits totais",
            fontsize=10, fontweight="bold", color=C["text"], pad=8,
        )
        ax.set_xlabel("Posição do bit", fontsize=9, color=C["muted"])
        ax.set_ylabel("Valor lógico", fontsize=9, color=C["muted"])
        ax.set_yticks([0, 1])
        ax.set_ylim(-0.3, 1.4)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.5, color=C["grid"])

    # ── Codificação / decodificação ───────────────────────────────────────────

    def _encode_digital(self, bits, mod_digital):
        """Encaminha o bitstream para a função de codificação digital escolhida na interface."""
        if mod_digital == "NRZ-Polar":
            return digital_core.encode_nrz_polar(bits)
        if mod_digital == "Manchester":
            return digital_core.encode_manchester(bits)
        return digital_core.encode_bipolar(bits)

    def _decode_physical_bits(self, noisy_signal, tx_mode, mod_digital, mod_analog):
        """Executa a etapa inversa da camada física, escolhendo a decodificação correta para o meio usado."""
        if tx_mode == "Cabo":
            if mod_digital == "NRZ-Polar":
                return digital_core.decode_nrz_polar(noisy_signal)
            if mod_digital == "Manchester":
                return digital_core.decode_manchester(noisy_signal)
            return digital_core.decode_bipolar(noisy_signal)

        if mod_analog == "ASK":
            rx_dig = portadora_core.decode_ask(noisy_signal)
        elif mod_analog == "FSK":
            rx_dig = portadora_core.decode_fsk(noisy_signal)
        elif mod_analog == "QPSK":
            rx_dig = portadora_core.decode_qpsk(noisy_signal)
        else:
            rx_dig = portadora_core.decode_16qam(noisy_signal)

        return digital_core.decode_nrz_polar(rx_dig)

    # ── Transmissão ───────────────────────────────────────────────────────────

    def _on_transmit_clicked(self):
        """Executa o pipeline completo do transmissor: converte texto, enquadra, protege, modula, aplica ruído e envia."""
        message_text = self.entry_message.get()
        if not message_text:
            return

        try:
            media = float(self.entry_media.get())
            desvio = float(self.entry_desvio.get())
        except ValueError:
            return

        framing_choice = self.tx_combos["framing"].get()
        error_choice = self.tx_combos["error"].get()
        mod_digital = self.tx_combos["digital"].get()
        mod_analog = self.tx_combos["analog"].get()

        raw_bits = utils.string_to_bitstream(message_text)
        if raw_bits is None:
            return

        payloads = [raw_bits]
        if framing_choice == "Contagem de Caracteres":
            frames = enquadramento.add_character_count_framing(payloads)
        elif framing_choice == "Inserção de Bytes":
            frames = enquadramento.add_byte_stuffing_framing(payloads)
        else:
            frames = enquadramento.add_bit_stuffing_framing(payloads)

        framed_bits = frames[0]

        if error_choice == "Bit de Paridade Par":
            protected_bits = erros_core.add_even_parity(framed_bits)
        elif error_choice == "Checksum (8-bit)":
            protected_bits = erros_core.add_checksum(framed_bits)
        elif error_choice == "CRC-32 (IEEE 802)":
            protected_bits = erros_core.add_crc32(framed_bits)
        else:
            protected_bits = erros_core.add_hamming(framed_bits)

        digital_signal = self._encode_digital(protected_bits, mod_digital)

        if mod_analog == "Nenhum":
            carrier_signal = None
            tx_mode = "Cabo"
            signal_to_send = digital_signal
        else:
            if mod_analog == "ASK":
                carrier_signal = portadora_core.encode_ask(digital_signal)
            elif mod_analog == "FSK":
                carrier_signal = portadora_core.encode_fsk(digital_signal)
            elif mod_analog == "QPSK":
                carrier_signal = portadora_core.encode_qpsk(digital_signal)
            else:
                carrier_signal = portadora_core.encode_16qam(digital_signal)
            tx_mode = "Ar"
            signal_to_send = carrier_signal

        noisy_signal = canal.inject_gaussian_noise(signal_to_send, media, desvio)

        tx_steps = [
            {"num": 1, "title": "Mensagem ASCII",
             "detail": f'Texto de entrada: "{message_text}"  ({len(message_text)} caracteres)',
             "mono": message_text, "mono_lines": 1},
            {"num": 2, "title": "Codificação → Bitstream",
             "detail": f"{len(raw_bits)} bits  (8 bits/caractere, MSB primeiro)",
             "mono": self._bits_str(raw_bits), "mono_lines": 2},
            {"num": 3, "title": f"Enquadramento — {framing_choice}",
             "detail": f"{len(raw_bits)} → {len(framed_bits)} bits",
             "mono": self._bits_str(framed_bits), "mono_lines": 2},
            {"num": 4, "title": f"Resistência a Erros — {error_choice}",
             "detail": f"{len(framed_bits)} → {len(protected_bits)} bits",
             "mono": self._bits_str(protected_bits), "mono_lines": 2},
            {"num": 5, "title": f"Modulação Digital — {mod_digital}",
             "detail": self._signal_stats(digital_signal),
             "badge": f"{len(protected_bits)} bits", "badge_color": C["accent"]},
        ]

        if carrier_signal is not None:
            tx_steps.append({
                "num": 6, "title": f"Modulação Portadora — {mod_analog}",
                "detail": self._signal_stats(carrier_signal),
                "badge": "NRZ → onda", "badge_color": "#7c3aed",
            })
            tx_steps.append({
                "num": 7, "title": "Ruído + envio via socket (pickle)",
                "detail": (
                    f"AWGN (μ={media}, σ={desvio}) aplicado ao sinal.\n"
                    f"Pacote serializado: sinal ({len(noisy_signal)} amostras) + "
                    f"parâmetros de protocolo (enquadramento, EDC, modulações).\n"
                    f"A mensagem original NÃO é enviada."
                ),
                "badge": tx_mode, "badge_color": C["warning"],
            })
        else:
            tx_steps.append({
                "num": 6, "title": "Ruído + envio via socket (pickle)",
                "detail": (
                    f"AWGN (μ={media}, σ={desvio}) sobre o sinal digital.\n"
                    f"Pacote serializado: sinal ({len(noisy_signal)} amostras) + "
                    f"parâmetros de protocolo (enquadramento, EDC, modulações).\n"
                    f"A mensagem original NÃO é enviada."
                ),
                "badge": tx_mode, "badge_color": C["warning"],
            })

        self._render_pipeline_steps(self.tx_pipeline_container, tx_steps)

        self.ax_tx_digital.clear()
        self._style_axis(
            self.ax_tx_digital, f"Sinal digital — {mod_digital}",
            "Amostras / posição", "Tensão (V)",
        )
        self._plot_digital_signal(self.ax_tx_digital, digital_signal, label=mod_digital)

        self.ax_tx_carrier.clear()
        if carrier_signal is not None:
            self._style_axis(
                self.ax_tx_carrier, f"Sinal portadora — {mod_analog}",
                "Amostras (tempo)", "Amplitude (V)",
            )
            self._plot_waveform(self.ax_tx_carrier, carrier_signal, color="#7c3aed", label=mod_analog)
            self.ax_tx_carrier.legend(loc="upper right", fontsize=8)
        else:
            self._style_axis(self.ax_tx_carrier, "Modulação portadora — não utilizada", "Amostras", "Amplitude (V)")
            self.ax_tx_carrier.text(
                0.5, 0.5, "Transmissão em banda base (sem portadora)",
                transform=self.ax_tx_carrier.transAxes, ha="center", va="center",
                color=C["muted"], fontsize=10,
            )

        self.canvas_tx.draw()

        pacote = {
            "noisy_signal": noisy_signal,
            "framing_choice": framing_choice,
            "error_choice": error_choice,
            "mod_digital": mod_digital,
            "mod_analog": mod_analog,
            "tx_mode": tx_mode,
            "protected_bit_count": len(protected_bits),
            "media": media,
            "desvio": desvio,
        }
        net_core.send_signal_via_socket(pacote)

    # ── Recepção ──────────────────────────────────────────────────────────────

    def _start_queue_polling(self):
        """Verifica periodicamente a fila compartilhada para processar pacotes recebidos pelo servidor."""
        if self.gui_queue and not self.gui_queue.empty():
            try:
                pacote = self.gui_queue.get_nowait()
                self._process_received_packet(pacote)
                self.notebook.select(self.tab_receiver)
            except Exception as e:
                print(f"[GUI Error] {e}")

        self.root.after(100, self._start_queue_polling)

    def _process_received_packet(self, pacote):
        """Processa o pacote recebido, executando a recepção, a verificação de erros e a atualização visual da interface."""
        if not isinstance(pacote, dict) or "noisy_signal" not in pacote:
            self.lbl_decoded_msg.config(text="[ pacote inválido ]", foreground=C["danger"])
            return

        noisy_signal = pacote["noisy_signal"]
        if not isinstance(noisy_signal, list) or len(noisy_signal) == 0:
            self.lbl_decoded_msg.config(text="[ sinal inválido ]", foreground=C["danger"])
            return

        framing_choice = pacote["framing_choice"]
        error_choice = pacote["error_choice"]
        mod_digital = pacote["mod_digital"]
        mod_analog = pacote["mod_analog"]
        tx_mode = pacote["tx_mode"]
        bit_count = pacote.get("protected_bit_count", len(noisy_signal))

        self._update_rx_protocol_info(pacote)

        # 1. Demodulação física com os parâmetros que vieram no pacote serializado.
        rx_bits_full = self._decode_physical_bits(noisy_signal, tx_mode, mod_digital, mod_analog)
        rx_bits = rx_bits_full[:bit_count]
        while len(rx_bits) < bit_count:
            rx_bits.append(False)

        # 2. Verificação e correção de erros da camada de enlace.
        edc_corrected = False
        if error_choice == "Bit de Paridade Par":
            after_edc, edc_error = erros_core.verify_and_remove_even_parity(rx_bits)
        elif error_choice == "Checksum (8-bit)":
            after_edc, edc_error = erros_core.verify_and_remove_checksum(rx_bits)
        elif error_choice == "CRC-32 (IEEE 802)":
            after_edc, edc_error = erros_core.verify_and_remove_crc32(rx_bits)
        else:
            after_edc, edc_error = erros_core.verify_and_correct_hamming(list(rx_bits))
            edc_corrected = edc_error and error_choice == "Código de Hamming"

        # 3. Remove o enquadramento para recuperar o payload original.
        if framing_choice == "Contagem de Caracteres":
            raw_payloads = enquadramento.remove_character_count_framing([after_edc])
        elif framing_choice == "Inserção de Bytes":
            raw_payloads = enquadramento.remove_byte_stuffing_framing([after_edc])
        else:
            raw_payloads = enquadramento.remove_bit_stuffing_framing([after_edc])

        payload_bits = []
        for rp in raw_payloads:
            payload_bits.extend(rp)

        # Remove apenas o byte incompleto no final; não apaga zeros válidos que fazem parte do ASCII.
        final_bits = list(payload_bits)
        remainder = len(final_bits) % 8
        if remainder:
            final_bits = final_bits[:-remainder]

        final_text = utils.bitstream_to_string(final_bits) if final_bits else None

        # ── Status visual ──
        self.lbl_rx_signal.config(text=f"Sinal recebido: {self._signal_stats(noisy_signal)}")

        if edc_error:
            if edc_corrected:
                self.lbl_edc.config(
                    text=f"EDC ({error_choice}): erro de 1 bit corrigido",
                    fg=C["warning"],
                )
            else:
                self.lbl_edc.config(
                    text=f"EDC ({error_choice}): inconsistência detectada — possível corrupção",
                    fg=C["danger"],
                )
        else:
            self.lbl_edc.config(text=f"EDC ({error_choice}): bloco íntegro", fg=C["success"])

        if final_text is None or not final_text.strip():
            self.lbl_decoded_msg.config(text="[ ilegível / corrompido ]", foreground=C["danger"])
            self.lbl_decode.config(
                text="Decodificação: falha — payload não-ASCII ou vazio",
                fg=C["danger"],
            )
        elif edc_error and not edc_corrected:
            self.lbl_decoded_msg.config(text=f'"{final_text}"', foreground=C["warning"])
            self.lbl_decode.config(
                text="Decodificação: texto parcial (EDC reportou corrupção)",
                fg=C["warning"],
            )
        else:
            self.lbl_decoded_msg.config(text=f'"{final_text}"', foreground=C["success"])
            self.lbl_decode.config(text="Decodificação: ASCII recuperado com sucesso", fg=C["success"])

        # ── Pipeline visual da recepção ──
        rx_steps = [
            {
                "num": 1, "title": "Pacote recebido via socket (pickle)",
                "detail": (
                    f"Desserializado na thread do servidor TCP.\n"
                    f"Sinal: {self._signal_stats(noisy_signal)}\n"
                    f"Protocolo: {framing_choice} | {error_choice} | "
                    f"{mod_digital} | {mod_analog} | {tx_mode}"
                ),
                "badge": f"{len(noisy_signal)} amostras", "badge_color": C["accent"],
            },
            {
                "num": 2, "title": f"Demodulação física — {mod_digital}"
                + (f" + portadora {mod_analog}" if tx_mode == "Ar" else ""),
                "detail": (
                    f"Parâmetros lidos do pacote (não configurados localmente).\n"
                    + (f"{mod_analog} → NRZ → " if tx_mode == "Ar" else "")
                    + f"{mod_digital} → {len(rx_bits)} bits recuperados"
                ),
                "mono": self._bits_str(rx_bits), "mono_lines": 2,
            },
            {
                "num": 3, "title": f"Verificação EDC — {error_choice}",
                "detail": (
                    ("Erro detectado e corrigido (Hamming)." if edc_corrected else
                     "Inconsistência detectada — dados possivelmente corrompidos." if edc_error else
                     "Integridade validada com sucesso.")
                    + f"\n{len(rx_bits)} → {len(after_edc)} bits (EDC removido)"
                ),
                "badge": "corrigido" if edc_corrected else ("falha" if edc_error else "OK"),
                "badge_color": C["warning"] if edc_corrected else (C["danger"] if edc_error else C["success"]),
                "mono": self._bits_str(after_edc), "mono_lines": 2,
            },
            {
                "num": 4, "title": f"Desenquadramento — {framing_choice}",
                "detail": f"{len(after_edc)} → {len(payload_bits)} bits  (headers/flags removidos)",
                "mono": self._bits_str(payload_bits), "mono_lines": 2,
            },
            {
                "num": 5, "title": "Decodificação ASCII",
                "detail": (
                    f"Payload útil: {len(final_bits)} bits\n"
                    + (f'Texto recuperado: "{final_text}"' if final_text
                       else "Falha — sequência não representa ASCII válido.")
                ),
                "mono": self._bits_str(final_bits), "mono_lines": 2,
                "badge": "corrompido" if (edc_error and not edc_corrected) else ("OK" if final_text else "falha"),
                "badge_color": C["danger"] if (edc_error and not edc_corrected) else (
                    C["success"] if final_text else C["warning"]
                ),
            },
        ]
        self._render_pipeline_steps(self.rx_pipeline_container, rx_steps)

        # ── Gráficos RX ──
        self.ax_rx_signal.clear()
        self._style_axis(self.ax_rx_signal, "", "Amostras", "Amplitude")
        self._plot_received_signal(self.ax_rx_signal, noisy_signal, tx_mode, mod_analog)

        self.ax_rx_decoded.clear()
        self._plot_decoded_bits(self.ax_rx_decoded, rx_bits)

        self.canvas_rx.draw()
