import numpy as np

def encode_ask(digital_signal: list[int], samples_per_bit: int = 100, cycles_per_bit: int = 2, amplitude: float = 1.0) -> list[float]:
    """Modula um sinal digital em ASK, ligando a portadora quando o nível é alto e anulando quando é baixo."""
    wave_signal = []
    
    # Gera uma senoide de referência para um bit inteiro.
    t = np.linspace(0, cycles_per_bit, samples_per_bit, endpoint=False)
    sine_carrier = amplitude * np.sin(2 * np.pi * t)
    
    for level in digital_signal:
        if level > 0:  # Nível alto: transmite a portadora.
            wave_signal.extend(sine_carrier.tolist())
        else:          # Nível baixo: transmite silêncio.
            wave_signal.extend([0.0] * samples_per_bit)
            
    return wave_signal


def decode_ask(wave_signal: list[float], samples_per_bit: int = 100, amplitude: float = 1.0) -> list[int]:
    """Demodula ASK usando energia RMS para distinguir portadora presente de ausência de sinal."""
    digital_signal = []
    
    # Calcula o RMS ideal da portadora e define um limiar simples de decisão.
    ideal_rms = amplitude / np.sqrt(2)
    decision_threshold = ideal_rms / 2
    
    for i in range(0, len(wave_signal), samples_per_bit):
        bit_segment = wave_signal[i:i + samples_per_bit]
        if len(bit_segment) < samples_per_bit:
            break
            
        segment_arr = np.array(bit_segment)
        rms_energy = np.sqrt(np.mean(segment_arr ** 2))
        
        # Se a energia ficar acima do limiar, interpreta como bit alto; caso contrário, bit baixo.
        digital_signal.append(1 if rms_energy > decision_threshold else -1)
        
    return digital_signal


def encode_fsk(digital_signal: list[int], samples_per_bit: int = 100) -> list[float]:
    """Modula um sinal digital em FSK, alternando entre duas frequências diferentes."""
    wave_signal = []
    
    # Cada bit recebe um trecho de mesmo comprimento, mas com frequência diferente.
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    low_freq_carrier = np.sin(2 * np.pi * 1 * t)
    high_freq_carrier = np.sin(2 * np.pi * 4 * t)
    
    for level in digital_signal:
        if level > 0:
            wave_signal.extend(high_freq_carrier.tolist())
        else:
            wave_signal.extend(low_freq_carrier.tolist())
            
    return wave_signal


def decode_fsk(wave_signal: list[float], samples_per_bit: int = 100) -> list[int]:
    """Demodula FSK contando cruzamentos por zero para identificar a frequência dominante."""
    digital_signal = []
    
    for i in range(0, len(wave_signal), samples_per_bit):
        bit_segment = wave_signal[i:i + samples_per_bit]
        if len(bit_segment) < samples_per_bit:
            break
            
        crossings = 0
        for idx in range(1, len(bit_segment)):
            if bit_segment[idx] * bit_segment[idx - 1] < 0:
                crossings += 1
                
        # Mais cruzamentos por zero indicam a frequência alta; menos cruzamentos indicam a baixa.
        digital_signal.append(1 if crossings > 5 else -1)
        
    return digital_signal


def encode_qpsk(digital_signal: list[int], samples_per_bit: int = 100) -> list[float]:
    """Modula pares de bits em QPSK, usando componentes ortogonais I e Q."""
    # Completa com -1 caso exista quantidade ímpar de símbolos para manter o pareamento.
    if len(digital_signal) % 2 != 0:
        digital_signal = digital_signal + [-1]
        
    wave_signal = []
    # Gera as portadoras ortogonais para I e Q.
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    carrier_i = np.cos(2 * np.pi * 2 * t)
    carrier_q = np.sin(2 * np.pi * 2 * t)
    
    for i in range(0, len(digital_signal), 2):
        level_i = digital_signal[i]
        level_q = digital_signal[i + 1]
        
        # Cada par de níveis modula diretamente as portadoras em fase e em quadratura.
        dibit_wave = (level_i * carrier_i) + (level_q * carrier_q)
        wave_signal.extend(dibit_wave.tolist())
        
    return wave_signal


