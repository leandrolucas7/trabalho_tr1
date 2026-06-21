from math import ceil

def split_bitstream_into_payloads(bitstream: list[bool], payload_size: int) -> list[list[bool]]:
    """
    Splits a continuous flat bitstream into multiple fixed-size payloads.
    Each sub-list represents the raw data body for an individual frame.
    """
    payloads = []
    # Calculate the total number of chunks needed, rounding up for any remainder
    num_payloads = ceil(len(bitstream) / payload_size)
    
    for i in range(num_payloads):
        # Calculate the start and end boundary indices for the current slice
        start = i * payload_size
        end = start + payload_size
        
        # Slice the bitstream and append the isolated payload chunk
        payloads.append(bitstream[start:end])
        
    return payloads


def add_character_count_framing(payloads: list[list[bool]]) -> list[list[bool]]:
    """
    Transmitter side: Prepends an 8-bit length header to each payload.
    The header value represents the total number of bytes (8-bit segments) 
    inside the final frame, including the header itself.
    """
    framed_payloads = []
    
    for payload in payloads:
        # 1. Align the payload to an 8-bit (1 byte) boundary
        # If a payload has 13 bits, we pad it with 3 False (0) bits to make it 16 bits (2 bytes)
        padding_needed = (8 - (len(payload) % 8)) % 8
        padded_payload = payload + ([False] * padding_needed)
        
        # 2. Calculate the total frame size in bytes
        # Total bytes = (payload bits / 8) + 1 byte reserved for the count header itself
        total_bytes = (len(padded_payload) // 8) + 1
        
        # 3. Convert the integer count into an 8-bit binary list
        # Example: if total_bytes is 5, binary_str becomes "00000101"
        binary_str = f'{total_bytes:08b}'
        header = [character == '1' for character in binary_str]
        
        # 4. Assemble the frame: [HEADER (8 bits)] + [PAYLOAD DATA]
        framed_payloads.append(header + padded_payload)
        
    return framed_payloads


def remove_character_count_framing(framed_payloads: list[list[bool]]) -> list[list[bool]]:
    """
    Receiver side: Reads the first 8 bits of each frame to extract the total byte count,
    then retrieves the raw payload data by stripping away the header.
    """
    raw_payloads = []
    
    for frame in framed_payloads:
        # A valid frame must at least contain the 8-bit header
        if len(frame) < 8:
            continue
            
        # 1. Extract the first 8 bits (the length header)
        header_bits = frame[:8]
        
        # 2. Convert the boolean header bits back into a binary string
        binary_str = "".join(['1' if bit else '0' for bit in header_bits])
        
        # 3. Parse the binary string into a base-10 integer (total bytes expected)
        total_bytes_expected = int(binary_str, 2)
        
        # 4. Extract the payload data
        # The payload starts at bit index 8 and ends at (total_bytes_expected * 8)
        payload_data = frame[8 : total_bytes_expected * 8]
        raw_payloads.append(payload_data)
        
    return raw_payloads


def add_byte_stuffing_framing(payloads: list[list[bool]]) -> list[list[bool]]:
    """
    Transmitter side: Wraps each payload between FLAG patterns (0x7E).
    If a FLAG or an ESCAPE (0x7D) pattern appears inside the original data,
    an ESCAPE pattern is byte-stuffed (inserted) right before it.
    """
    # Define our 8-bit patterns for control bytes
    FLAG_PATTERN = [False, True, True, True, True, True, True, False]   # 0x7E
    ESC_PATTERN  = [False, True, True, True, True, True, False, True]   # 0x7D
    
    framed_payloads = []
    
    for payload in payloads:
        # 1. Align the payload to an 8-bit (1 byte) boundary
        padding_needed = (8 - (len(payload) % 8)) % 8
        padded_payload = payload + ([False] * padding_needed)
        
        stuffed_payload = []
        
        # 2. Process the payload byte by byte (8-bit steps)
        for i in range(0, len(padded_payload), 8):
            current_byte = padded_payload[i:i+8]
            
            # If the current byte matches FLAG or ESC, prepend an ESC pattern
            if current_byte == FLAG_PATTERN or current_byte == ESC_PATTERN:
                stuffed_payload.extend(ESC_PATTERN)
                
            stuffed_payload.extend(current_byte)
            
        # 3. Encapsulate the stuffed payload: [FLAG] + [DATA] + [FLAG]
        final_frame = FLAG_PATTERN + stuffed_payload + FLAG_PATTERN
        framed_payloads.append(final_frame)
        
    return framed_payloads


def remove_byte_stuffing_framing(framed_payloads: list[list[bool]]) -> list[list[bool]]:
    """
    Receiver side: Strips away the boundary FLAG patterns.
    Iterates through the frame and removes any ESCAPE pattern that was stuffed,
    treating the byte immediately following the ESCAPE as literal data.
    """
    FLAG_PATTERN = [False, True, True, True, True, True, True, False]   # 0x7E
    ESC_PATTERN  = [False, True, True, True, True, True, False, True]   # 0x7D
    
    raw_payloads = []
    
    for frame in framed_payloads:
        # A valid frame must have at least an opening FLAG and a closing FLAG (16 bits)
        if len(frame) < 16:
            continue
            
        # Strip the outer boundary FLAGS by analyzing only the inner data
        # frame[8:-8] removes the first 8 bits and the last 8 bits
        inner_data = frame[8:-8]
        clean_payload = []
        
        skip_next_byte = False
        i = 0
        
        while i + 8 <= len(inner_data):
            current_byte = inner_data[i:i+8]
            
            if skip_next_byte:
                # This byte was escaped, so we accept it as literal data without checking
                clean_payload.extend(current_byte)
                skip_next_byte = False
                i += 8
            elif current_byte == ESC_PATTERN:
                # We found a stuffed ESC pattern! 
                # We skip appending this ESC and tell the loop to treat the next byte literally
                skip_next_byte = True
                i += 8
            else:
                # Regular data byte, append normally
                clean_payload.extend(current_byte)
                i += 8
                
        raw_payloads.append(clean_payload)
        
    return raw_payloads


def add_bit_stuffing_framing(payloads: list[list[bool]]) -> list[list[bool]]:
    """
    Transmitter side: Performs bit-oriented framing with bit stuffing.
    Appends the universal FLAG sequence (01111110) to the start and end of the frame.
    Whenever five consecutive True (1) bits occur in the payload, a False (0) bit 
    is tightly stuffed into the stream to prevent accidental flags.
    """
    FLAG_PATTERN = [False, True, True, True, True, True, True, False]  # 01111110
    framed_payloads = []
    
    for payload in payloads:
        stuffed_payload = []
        consecutive_ones = 0
        
        for bit in payload:
            stuffed_payload.append(bit)
            
            if bit:
                consecutive_ones += 1
                # After five consecutive True bits, inject a False bit
                if consecutive_ones == 5:
                    stuffed_payload.append(False)
                    consecutive_ones = 0
            else:
                consecutive_ones = 0
                
        # Encapsulate the bit-stuffed payload between boundary flags
        final_frame = FLAG_PATTERN + stuffed_payload + FLAG_PATTERN
        framed_payloads.append(final_frame)
        
    return framed_payloads


def remove_bit_stuffing_framing(framed_payloads: list[list[bool]]) -> list[list[bool]]:
    """
    Receiver side: Strips boundary flags and removes stuffed False (0) bits.
    If five consecutive True bits are found, the subsequent False bit is discarded.
    """
    raw_payloads = []
    
    for frame in framed_payloads:
        # A valid frame must contain at least the opening and closing flags (16 bits)
        if len(frame) < 16:
            continue
            
        # Strip the boundary flags [8:-8]
        inner_bits = frame[8:-8]
        clean_payload = []
        
        consecutive_ones = 0
        i = 0
        
        while i < len(inner_bits):
            bit = inner_bits[i]
            
            if consecutive_ones == 5:
                # We reached 5 consecutive ones! 
                # According to bit stuffing rules, the current bit MUST be a stuffed False (0).
                # We skip appending this bit and reset the counter.
                consecutive_ones = 0
                i += 1
                continue
                
            clean_payload.append(bit)
            
            if bit:
                consecutive_ones += 1
            else:
                consecutive_ones = 0
                
            i += 1
            
        raw_payloads.append(clean_payload)
        
    return raw_payloads
