def string_to_bitstream(message: str) -> list[bool]:
    try:
        # Imagine it like: "Hi" -> [72, 105] -> 01001000 , 01101001
        raw_bytes = message.encode('ascii')
    except UnicodeEncodeError:
        return None

    # Convert every bit of every byte (char) into a bool (byte)
        # 01001000 >> 7 = 00000001 --> 1 & 1 = 1 -> True = 1 (Continue to logic with >>6, >>5)
    return [bool((byte >> i) & 1) for byte in raw_bytes for i in range(7, -1, -1)]



def bitstream_to_string(bitstream: list[bool]) -> str:
    if len(bitstream) % 8 != 0:
        return None

    byte_list = []
    for i in range(0, len(bitstream), 8):
        chunk = bitstream[i:i+8]
        
        byte_value = 0
        for bit in chunk:
            byte_value = (byte_value << 1) | int(bit)
        byte_list.append(byte_value)
        
    try:
        # Convert our list of integers directly to a native bytes object and decode it
        return bytes(byte_list).decode('ascii')
    except UnicodeDecodeError:
        return None
