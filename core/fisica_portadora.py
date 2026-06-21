import numpy as np

def encode_ask(bitstream: list[bool], samples_per_bit: int = 100, cycles_per_bit: int = 2, amplitude: float = 1.0) -> list[float]:
    """
    Transmitter side: Modulates a bitstream into an Amplitude Shift Keying (ASK) wave.
    - True (1)  -> Sinusoidal wave with full amplitude
    - False (0) -> Zero amplitude (0.0 / silence)
    """
    wave_signal = []
    
    # Time array for a single bit period, broken down into 'samples_per_bit' points
    t = np.linspace(0, cycles_per_bit, samples_per_bit, endpoint=False)
    # The pure sine wave carrier scaled by the requested amplitude
    sine_carrier = amplitude * np.sin(2 * np.pi * t)
    
    for bit in bitstream:
        if bit:
            wave_signal.extend(sine_carrier.tolist())
        else:
            wave_signal.extend([0.0] * samples_per_bit)
            
    return wave_signal


def decode_ask(wave_signal: list[float], samples_per_bit: int = 100, amplitude: float = 1.0) -> list[bool]:
    """
    Receiver side: Demodulates an ASK wave signal back into a logical bitstream.
    Calculates the Root Mean Square (RMS) energy of each bit segment.
    """
    bitstream = []
    
    # An ideal sine wave with peak 'A' has an RMS value of A / sqrt(2).
    # We dynamically set our threshold at half of the ideal RMS value 
    # to protect the decision against noise.
    ideal_rms = amplitude / np.sqrt(2)
    decision_threshold = ideal_rms / 2
    
    for i in range(0, len(wave_signal), samples_per_bit):
        bit_segment = wave_signal[i:i + samples_per_bit]
        if len(bit_segment) < samples_per_bit:
            break
            
        segment_arr = np.array(bit_segment)
        # Root Mean Square (RMS) energy calculation: sqrt(mean(squares))
        rms_energy = np.sqrt(np.mean(segment_arr ** 2))
        
        # Decide based on our dynamic threshold
        bitstream.append(rms_energy > decision_threshold)
        
    return bitstream


def encode_fsk(bitstream: list[bool], samples_per_bit: int = 100) -> list[float]:
    """
    Transmitter side: Modulates a bitstream into a Frequency Shift Keying (FSK) wave.
    - True (1)  -> High Frequency (4 cycles per bit period)
    - False (0) -> Low Frequency (1 cycle per bit period)
    """
    wave_signal = []
    
    # 1. Create the two target frequency carriers based on the number of cycles
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    low_freq_carrier = np.sin(2 * np.pi * 1 * t)   # 1 cycle (False)
    high_freq_carrier = np.sin(2 * np.pi * 4 * t)  # 4 cycles (True)
    
    # 2. Map each bit to its respective frequency array
    for bit in bitstream:
        if bit:
            wave_signal.extend(high_freq_carrier.tolist())
        else:
            wave_signal.extend(low_freq_carrier.tolist())
            
    return wave_signal


def decode_fsk(wave_signal: list[float], samples_per_bit: int = 100) -> list[bool]:
    """
    Receiver side: Demodulates an FSK wave signal back into a logical bitstream.
    Counts the number of zero-crossings in each bit segment to determine the frequency.
    """
    bitstream = []
    
    # Process the wave segment by segment
    for i in range(0, len(wave_signal), samples_per_bit):
        bit_segment = wave_signal[i:i + samples_per_bit]
        if len(bit_segment) < samples_per_bit:
            break
            
        # Count Zero Crossings: how many times the signal crosses the X-axis
        # We check where the sign flips from positive to negative or vice-versa
        crossings = 0
        for idx in range(1, len(bit_segment)):
            # If the product of consecutive samples is negative, a zero-crossing occurred
            if bit_segment[idx] * bit_segment[idx - 1] < 0:
                crossings += 1
                
        # A low frequency (1 cycle) has about 2 zero-crossings per bit window.
        # A high frequency (4 cycles) has about 8 zero-crossings.
        # We set a threshold in the middle (e.g., 5) to safely decide under noise!
        bitstream.append(crossings > 5)
        
    return bitstream


def encode_qpsk(bitstream: list[bool], samples_per_bit: int = 100) -> list[float]:
    """
    Transmitter side: Modulates a bitstream into a QPSK wave signal.
    Groups bits 2 by 2 (dibits) to control two orthogonal carrier signals (I and Q).
    """
    # If the bitstream has an odd number of bits, pad it with a False (0) bit
    if len(bitstream) % 2 != 0:
        bitstream = bitstream + [False]
        
    wave_signal = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    # Generate our two orthogonal base carriers
    carrier_i = np.cos(2 * np.pi * 2 * t)  # In-phase component (X axis)
    carrier_q = np.sin(2 * np.pi * 2 * t)  # Quadrature component (Y axis)
    
    # Process bits in pairs (steps of 2)
    for i in range(0, len(bitstream), 2):
        bit_i = bitstream[i]      # First bit determines In-phase amplitude
        bit_q = bitstream[i + 1]  # Second bit determines Quadrature amplitude
        
        # Map True to +1.0 and False to -1.0
        amp_i = 1.0 if bit_i else -1.0
        amp_q = 1.0 if bit_q else -1.0
        
        # Combine the two orthogonal waves into a single physical signal block
        dibit_wave = (amp_i * carrier_i) + (amp_q * carrier_q)
        wave_signal.extend(dibit_wave.tolist())
        
    return wave_signal


