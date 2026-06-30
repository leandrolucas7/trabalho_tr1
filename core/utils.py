def string_to_bitstream(message: str) -> list[bool]:
    """Converte uma string ASCII em uma lista de bits booleanos, mantendo a ordem dos bits de cada caractere."""
    try:
        # Converte a string para bytes ASCII; cada caractere vira um valor numérico entre 0 e 127.
        raw_bytes = message.encode('ascii')
    except UnicodeEncodeError:
        return None

    # Para cada byte, percorre os 8 bits do mais significativo para o menos significativo.
    return [bool((byte >> i) & 1) for byte in raw_bytes for i in range(7, -1, -1)]



def bitstream_to_string(bitstream: list[bool]) -> str:
    """Converte uma lista de bits booleanos de volta para uma string ASCII."""
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
        # Converte a lista de inteiros em bytes e depois decodifica para ASCII.
        return bytes(byte_list).decode('ascii')
    except UnicodeDecodeError:
        return None
