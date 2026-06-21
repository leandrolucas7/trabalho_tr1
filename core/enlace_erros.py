def add_even_parity(frame: list[bool]) -> list[bool]:
    """
    Transmitter side: Counts the number of True (1) bits in the frame.
    Appends a single parity bit at the end to ensure the total count of True bits is always even.
    """
    # sum() counts True as 1 and False as 0
    total_ones = sum(frame)
    
    # If total_ones is odd, total_ones % 2 is 1 (True), so we append True to make it even.
    # If total_ones is even, total_ones % 2 is 0 (False), so we append False to keep it even.
    parity_bit = bool(total_ones % 2)
    
    return frame + [parity_bit]


def verify_and_remove_even_parity(frame: list[bool]) -> tuple[list[bool], bool]:
    """
    Receiver side: Verifies the integrity of the frame using even parity.
    
    Returns a tuple containing:
        - The clean frame with the parity bit removed.
        - A boolean flag indicating if an error was detected (True if error, False if clean).
    """
    if len(frame) == 0:
        return [], True
        
    # 1. Count all ones including the parity bit
    total_ones = sum(frame)
    
    # If the sum is odd (total_ones % 2 != 0), an error definitely occurred.
    error_detected = bool(total_ones % 2)
    
    # 2. Extract the clean data payload by stripping the last bit
    clean_frame = frame[:-1]
    
    return clean_frame, error_detected


def add_checksum(frame: list[bool]) -> list[bool]:
    """
    Transmitter side: Computes an 8-bit one's complement checksum.
    Divides the frame into 8-bit segments, sums them up, inverts the result,
    and appends this 8-bit checksum code to the end of the frame.
    """
    # 1. Ensure the frame is perfectly aligned to an 8-bit segment boundary
    padding_needed = (8 - (len(frame) % 8)) % 8
    padded_frame = frame + ([False] * padding_needed)
    
    checksum_accumulator = 0
    
    # 2. Sum all 8-bit segments as integers
    for i in range(0, len(padded_frame), 8):
        segment = padded_frame[i:i+8]
        # Reusing our manual bit-shifting register logic to get the integer value
        segment_value = 0
        for bit in segment:
            segment_value = (segment_value << 1) | int(bit)
        checksum_accumulator += segment_value
        
    # 3. Handle the carry (wrap-around overflow) for an 8-bit architecture
    # While the number takes more than 8 bits, add the overflow part to the lower 8 bits
    while checksum_accumulator > 0xFF:
        carry = checksum_accumulator >> 8
        checksum_accumulator = (checksum_accumulator & 0xFF) + carry
        
    # 4. Apply one's complement (invert all 8 bits)
    # 0xFF is 255 (11111111). Subtracting our value from 255 flips all its bits!
    checksum_final_value = 0xFF - checksum_accumulator
    
    # 5. Convert the final checksum integer back to an 8-bit boolean list
    checksum_bits = [bool((checksum_final_value >> i) & 1) for i in range(7, -1, -1)]
    
    return padded_frame + checksum_bits


def verify_and_remove_checksum(frame: list[bool]) -> tuple[list[bool], bool]:
    """
    Receiver side: Verifies the integrity of the frame by summing all segments,
    including the received checksum segment at the tail.
    
    Returns a tuple with the clean frame (without checksum) and an error boolean flag.
    """
    # A valid frame must at least contain the 8-bit data segment + 8-bit checksum segment
    if len(frame) < 16 or len(frame) % 8 != 0:
        return [], True
        
    checksum_accumulator = 0
    
    # 1. Sum ALL segments including the checksum byte at the end
    for i in range(0, len(frame), 8):
        segment = frame[i:i+8]
        segment_value = 0
        for bit in segment:
            segment_value = (segment_value << 1) | int(bit)
        checksum_accumulator += segment_value
        
    # 2. Handle carry overflow wrap-around
    while checksum_accumulator > 0xFF:
        carry = checksum_accumulator >> 8
        checksum_accumulator = (checksum_accumulator & 0xFF) + carry
        
    # 3. Verify the result
    # If the one's complement sum is correct, the accumulator MUST be exactly 0xFF (11111111)
    # Inverting it (0xFF - accumulator) must yield exactly 0 (no errors).
    error_detected = (0xFF - checksum_accumulator) != 0
    
    # 4. Remove the last 8 bits (the checksum segment) to return clean data
    clean_frame = frame[:-8]
    
    return clean_frame, error_detected


