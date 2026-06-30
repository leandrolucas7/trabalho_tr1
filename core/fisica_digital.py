def encode_nrz_polar(bitstream: list[bool]) -> list[int]:
    """Codifica um bitstream lógico em NRZ-Polar, usando +1 para 1 e -1 para 0."""
    # Usa uma list comprehension para transformar cada bit no nível de tensão correspondente.
    return [1 if bit else -1 for bit in bitstream]


def decode_nrz_polar(digital_signal: list[int]) -> list[bool]:
    """Decodifica um sinal NRZ-Polar e reconstrói o bitstream lógico original."""
    # Qualquer nível de tensão acima de zero é interpretado como 1.
    return [bit > 0 for bit in digital_signal]


def encode_manchester(bitstream: list[bool]) -> list[int]:
    """Codifica o bitstream usando Manchester, com transição no meio de cada período."""
    digital_signal = []
    
    for bit in bitstream:
        if bit:
            # Bit 1: transição de nível baixo para nível alto.
            digital_signal.extend([-1, 1])
        else:
            # Bit 0: transição de nível alto para nível baixo.
            digital_signal.extend([1, -1])
            
    return digital_signal


def decode_manchester(digital_signal: list[int]) -> list[bool]:
    """Decodifica um sinal Manchester observando a direção da transição em cada par de amostras."""
    bitstream = []
    
    # Percorre o sinal dois elementos por vez, porque cada bit ocupa meio período em cada amostra.
    for i in range(0, len(digital_signal), 2):
        if i + 1 < len(digital_signal):
            first_half = digital_signal[i]
            second_half = digital_signal[i + 1]
            
            # Se a transição sobe, o bit é 1; se desce, o bit é 0.
            bitstream.append(second_half > first_half)
            
    return bitstream


def encode_bipolar(bitstream: list[bool]) -> list[int]:
    """Codifica o bitstream em Bipolar/AMI, alternando a polaridade dos bits 1."""
    digital_signal = []
    # Começa com polaridade positiva para o primeiro bit 1 encontrado.
    next_polarity = 1
    
    for bit in bitstream:
        if bit:
            # Adiciona a polaridade atual e inverte para o próximo 1.
            digital_signal.append(next_polarity)
            next_polarity = -next_polarity
        else:
            # Bits 0 sempre são representados por nível zero.
            digital_signal.append(0)
            
    return digital_signal


def decode_bipolar(digital_signal: list[int]) -> list[bool]:
    """Decodifica um sinal Bipolar/AMI convertendo qualquer nível não nulo em bit 1."""
    # Se o valor absoluto for diferente de zero, o bit é interpretado como 1.
    return [abs(level) != 0 for level in digital_signal]