def decode_qpsk(wave_signal: list[float], samples_per_bit: int = 100) -> list[bool]:
    """
    Receiver side: Demodulates a QPSK wave signal back into a logical bitstream.
    Correlates the received window with reference I and Q signals to find the quadrant.
    """
    bitstream = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    # Local references for demodulation correlation
    ref_i = np.cos(2 * np.pi * 2 * t)
    ref_q = np.sin(2 * np.pi * 2 * t)
    
    for i in range(0, len(wave_signal), samples_per_bit):
        segment = wave_signal[i:i + samples_per_bit]
        if len(segment) < samples_per_bit:
            break
            
        segment_arr = np.array(segment)
        
        # Integrate (multiply and sum) to recover the original I and Q energy levels
        # This is a classic mathematical dot-product correlation
        recovered_i = np.sum(segment_arr * ref_i) / (samples_per_bit / 2)
        recovered_q = np.sum(segment_arr * ref_q) / (samples_per_bit / 2)
        
        # If the recovered coordination is positive, the bit was True (1), else False (0)
        bitstream.append(recovered_i > 0)
        bitstream.append(recovered_q > 0)
        
    return bitstream


def encode_16qam(bitstream: list[bool], samples_per_bit: int = 100) -> list[float]:
    """
    Transmitter side: Modulates a bitstream into a 16-QAM wave signal.
    Groups bits 4 by 4 (quadbits) to control amplitude combinations on orthogonal carriers.
    """
    # Ensure the bitstream length is a multiple of 4 by padding with False bits
    remainder = len(bitstream) % 4
    if remainder != 0:
        bitstream = bitstream + ([False] * (4 - remainder))
        
    wave_signal = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    # Mathematical orthogonal carriers (2 cycles per bit slot)
    carrier_i = np.cos(2 * np.pi * 2 * t)
    carrier_q = np.sin(2 * np.pi * 2 * t)
    
    # Map for 2-bit combinations to 16-QAM amplitude levels (-3, -1, 1, 3)
    level_map = {
        (False, False): -3.0,
        (False, True):  -1.0,
        (True, True):   1.0,
        (True, False):  3.0
    }
    
    # Process bits in groups of 4
    for i in range(0, len(bitstream), 4):
        # Slice the 4 bits
        b1, b2, b3, b4 = bitstream[i:i+4]
        
        # Determine amplitudes for In-phase and Quadrature paths
        amp_i = level_map[(b1, b2)]
        amp_q = level_map[(b3, b4)]
        
        # Modulate and fuse into the final physical wave segment
        quadbit_wave = (amp_i * carrier_i) + (amp_q * carrier_q)
        wave_signal.extend(quadbit_wave.tolist())
        
    return wave_signal


def decode_16qam(wave_signal: list[float], samples_per_bit: int = 100) -> list[bool]:
    """
    Receiver side: Demodulates a 16-QAM wave signal back into a logical bitstream.
    Extracts I and Q coordinates and uses threshold slicing to decode the 4 bits.
    """
    bitstream = []
    t = np.linspace(0, 1, samples_per_bit, endpoint=False)
    
    ref_i = np.cos(2 * np.pi * 2 * t)
    ref_q = np.sin(2 * np.pi * 2 * t)
    
    # Helper to decode a captured continuous coordinate back to 2 logical bits
    def slice_level(value: float) -> list[bool]:
        # Threshold decision zones: boundaries at -2.0, 0.0, and 2.0
        if value < -2.0:
            return [False, False]  # Corresponds to -3.0
        elif value < 0.0:
            return [False, True]   # Corresponds to -1.0
        elif value < 2.0:
            return [True, True]    # Corresponds to 1.0
        else:
            return [True, False]   # Corresponds to 3.0

    for i in range(0, len(wave_signal), samples_per_bit):
        segment = wave_signal[i:i + samples_per_bit]
        if len(segment) < samples_per_bit:
            break
            
        segment_arr = np.array(segment)
        
        # Correlate to extract the absolute scaling value on each axis
        raw_i = np.sum(segment_arr * ref_i) / (samples_per_bit / 2)
        raw_q = np.sum(segment_arr * ref_q) / (samples_per_bit / 2)
        
        # Slice coordinates to extract the 4 bits
        bitstream.extend(slice_level(raw_i))
        bitstream.extend(slice_level(raw_q))
        
    return bitstream
