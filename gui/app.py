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


# ── Paleta ──────────────────────────────────────────────────────────────────
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
}

STEP_COLORS = ["#dbeafe", "#dcfce7", "#fef9c3", "#fce7f3", "#ede9fe", "#ffedd5", "#f0fdf4"]


class TelecomSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Comunicação — Camada Física e Enlace")
        self.root.geometry("1500x920")
        self.root.minsize(1280, 780)

        self._apply_theme()

        self.gui_queue = None
        self.last_tx_bits = []
        self.last_tx_pipeline = {}
        self.last_original_message = ""

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
        self.style.configure(
            "TLabelframe", background=C["bg"], borderwidth=1, relief="solid",
        )
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
        self.style.configure("TEntry", font=("Segoe UI", 10), padding=4)

    # ── Utilitários de exibição ───────────────────────────────────────────────

    @staticmethod
    def _bits_str(bits: list[bool], max_len: int = 64) -> str:
        s = "".join("1" if b else "0" for b in bits)
        if len(s) > max_len:
            return s[:max_len] + f"…  (+{len(s) - max_len} bits)"
        return s

    @staticmethod
    def _signal_stats(signal) -> str:
        arr = np.array(signal, dtype=float)
        if len(arr) == 0:
            return "vazio"
        return f"{len(arr)} amostras  |  min={arr.min():.2f}  max={arr.max():.2f}  média={arr.mean():.3f}"

    def _make_scrollable(self, parent):
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
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        return outer, inner

    def _render_pipeline_steps(self, container, steps: list[dict]):
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
                badge_color = step.get("badge_color", C["muted"])
                tk.Label(
                    header, text=step["badge"], bg=badge_color, fg="white",
                    font=("Segoe UI", 8, "bold"), padx=6, pady=1,
                ).pack(side="right")

            tk.Label(
                card, text=step["detail"], bg=bg, fg=C["text"],
                font=("Segoe UI", 9), anchor="w", justify="left", wraplength=520,
            ).pack(fill="x", pady=(6, 0))

            if step.get("mono"):
                mono = tk.Text(
                    card, height=step.get("mono_lines", 2), wrap="none",
                    font=("Courier New", 9), bg="#1e293b", fg="#e2e8f0",
                    relief="flat", padx=8, pady=6,
                )
                mono.insert("1.0", step["mono"])
                mono.config(state="disabled")
                mono.pack(fill="x", pady=(6, 0))

            if i < len(steps) - 1:
                tk.Label(
                    container, text="▼", bg=C["bg"], fg=C["arrow"],
                    font=("Segoe UI", 11),
                ).pack(pady=2)

    # ── Aba Transmissor ───────────────────────────────────────────────────────

    def _setup_transmitter_tab(self):
        paned = ttk.PanedWindow(self.tab_transmitter, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Controles ──
        ctrl_outer = ttk.LabelFrame(paned, text=" Configurações ", padding=14)
        paned.add(ctrl_outer, weight=0)

        ttk.Label(ctrl_outer, text="Mensagem:").pack(anchor="w")
        self.entry_message = ttk.Entry(ctrl_outer, width=30)
        self.entry_message.pack(fill="x", pady=(2, 10))
        self.entry_message.insert(0, "Ola!")

        ttk.Label(ctrl_outer, text="Enquadramento:").pack(anchor="w")
        self.combo_framing = ttk.Combobox(
            ctrl_outer,
            values=["Contagem de Caracteres", "Inserção de Bytes", "Inserção de Bits"],
            state="readonly", width=28,
        )
        self.combo_framing.current(0)
        self.combo_framing.pack(fill="x", pady=(2, 10))

        ttk.Label(ctrl_outer, text="Resistência a Erros (EDC):").pack(anchor="w")
        self.combo_error = ttk.Combobox(
            ctrl_outer,
            values=["Bit de Paridade Par", "Checksum (8-bit)", "CRC-32 (IEEE 802)", "Código de Hamming"],
            state="readonly", width=28,
        )
        self.combo_error.current(2)
        self.combo_error.pack(fill="x", pady=(2, 10))

        ttk.Label(ctrl_outer, text="Modulação Digital:").pack(anchor="w")
        self.combo_mod_digital = ttk.Combobox(
            ctrl_outer, values=["NRZ-Polar", "Manchester", "Bipolar (AMI)"],
            state="readonly", width=28,
        )
        self.combo_mod_digital.current(0)
        self.combo_mod_digital.pack(fill="x", pady=(2, 10))

        ttk.Label(ctrl_outer, text="Modulação Portadora:").pack(anchor="w")
        self.combo_mod_analog = ttk.Combobox(
            ctrl_outer, values=["Nenhum", "ASK", "FSK", "QPSK", "16-QAM"],
            state="readonly", width=28,
        )
        self.combo_mod_analog.current(0)
        self.combo_mod_analog.pack(fill="x", pady=(2, 4))
        self.combo_mod_analog.bind("<<ComboboxSelected>>", self._on_analog_changed)

        self.lbl_nrz_lock = ttk.Label(
            ctrl_outer,
            text="ℹ  Com portadora ativa, digital trava em NRZ-Polar.",
            foreground=C["muted"], font=("Segoe UI", 8),
        )
        self.lbl_nrz_lock.pack(anchor="w", pady=(0, 10))

        noise_frame = ttk.LabelFrame(ctrl_outer, text=" Canal AWGN ", padding=10)
        noise_frame.pack(fill="x", pady=(0, 14))

        nf = ttk.Frame(noise_frame)
        nf.pack(fill="x")
        ttk.Label(nf, text="μ:").grid(row=0, column=0, sticky="w", padx=2)
        self.entry_media = ttk.Entry(nf, width=8)
        self.entry_media.grid(row=0, column=1, padx=4)
        self.entry_media.insert(0, "0.0")
        ttk.Label(nf, text="σ:").grid(row=0, column=2, sticky="w", padx=(10, 2))
        self.entry_desvio = ttk.Entry(nf, width=8)
        self.entry_desvio.grid(row=0, column=3, padx=4)
        self.entry_desvio.insert(0, "0.5")

        self.btn_transmit = ttk.Button(
            ctrl_outer, text="▶  TRANSMITIR", style="Accent.TButton",
            command=self._on_transmit_clicked,
        )
        self.btn_transmit.pack(fill="x", ipady=4)

        # ── Painel central: pipeline ──
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

        # ── Gráficos TX ──
        plots_frame = ttk.LabelFrame(mid_paned, text=" Sinais a Enviar ", padding=8)
        mid_paned.add(plots_frame, weight=3)

        self.fig_tx = Figure(figsize=(8, 5), dpi=100, facecolor=C["plot_bg"])
        self.ax_tx_digital = self.fig_tx.add_subplot(211)
        self.ax_tx_carrier = self.fig_tx.add_subplot(212)
        self.fig_tx.subplots_adjust(hspace=0.45, left=0.08, right=0.97, top=0.93, bottom=0.10)
        self.canvas_tx = FigureCanvasTkAgg(self.fig_tx, master=plots_frame)
        self.canvas_tx.get_tk_widget().pack(fill="both", expand=True)

        self._on_analog_changed()
        self._clear_tx_plots()

    # ── Aba Receptor ──────────────────────────────────────────────────────────

    def _setup_receiver_tab(self):
        paned = ttk.PanedWindow(self.tab_receiver, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Status lateral ──
        status_frame = ttk.LabelFrame(paned, text=" Resultado ", padding=14)
        paned.add(status_frame, weight=0)

        ttk.Label(status_frame, text="Mensagem Original:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.lbl_original_msg = ttk.Label(
            status_frame, text="—", font=("Courier New", 14), foreground=C["muted"],
        )
        self.lbl_original_msg.pack(anchor="w", pady=(2, 12))

        ttk.Label(status_frame, text="Mensagem Recuperada:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.lbl_decoded_msg = ttk.Label(
            status_frame, text="Aguardando…", font=("Courier New", 14, "bold"), foreground=C["muted"],
        )
        self.lbl_decoded_msg.pack(anchor="w", pady=(2, 12))

        stats_frame = tk.Frame(status_frame, bg=C["step_bg"], highlightbackground=C["border"], highlightthickness=1)
        stats_frame.pack(fill="x", pady=(0, 12))
        self.lbl_ber = tk.Label(
            stats_frame, text="BER físico: —", bg=C["step_bg"], fg=C["text"],
            font=("Segoe UI", 9), anchor="w", padx=10, pady=4,
        )
        self.lbl_ber.pack(fill="x")
        self.lbl_edc = tk.Label(
            stats_frame, text="EDC: —", bg=C["step_bg"], fg=C["text"],
            font=("Segoe UI", 9), anchor="w", padx=10, pady=4,
        )
        self.lbl_edc.pack(fill="x")
        self.lbl_match = tk.Label(
            stats_frame, text="Integridade: —", bg=C["step_bg"], fg=C["text"],
            font=("Segoe UI", 9, "bold"), anchor="w", padx=10, pady=4,
        )
        self.lbl_match.pack(fill="x")

        ttk.Label(status_frame, text="Comparação caractere a caractere:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.text_diff = tk.Text(
            status_frame, width=34, height=6, wrap="word",
            font=("Courier New", 11), bg="#1e293b", fg="#e2e8f0",
            relief="flat", padx=8, pady=6,
        )
        self.text_diff.pack(fill="x", pady=(4, 0))
        self.text_diff.tag_configure("ok", foreground="#4ade80")
        self.text_diff.tag_configure("bad", foreground="#f87171", underline=True)
        self.text_diff.tag_configure("missing", foreground="#fb923c")
        self.text_diff.insert("1.0", "Aguardando transmissão…")
        self.text_diff.config(state="disabled")

        # ── Centro: pipeline + gráficos ──
        mid_paned = ttk.PanedWindow(paned, orient="vertical")
        paned.add(mid_paned, weight=3)

        pipe_frame = ttk.LabelFrame(mid_paned, text=" Pipeline de Recepção ", padding=8)
        mid_paned.add(pipe_frame, weight=2)
        scroll_outer, self.rx_pipeline_container = self._make_scrollable(pipe_frame)
        scroll_outer.pack(fill="both", expand=True)
        self._render_pipeline_steps(self.rx_pipeline_container, [{
            "num": "—", "title": "Aguardando sinal",
            "detail": "O receptor processará o sinal assim que uma transmissão chegar.",
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
        ax.set_facecolor(C["plot_bg"])
        ax.set_title(title, fontsize=10, fontweight="bold", color=C["text"], pad=8)
        ax.set_xlabel(xlabel, fontsize=9, color=C["muted"])
        ax.set_ylabel(ylabel, fontsize=9, color=C["muted"])
        ax.tick_params(labelsize=8, colors=C["muted"])
        ax.grid(True, linestyle="--", alpha=0.5, color=C["grid"])
        for spine in ax.spines.values():
            spine.set_color(C["border"])

    def _clear_tx_plots(self):
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
        self.ax_rx_signal.clear()
        self._style_axis(self.ax_rx_signal, "Canal: sinal esperado vs. recebido", "Amostras", "Amplitude")
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
        sig = signal[:max_pts]
        x = np.arange(len(sig))
        ax.step(x, sig, where="post", color=color, lw=1.8, label=label, alpha=0.9)
        if len(signal) > max_pts:
            ax.annotate(
                f"… {len(signal)} amostras totais",
                xy=(max_pts - 1, sig[-1]), fontsize=8, color=C["muted"],
            )
        if len(sig) > 0:
            margin = max(abs(min(sig)), abs(max(sig)), 0.5) * 0.3
            ax.set_ylim(min(sig) - margin, max(sig) + margin)

    def _plot_waveform(self, ax, signal, color="#2563eb", label="Sinal", max_pts=2000, step=False):
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

    def _plot_rx_signal_overlay(self, ax, clean, noisy, tx_mode, mod_analog):
        max_pts = 250 if tx_mode == "Cabo" else 2000
        clean_s = clean[:max_pts]
        noisy_s = noisy[:max_pts]
        x = np.arange(len(clean_s))

        if tx_mode == "Cabo":
            self._plot_waveform(ax, clean_s, color="#94a3b8", label="Esperado (limpo)", max_pts=max_pts, step=True)
            self._plot_waveform(ax, noisy_s, color="#ea580c", label="Recebido (com ruído)", max_pts=max_pts, step=True)
        else:
            self._plot_waveform(ax, clean_s, color="#94a3b8", label="Esperado (limpo)", max_pts=max_pts)
            self._plot_waveform(ax, noisy_s, color="#ea580c", label="Recebido (com ruído)", max_pts=max_pts)

        ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
        title = f"Sinal no canal ({'banda base' if tx_mode == 'Cabo' else mod_analog})"
        ax.set_title(title, fontsize=10, fontweight="bold", color=C["text"], pad=8)

    def _plot_decoded_bits(self, ax, tx_bits, rx_bits, max_bits=120):
        n = min(len(rx_bits), max_bits)
        tx_trim = tx_bits[:n]
        rx_trim = rx_bits[:n]
        x = np.arange(n)

        tx_int = [1 if b else 0 for b in tx_trim]
        rx_int = [1 if b else 0 for b in rx_trim]

        ax.step(x, tx_int, where="post", color="#94a3b8", lw=1.5, label="Esperado", alpha=0.7)
        ax.step(x, rx_int, where="post", color="#16a34a", lw=1.8, label="Decodificado", alpha=0.9)

        errors = sum(1 for a, b in zip(tx_trim, rx_trim) if a != b)
        ax.set_title(
            f"Bits decodificados  ({errors} erro(s) nos primeiros {n} bits)",
            fontsize=10, fontweight="bold", color=C["text"], pad=8,
        )
        ax.set_xlabel("Posição do bit", fontsize=9, color=C["muted"])
        ax.set_ylabel("Valor lógico", fontsize=9, color=C["muted"])
        ax.set_yticks([0, 1])
        ax.set_ylim(-0.3, 1.4)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.5, color=C["grid"])

    # ── Comparação de mensagens ───────────────────────────────────────────────

    def _update_diff_view(self, original: str, recovered: str | None):
        self.text_diff.config(state="normal")
        self.text_diff.delete("1.0", tk.END)

        if recovered is None:
            self.text_diff.insert(tk.END, "Não foi possível recuperar texto.")
            self.text_diff.config(state="disabled")
            return

        max_len = max(len(original), len(recovered))
        for i in range(max_len):
            orig_c = original[i] if i < len(original) else None
            recv_c = recovered[i] if i < len(recovered) else None

            if orig_c is None:
                self.text_diff.insert(tk.END, recv_c, "missing")
            elif recv_c is None:
                self.text_diff.insert(tk.END, orig_c, "bad")
            elif orig_c == recv_c:
                self.text_diff.insert(tk.END, orig_c, "ok")
            else:
                self.text_diff.insert(tk.END, recv_c, "bad")

        self.text_diff.config(state="disabled")

    # ── Eventos ───────────────────────────────────────────────────────────────

    def _on_analog_changed(self, event=None):
        if self.combo_mod_analog.get() == "Nenhum":
            self.combo_mod_digital.config(state="readonly")
            self.lbl_nrz_lock.config(text="")
        else:
            self.combo_mod_digital.set("NRZ-Polar")
            self.combo_mod_digital.config(state="disabled")
            self.lbl_nrz_lock.config(
                text="ℹ  Com portadora ativa, digital trava em NRZ-Polar.",
                foreground=C["accent"],
            )

    def _encode_digital(self, bits, mod_digital):
        if mod_digital == "NRZ-Polar":
            return digital_core.encode_nrz_polar(bits)
        if mod_digital == "Manchester":
            return digital_core.encode_manchester(bits)
        return digital_core.encode_bipolar(bits)

    def _decode_physical_bits(self, noisy_signal, tx_mode, mod_digital, mod_analog):
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

    def _on_transmit_clicked(self):
        message_text = self.entry_message.get()
        if not message_text:
            return

        try:
            media = float(self.entry_media.get())
            desvio = float(self.entry_desvio.get())
        except ValueError:
            self.notebook.select(self.tab_receiver)
            self._process_rx_error("Média (μ) e Desvio (σ) devem ser numéricos.")
            return

        framing_choice = self.combo_framing.get()
        error_choice = self.combo_error.get()
        mod_digital = self.combo_mod_digital.get()
        mod_analog = self.combo_mod_analog.get()

        raw_bits = utils.string_to_bitstream(message_text)
        if raw_bits is None:
            return

        # ── Pipeline enlace ──
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

        self.last_tx_bits = protected_bits
        self.last_original_message = message_text
        self.last_tx_pipeline = {
            "raw_bits": raw_bits,
            "framed_bits": framed_bits,
            "protected_bits": protected_bits,
        }

        # ── Modulação ──
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

        # ── Pipeline visual TX ──
        tx_steps = [
            {
                "num": 1, "title": "Mensagem ASCII",
                "detail": f'Texto de entrada: "{message_text}"  ({len(message_text)} caracteres)',
                "mono": message_text, "mono_lines": 1,
            },
            {
                "num": 2, "title": "Codificação → Bitstream",
                "detail": f"{len(raw_bits)} bits  (8 bits por caractere, MSB primeiro)",
                "mono": self._bits_str(raw_bits), "mono_lines": 2,
            },
            {
                "num": 3, "title": f"Enquadramento — {framing_choice}",
                "detail": f"{len(raw_bits)} → {len(framed_bits)} bits  (cabeçalho, flags ou stuffing)",
                "mono": self._bits_str(framed_bits), "mono_lines": 2,
            },
            {
                "num": 4, "title": f"Resistência a Erros — {error_choice}",
                "detail": f"{len(framed_bits)} → {len(protected_bits)} bits  (paridade, checksum, CRC ou Hamming)",
                "mono": self._bits_str(protected_bits), "mono_lines": 2,
            },
            {
                "num": 5, "title": f"Modulação Digital — {mod_digital}",
                "detail": self._signal_stats(digital_signal),
                "badge": f"{len(protected_bits)} bits", "badge_color": C["accent"],
            },
        ]

        if carrier_signal is not None:
            tx_steps.append({
                "num": 6, "title": f"Modulação Portadora — {mod_analog}",
                "detail": self._signal_stats(carrier_signal),
                "badge": "NRZ → onda", "badge_color": "#7c3aed",
            })
            tx_steps.append({
                "num": 7, "title": "Canal AWGN",
                "detail": f"Ruído gaussiano aplicado  (μ={media}, σ={desvio})  →  sinal enviado ao receptor",
                "badge": tx_mode, "badge_color": C["warning"],
            })
        else:
            tx_steps.append({
                "num": 6, "title": "Canal AWGN (banda base / cabo)",
                "detail": f"Ruído sobre o sinal digital  (μ={media}, σ={desvio})  →  enviado ao receptor",
                "badge": tx_mode, "badge_color": C["warning"],
            })

        self._render_pipeline_steps(self.tx_pipeline_container, tx_steps)

        # ── Gráficos TX ──
        self.ax_tx_digital.clear()
        self._style_axis(
            self.ax_tx_digital,
            f"Sinal digital enviado — {mod_digital}",
            "Amostras / posição", "Tensão (V)",
        )
        self._plot_digital_signal(self.ax_tx_digital, digital_signal, color="#2563eb", label=mod_digital)

        self.ax_tx_carrier.clear()
        if carrier_signal is not None:
            self._style_axis(
                self.ax_tx_carrier,
                f"Sinal portadora enviado — {mod_analog}",
                "Amostras (tempo)", "Amplitude (V)",
            )
            self._plot_waveform(
                self.ax_tx_carrier, carrier_signal,
                color="#7c3aed", label=f"Portadora {mod_analog}",
            )
            self.ax_tx_carrier.legend(loc="upper right", fontsize=8)
        else:
            self._style_axis(
                self.ax_tx_carrier,
                "Modulação portadora — não utilizada",
                "Amostras", "Amplitude (V)",
            )
            self.ax_tx_carrier.text(
                0.5, 0.5,
                "Transmissão em banda base (sem portadora)\nApenas o sinal digital é enviado",
                transform=self.ax_tx_carrier.transAxes, ha="center", va="center",
                color=C["muted"], fontsize=10,
            )

        self.canvas_tx.draw()

        # ── Envio ──
        payload_data = {
            "mod_digital": mod_digital,
            "mod_analog": mod_analog,
            "framing_choice": framing_choice,
            "error_choice": error_choice,
            "clean_signal": signal_to_send,
            "noisy_signal": noisy_signal,
            "tx_mode": tx_mode,
            "message_original": message_text,
            "protected_bit_count": len(protected_bits),
            "pipeline_tx": self.last_tx_pipeline,
            "media": media,
            "desvio": desvio,
        }
        net_core.send_signal_via_socket(payload_data)

    def _process_rx_error(self, msg):
        self.lbl_decoded_msg.config(text="Erro", foreground=C["danger"])
        self._render_pipeline_steps(self.rx_pipeline_container, [{
            "num": "!", "title": "Erro", "detail": msg,
        }])

    def _start_queue_polling(self):
        if self.gui_queue and not self.gui_queue.empty():
            try:
                payload = self.gui_queue.get_nowait()
                self._process_received_payload(payload)
                self.notebook.select(self.tab_receiver)
            except Exception as e:
                print(f"[GUI Error] {e}")

        self.root.after(100, self._start_queue_polling)

    def _process_received_payload(self, payload):
        clean_signal = payload["clean_signal"]
        noisy_signal = payload["noisy_signal"]
        tx_mode = payload["tx_mode"]
        mod_digital = payload["mod_digital"]
        mod_analog = payload["mod_analog"]
        framing_choice = payload["framing_choice"]
        error_choice = payload["error_choice"]
        original_msg = payload.get("message_original", self.last_original_message)
        expected_bit_count = payload.get("protected_bit_count", len(self.last_tx_bits))

        self.lbl_original_msg.config(text=f'"{original_msg}"', foreground=C["text"])

        # ── 1. Demodulação física ──
        rx_bits_full = self._decode_physical_bits(noisy_signal, tx_mode, mod_digital, mod_analog)
        rx_bits = rx_bits_full[:expected_bit_count]
        while len(rx_bits) < expected_bit_count:
            rx_bits.append(False)

        min_len = min(len(self.last_tx_bits), len(rx_bits))
        bit_errors = sum(
            1 for a, b in zip(self.last_tx_bits[:min_len], rx_bits[:min_len]) if a != b
        )
        ber_pct = (bit_errors / min_len * 100) if min_len else 0

        # ── 2. EDC ──
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

        # ── 3. Desenquadramento ──
        if framing_choice == "Contagem de Caracteres":
            raw_payloads = enquadramento.remove_character_count_framing([after_edc])
        elif framing_choice == "Inserção de Bytes":
            raw_payloads = enquadramento.remove_byte_stuffing_framing([after_edc])
        else:
            raw_payloads = enquadramento.remove_bit_stuffing_framing([after_edc])

        payload_bits = []
        for rp in raw_payloads:
            payload_bits.extend(rp)

        # Remove padding de byte alignment (zeros finais do enquadramento)
        raw_original = self.last_tx_pipeline.get("raw_bits", [])
        if raw_original and len(payload_bits) >= len(raw_original):
            final_bits = payload_bits[:len(raw_original)]
        else:
            final_bits = payload_bits
            remainder = len(final_bits) % 8
            if remainder:
                final_bits = final_bits[:-remainder]

        final_text = utils.bitstream_to_string(final_bits) if final_bits else None

        # ── Status lateral ──
        self.lbl_ber.config(
            text=f"BER físico: {bit_errors}/{min_len} bits  ({ber_pct:.1f}%)"
        )

        if edc_error:
            if edc_corrected:
                self.lbl_edc.config(text=f"EDC ({error_choice}): erro corrigido ✓", fg=C["warning"])
            else:
                self.lbl_edc.config(text=f"EDC ({error_choice}): inconsistência detectada ✗", fg=C["danger"])
        else:
            self.lbl_edc.config(text=f"EDC ({error_choice}): integridade OK ✓", fg=C["success"])

        messages_match = final_text == original_msg
        if final_text is None:
            self.lbl_decoded_msg.config(text="[ ilegível ]", foreground=C["danger"])
            self.lbl_match.config(text="Integridade: falha na decodificação", fg=C["danger"])
        elif messages_match:
            self.lbl_decoded_msg.config(text=f'"{final_text}"', foreground=C["success"])
            self.lbl_match.config(text="Integridade: mensagem recuperada com sucesso ✓", fg=C["success"])
        else:
            self.lbl_decoded_msg.config(text=f'"{final_text}"', foreground=C["warning"])
            self.lbl_match.config(text="Integridade: mensagem corrompida ✗", fg=C["danger"])

        self._update_diff_view(original_msg, final_text or "")

        # ── Pipeline visual RX ──
        rx_steps = [
            {
                "num": 1,
                "title": f"Recepção no canal ({tx_mode})",
                "detail": (
                    f"Sinal recebido com ruído AWGN  (μ={payload.get('media', 0)}, "
                    f"σ={payload.get('desvio', 0)})\n{self._signal_stats(noisy_signal)}"
                ),
                "badge": f"{bit_errors} erros físicos", "badge_color": C["danger"] if bit_errors else C["success"],
            },
            {
                "num": 2,
                "title": "Demodulação física",
                "detail": (
                    f"{'Portadora ' + mod_analog + ' → NRZ → ' if tx_mode == 'Ar' else ''}"
                    f"Modulação digital {mod_digital} → {len(rx_bits)} bits recuperados"
                ),
                "mono": self._bits_str(rx_bits), "mono_lines": 2,
            },
            {
                "num": 3,
                "title": f"Verificação EDC — {error_choice}",
                "detail": (
                    ("Erro detectado e corrigido (Hamming)." if edc_corrected else
                     "Inconsistência detectada — bloco possivelmente corrompido." if edc_error else
                     "Bloco validado com sucesso.")
                    + f"\n{len(rx_bits)} → {len(after_edc)} bits (EDC removido)"
                ),
                "badge": "corrigido" if edc_corrected else ("falha" if edc_error else "OK"),
                "badge_color": C["warning"] if edc_corrected else (C["danger"] if edc_error else C["success"]),
                "mono": self._bits_str(after_edc), "mono_lines": 2,
            },
            {
                "num": 4,
                "title": f"Desenquadramento — {framing_choice}",
                "detail": f"{len(after_edc)} → {len(payload_bits)} bits  (cabeçalho/flags removidos)",
                "mono": self._bits_str(payload_bits), "mono_lines": 2,
            },
            {
                "num": 5,
                "title": "Decodificação ASCII",
                "detail": (
                    f'Payload útil: {len(final_bits)} bits\n'
                    f'Texto recuperado: "{final_text}"' if final_text else
                    "Não foi possível decodificar texto ASCII válido."
                ),
                "mono": self._bits_str(final_bits), "mono_lines": 2,
            },
            {
                "num": 6,
                "title": "Comparação final",
                "detail": (
                    f'Original:  "{original_msg}"\n'
                    f'Recebido:  "{final_text or "[vazio]"}"\n'
                    + ("Mensagens idênticas." if messages_match else
                       f"Divergência em {sum(1 for a, b in zip(original_msg, final_text or '') if a != b)} caractere(s).")
                ),
                "badge": "OK" if messages_match else "CORROMPIDO",
                "badge_color": C["success"] if messages_match else C["danger"],
            },
        ]
        self._render_pipeline_steps(self.rx_pipeline_container, rx_steps)

        # ── Gráficos RX ──
        self.ax_rx_signal.clear()
        self._style_axis(self.ax_rx_signal, "", "Amostras", "Amplitude")
        self._plot_rx_signal_overlay(self.ax_rx_signal, clean_signal, noisy_signal, tx_mode, mod_analog)

        self.ax_rx_decoded.clear()
        self._plot_decoded_bits(self.ax_rx_decoded, self.last_tx_bits, rx_bits)

        self.canvas_rx.draw()