def add_crc32(frame: list[bool]) -> list[bool]:
    """
    Transmitter side: Computes a 32-bit Cyclic Redundancy Check (CRC-32) 
    using the IEEE 802 polynomial (0x04C11DB7).
    Appends the 32-bit remainder code to the end of the frame.
    """
    # IEEE 802.3 generator polynomial coefficients:
    # x^32 + x^26 + x^23 + x^22 + x^16 + x^12 + x^11 + x^10 + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1
    # Represented in binary, it requires 33 bits (MSB is 1, followed by 0x04C11DB7)
    POLYNOMIAL_33BITS = [
        True, False, False, False, False, True, False, False,
        True, True, False, False, False, False, False, True,
        False, False, False, True, True, True, False, True,
        True, False, True, True, False, True, True, True, True
    ]

    # 1. Append 32 zeros as a placeholder for the CRC remainder
    dividend = frame + ([False] * 32)
    
    # 2. Copy the first 33 bits to initialize our division remainder register
    remainder = dividend[:33]
    
    # 3. Long division loop using bitwise XOR operations
    for i in range(33, len(dividend)):
        # If the leading bit (MSB) of the remainder is 1 (True), we apply XOR with the polynomial
        if remainder[0]:
            remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        
        # Shift the register left by 1 bit and pull in the next bit from the dividend
        remainder = remainder[1:] + [dividend[i]]
        
    # 4. Final mathematical check for the last remaining block
    if remainder[0]:
        remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        
    # Drop the overflow bit to get the exact 32-bit final checksum
    crc_32_bits = remainder[1:]
    
    # Return the original frame tightly bound with its signature
    return frame + crc_32_bits


def verify_and_remove_crc32(frame: list[bool]) -> tuple[list[bool], bool]:
    """
    Receiver side: Verifies the frame integrity by dividing the entire block
    (data + received CRC) by the IEEE 802 polynomial.
    
    Returns a tuple with the clean frame and an error boolean flag (True if corrupted).
    """
    # A valid frame must at least contain the 32 bits of the CRC signature
    if len(frame) <= 32:
        return [], True
        
    POLYNOMIAL_33BITS = [
        True, False, False, False, False, True, False, False,
        True, True, False, False, False, False, False, True,
        False, False, False, True, True, True, False, True,
        True, False, True, True, False, True, True, True, True
    ]
    
    # 1. The dividend is the entire frame that arrived
    remainder = frame[:33]
    
    # 2. Run the exact same polynomial long division
    for i in range(33, len(frame)):
        if remainder[0]:
            remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        remainder = remainder[1:] + [frame[i]]
        
    if remainder[0]:
        remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        
    # 3. Check the remainder: if ANY bit inside the remainder is True (1), an error occurred!
    error_detected = any(remainder[1:])
    
    # 4. Remove the 32 bits of CRC from the tail to recover the original clean data
    clean_frame = frame[:-32]
    
    return clean_frame, error_detected


def add_hamming(frame: list[bool]) -> list[bool]:
    """
    Transmitter side: Embeds Hamming code error-correcting parity bits 
    into the frame at positions that are powers of two (1, 2, 4, 8, etc.).
    """
    m = len(frame)  # Number of data bits
    r = 0           # Number of required parity bits
    
    # Calculate how many parity bits are needed using the formula: 2^r >= m + r + 1
    while (2 ** r) < (m + r + 1):
        r += 1
        
    hamming_code = []
    data_idx = 0
    total_length = m + r
    
    # 1. Build the fita inserting placeholders (False) at powers of 2
    for i in range(1, total_length + 1):
        # A quick bitwise check to see if 'i' is a power of 2: (i & (i - 1)) == 0
        if (i & (i - 1)) == 0:
            hamming_code.append(False)  # Parity bit placeholder
        else:
            hamming_code.append(frame[data_idx])
            data_idx += 1
            
    # 2. Calculate the correct parity value for each power of 2
    for i in range(r):
        pos = 2 ** i  # The 1-based bit position of the current parity bit
        parity_accumulator = 0
        
        for j in range(1, total_length + 1):
            # If the bit position 'pos' is covered by the index 'j'
            if j & pos:
                parity_accumulator ^= int(hamming_code[j - 1])
                
        hamming_code[pos - 1] = bool(parity_accumulator)
        
    return hamming_code


def verify_and_correct_hamming(frame: list[bool]) -> tuple[list[bool], bool]:
    """
    Receiver side: Analyzes the Hamming codeword, calculates the syndrome,
    automatically corrects any single-bit error found, and strips the parity bits.
    
    Returns a tuple with the clean data list and an error_detected flag.
    """
    n = len(frame)
    if n == 0:
        return [], True
        
    r = 0
    # Estimate the number of parity bits embedded from the total length
    while (2 ** r) < n:
        r += 1
        
    error_position = 0
    
    # 1. Check all parities to locate the corrupted bit position (Syndrome)
    for i in range(r):
        pos = 2 ** i
        parity_check_val = 0
        for j in range(1, n + 1):
            if j & pos:
                parity_check_val ^= int(frame[j - 1])
        if parity_check_val != 0:
            error_position += pos
            
    error_detected = error_position != 0
    
    # 2. If a single-bit error is located within valid boundaries, fix it in-place!
    if error_detected and error_position <= n:
        frame[error_position - 1] = not frame[error_position - 1]
        
    # 3. Strip away the parity bits (powers of 2) to recover clean user data
    clean_data = []
    for i in range(1, n + 1):
        if (i & (i - 1)) != 0:  # If it's NOT a power of 2, it's literal user data
            clean_data.append(frame[i - 1])
            
    return clean_data, error_detected
