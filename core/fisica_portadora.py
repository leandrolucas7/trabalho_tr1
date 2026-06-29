import numpy as np

def encode_ask(digital_signal: list[int], samples_per_bit: int = 100, cycles_per_bit: int = 2, amplitude: float = 1.0) -> list[float]:
    """
    Transmitter side: Modulates a digital signal into an Amplitude Shift Keying (ASK) wave.
    - +1 (High) -> Sinusoidal wave with full amplitude
    - -1 (Low)  -> Zero amplitude (0.0 / silence)
    """
    wave_signal = []
    
    t = np.linspace(0, cycles_per_bit, samples_per_bit, endpoint=False)
    sine_carrier = amplitude * np.sin(2 * np.pi * t)
    
    for level in digital_signal:
        if level > 0: # +1
            wave_signal.extend(sine_carrier.tolist())
        else:         # -1
            wave_signal.extend([0.0] * samples_per_bit)
            
    return wave_signal


def decode_ask(wave_signal: list[float], samples_per_bit: int = 100, amplitude: float = 1.0) -> list[int]:
    """
    Receiver side: Demodulates an ASK wave signal back into a digital signal (+1 or -1).
    """
    digital_signal = []
    
    ideal_rms = amplitude / np.sqrt(2)
    decision_threshold = ideal_rms / 2
    
    for i in range(0, len(wave_signal), samples_per_bit):
        bit_segment = wave_signal[i:i + samples_per_bit]
        if len(bit_segment) < samples_per_bit:
            break
            
        segment_arr = np.array(bit_segment)
        rms_energy = np.sqrt(np.mean(segment_arr ** 2))
        
        # Returns +1 if signal is strong, -1 if it's silence
        digital_signal.append(1 if rms_energy > decision_threshold else -1)
        
    return digital_signal


def encode_fsk(digital_signal: list[int], samples_per_bit: int = 100) -> list[float]:
    """
    Transmitter side: Modulates a digital signal into a Frequency Shift Keying (FSK) wave.
    - +1 (High) -> High Frequency (4 cycles)
    - -1 (Low)  -> Low Frequency (1 cycle)
    """
    wave_signal = []
    
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
    """
    Receiver side: Demodulates an FSK wave signal back into a digital signal (+1 or -1).
    """
    digital_signal = []
    
    for i in range(0, len(wave_signal), samples_per_bit):
        bit_segment = wave_signal[i:i + samples_per_bit]
        if len(bit_segment) < samples_per_bit:
            break
            
        crossings = 0
        for idx in range(1, len(bit_segment)):
            if bit_segment[idx] * bit_segment[idx - 1] < 0:
                crossings += 1
                
        digital_signal.append(1 if crossings > 5 else -1)
        
    return digital_signal


def encode_qpsk(digital_signal: list[int], samples_per_bit: int = 100) -> list[float]:
    """
    Transmitter side: Modulates a digital signal into a QPSK wave signal.
    Directly multiplies the voltage levels (+1, -1) by the orthogonal carriers.
    """
    # Pad with -1 (equivalent to False) if odd number of elements
    if len(digital_signal) % 2 != 0:
        digital_signal = digital_signal + [-1]
        
    wave_signal = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    carrier_i = np.cos(2 * np.pi * 2 * t)
    carrier_q = np.sin(2 * np.pi * 2 * t)
    
    for i in range(0, len(digital_signal), 2):
        level_i = digital_signal[i]
        level_q = digital_signal[i + 1]
        
        # Mathematical beauty: direct multiplication of voltage by carrier!
        dibit_wave = (level_i * carrier_i) + (level_q * carrier_q)
        wave_signal.extend(dibit_wave.tolist())
        
    return wave_signal


def decode_qpsk(wave_signal: list[float], samples_per_bit: int = 100) -> list[int]:
    """
    Receiver side: Demodulates a QPSK wave signal back into a digital signal (+1 or -1).
    """
    digital_signal = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    ref_i = np.cos(2 * np.pi * 2 * t)
    ref_q = np.sin(2 * np.pi * 2 * t)
    
    for i in range(0, len(wave_signal), samples_per_bit):
        segment = wave_signal[i:i + samples_per_bit]
        if len(segment) < samples_per_bit:
            break
            
        segment_arr = np.array(segment)
        
        recovered_i = np.sum(segment_arr * ref_i) / (samples_per_bit / 2)
        recovered_q = np.sum(segment_arr * ref_q) / (samples_per_bit / 2)
        
        digital_signal.append(1 if recovered_i > 0 else -1)
        digital_signal.append(1 if recovered_q > 0 else -1)
        
    return digital_signal


def encode_16qam(digital_signal: list[int], samples_per_bit: int = 100) -> list[float]:
    """
    Transmitter side: Modulates a digital signal into a 16-QAM wave signal.
    """
    remainder = len(digital_signal) % 4
    if remainder != 0:
        digital_signal = digital_signal + ([-1] * (4 - remainder))
        
    wave_signal = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    carrier_i = np.cos(2 * np.pi * 2 * t)
    carrier_q = np.sin(2 * np.pi * 2 * t)
    
    # Map for digital voltage combinations (-1 and 1) to 16-QAM amplitude levels
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
        
        quadbit_wave = (amp_i * carrier_i) + (amp_q * carrier_q)
        wave_signal.extend(quadbit_wave.tolist())
        
    return wave_signal


def decode_16qam(wave_signal: list[float], samples_per_bit: int = 100) -> list[int]:
    """
    Receiver side: Demodulates a 16-QAM wave signal back into a digital signal (+1 or -1).
    """
    digital_signal = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    ref_i = np.cos(2 * np.pi * 2 * t)
    ref_q = np.sin(2 * np.pi * 2 * t)
    
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