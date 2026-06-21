def encode_nrz_polar(bitstream: list[bool]) -> list[int]:
    """
    Transmitter side: Encodes a logical bitstream into an NRZ-Polar digital signal.
    Maps:
        - True (1)  -> +1 (Positive Voltage)
        - False (0) -> -1 (Negative Voltage)
    """
    # Using a clean list comprehension: 1 if bit is True, else -1
    return [1 if bit else -1 for bit in bitstream]


def decode_nrz_polar(digital_signal: list[int]) -> list[bool]:
    """
    Receiver side: Decodes an NRZ-Polar digital signal back into a logical bitstream.
    Maps:
        - +1 -> True (1)
        - -1 -> False (0)
    """
    # Any voltage level greater than 0 is treated as True, otherwise False
    return [bit > 0 for bit in digital_signal]


def encode_manchester(bitstream: list[bool]) -> list[int]:
    """
    Transmitter side: Encodes a logical bitstream into a Manchester digital signal (IEEE 802.3).
    Each bit is mapped to a transition in the middle of its period:
        - False (0) -> High to Low (+1 followed by -1)
        - True (1)  -> Low to High (-1 followed by +1)
    """
    digital_signal = []
    
    for bit in bitstream:
        if bit:
            # True (1): Transition from Low (-1) to High (+1)
            digital_signal.extend([-1, 1])
        else:
            # False (0): Transition from High (+1) to Low (-1)
            digital_signal.extend([1, -1])
            
    return digital_signal


def decode_manchester(digital_signal: list[int]) -> list[bool]:
    """
    Receiver side: Decodes a Manchester digital signal back into a logical bitstream.
    Analyzes the signal in 2-element segments to detect the direction of the transition:
        - [+1, -1] -> High to Low -> False (0)
        - [-1, +1] -> Low to High -> True (1)
    """
    bitstream = []
    
    # Iterate through the signal in steps of 2 elements
    for i in range(0, len(digital_signal), 2):
        if i + 1 < len(digital_signal):
            first_half = digital_signal[i]
            second_half = digital_signal[i + 1]
            
            # If the transition goes up (ends positive), it's a True (1)
            # If it goes down (ends negative), it's a False (0)
            bitstream.append(second_half > first_half)
            
    return bitstream


def encode_bipolar(bitstream: list[bool]) -> list[int]:
    """
    Transmitter side: Encodes a logical bitstream into a Bipolar (AMI) signal.
    Maps:
        - False (0) -> Always 0
        - True (1)  -> Alternates between +1 and -1 for every occurrence.
    """
    digital_signal = []
    # Start with positive polarity (+1) for the first 'True' bit found
    next_polarity = 1
    
    for bit in bitstream:
        if bit:
            # Append the current alternating polarity (+1 or -1)
            digital_signal.append(next_polarity)
            # Flip the polarity for the next 'True' bit (1 becomes -1, -1 becomes 1)
            next_polarity = -next_polarity
        else:
            # False bits are always mapped to zero volts
            digital_signal.append(0)
            
    return digital_signal


def decode_bipolar(digital_signal: list[int]) -> list[bool]:
    """
    Receiver side: Decodes a Bipolar (AMI) digital signal back into a bitstream.
    Maps:
        - 0       -> False (0)
        - +1 / -1 -> True (1)
    """
    # If the absolute value of the signal is non-zero, it represents a True bit
    return [abs(level) != 0 for level in digital_signal]