def decode_qpsk(wave_signal: list[float], samples_per_bit: int = 100) -> list[int]:
    """Demodula QPSK recuperando os componentes I e Q por correlação com as portadoras de referência."""
    digital_signal = []
    # Usa as mesmas referências do transmissor para medir a energia projetada em I e Q.
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    ref_i = np.cos(2 * np.pi * 2 * t)
    ref_q = np.sin(2 * np.pi * 2 * t)
    
    for i in range(0, len(wave_signal), samples_per_bit):
        segment = wave_signal[i:i + samples_per_bit]
        if len(segment) < samples_per_bit:
            break
            
        segment_arr = np.array(segment)
        
        # Calcula quanto do sinal recebido “bate” com cada eixo da modulação.
        recovered_i = np.sum(segment_arr * ref_i) / (samples_per_bit / 2)
        recovered_q = np.sum(segment_arr * ref_q) / (samples_per_bit / 2)
        
        digital_signal.append(1 if recovered_i > 0 else -1)
        digital_signal.append(1 if recovered_q > 0 else -1)
        
    return digital_signal


def encode_16qam(digital_signal: list[int], samples_per_bit: int = 100) -> list[float]:
    """Modula quatro bits por símbolo em 16-QAM, mapeando combinações binárias para níveis de amplitude."""
    remainder = len(digital_signal) % 4
    if remainder != 0:
        # Completa com -1 para que a quantidade de bits seja múltipla de 4.
        digital_signal = digital_signal + ([-1] * (4 - remainder))
        
    wave_signal = []
    # Usa as mesmas portadoras ortogonais do QPSK como base do 16-QAM.
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    carrier_i = np.cos(2 * np.pi * 2 * t)
    carrier_q = np.sin(2 * np.pi * 2 * t)
    
    # Mapeia combinações de dois bits para níveis de amplitude em I e Q.
    level_map = {
        (-1, -1): -3.0,
        (-1,  1): -1.0,
        ( 1,  1):  1.0,
        ( 1, -1):  3.0
    }
    
    for i in range(0, len(digital_signal), 4):
        v1, v2, v3, v4 = digital_signal[i:i+4]
        
        amp_i = level_map[(v1, v2)]
        amp_q = level_map[(v3, v4)]
        
        # Combina os dois pares de bits em uma única forma de onda de 16-QAM.
        quadbit_wave = (amp_i * carrier_i) + (amp_q * carrier_q)
        wave_signal.extend(quadbit_wave.tolist())
        
    return wave_signal


def decode_16qam(wave_signal: list[float], samples_per_bit: int = 100) -> list[int]:
    """Demodula 16-QAM estimando os níveis de amplitude em I e Q e convertendo-os em pares de bits."""
    digital_signal = []
    # Recria as referências usadas na modulação para medir as projeções de I e Q.
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    ref_i = np.cos(2 * np.pi * 2 * t)
    ref_q = np.sin(2 * np.pi * 2 * t)
    
    # Converte o valor estimado em cada eixo de volta para um par de bits.
    def slice_level(value: float) -> list[int]:
        if value < -2.0:
            return [-1, -1]
        elif value < 0.0:
            return [-1,  1]
        elif value < 2.0:
            return [ 1,  1]
        else:
            return [ 1, -1]

    for i in range(0, len(wave_signal), samples_per_bit):
        segment = wave_signal[i:i + samples_per_bit]
        if len(segment) < samples_per_bit:
            break
            
        segment_arr = np.array(segment)
        
        raw_i = np.sum(segment_arr * ref_i) / (samples_per_bit / 2)
        raw_q = np.sum(segment_arr * ref_q) / (samples_per_bit / 2)
        
        digital_signal.extend(slice_level(raw_i))
        digital_signal.extend(slice_level(raw_q))
        
    return digital_signal