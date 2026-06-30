def add_even_parity(frame: list[bool]) -> list[bool]:
    """Adiciona um bit de paridade par ao final do quadro para permitir verificação simples de erro."""
    # sum() trata True como 1 e False como 0.
    total_ones = sum(frame)
    
    # Se o total de bits 1 for ímpar, adiciona True; se for par, adiciona False.
    parity_bit = bool(total_ones % 2)
    
    return frame + [parity_bit]


def verify_and_remove_even_parity(frame: list[bool]) -> tuple[list[bool], bool]:
    """Verifica a paridade par, remove o bit de paridade e informa se houve erro."""
    if len(frame) == 0:
        return [], True
        
    # 1. Conta todos os bits 1, incluindo o bit de paridade recebido.
    total_ones = sum(frame)
    
    # Se a soma resultar em ímpar, a paridade foi violada e há erro.
    error_detected = bool(total_ones % 2)
    
    # 2. Remove o último bit, que é o bit de paridade.
    clean_frame = frame[:-1]
    
    return clean_frame, error_detected


def add_checksum(frame: list[bool]) -> list[bool]:
    """Calcula e anexa um checksum de 8 bits usando complemento de um."""
    # 1. Garante que o quadro fique alinhado em blocos de 8 bits.
    padding_needed = (8 - (len(frame) % 8)) % 8
    padded_frame = frame + ([False] * padding_needed)
    
    checksum_accumulator = 0
    
    # 2. Soma cada segmento de 8 bits como se fosse um inteiro.
    for i in range(0, len(padded_frame), 8):
        segment = padded_frame[i:i+8]
        # Converte manualmente os bits do segmento em um número inteiro.
        segment_value = 0
        for bit in segment:
            segment_value = (segment_value << 1) | int(bit)
        checksum_accumulator += segment_value
        
    # 3. Trata o excesso de carry somando a parte que ultrapassa 8 bits de volta ao valor baixo.
    while checksum_accumulator > 0xFF:
        carry = checksum_accumulator >> 8
        checksum_accumulator = (checksum_accumulator & 0xFF) + carry
        
    # 4. Aplica o complemento de um invertendo todos os bits do valor acumulado.
    checksum_final_value = 0xFF - checksum_accumulator
    
    # 5. Converte o valor final de volta para uma lista booleana de 8 bits.
    checksum_bits = [bool((checksum_final_value >> i) & 1) for i in range(7, -1, -1)]
    
    return padded_frame + checksum_bits


def verify_and_remove_checksum(frame: list[bool]) -> tuple[list[bool], bool]:
    """Verifica o checksum recebido e remove os 8 bits finais do quadro."""
    # Um quadro válido precisa ter ao menos um segmento de dados e um de checksum.
    if len(frame) < 16 or len(frame) % 8 != 0:
        return [], True
        
    checksum_accumulator = 0
    
    # 1. Soma todos os segmentos, inclusive o byte do checksum.
    for i in range(0, len(frame), 8):
        segment = frame[i:i+8]
        segment_value = 0
        for bit in segment:
            segment_value = (segment_value << 1) | int(bit)
        checksum_accumulator += segment_value
        
    # 2. Faz o ajuste de carry caso a soma ultrapasse 8 bits.
    while checksum_accumulator > 0xFF:
        carry = checksum_accumulator >> 8
        checksum_accumulator = (checksum_accumulator & 0xFF) + carry
        
    # 3. Se o complemento de um estiver correto, o acumulador precisa resultar em 0xFF.
    error_detected = (0xFF - checksum_accumulator) != 0
    
    # 4. Remove os últimos 8 bits, que correspondem ao checksum.
    clean_frame = frame[:-8]
    
    return clean_frame, error_detected


def add_crc32(frame: list[bool]) -> list[bool]:
    """Calcula e anexa um CRC-32 IEEE 802.3 ao quadro de bits."""
    # Polinômio gerador da IEEE 802.3 representado com 33 bits, incluindo o bit mais significativo 1.
    POLYNOMIAL_33BITS = [
        True, False, False, False, False, True, False, False,
        True, True, False, False, False, False, False, True,
        False, False, False, True, True, True, False, True,
        True, False, True, True, False, True, True, True, True
    ]

    # 1. Acrescenta 32 zeros como espaço reservado para o resto do CRC.
    dividend = frame + ([False] * 32)
    
    # 2. Copia os primeiros 33 bits para iniciar o registrador do resto da divisão.
    remainder = dividend[:33]
    
    # 3. Executa a divisão polinomial bit a bit usando XOR.
    for i in range(33, len(dividend)):
        # Se o bit mais significativo do resto for 1, aplica XOR com o polinômio gerador.
        if remainder[0]:
            remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        
        # Desloca o registrador para a esquerda e injeta o próximo bit do dividendo.
        remainder = remainder[1:] + [dividend[i]]
        
    # 4. Faz a última correção matemática no bloco restante.
    if remainder[0]:
        remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        
    # Remove o bit excedente para ficar apenas com os 32 bits finais do CRC.
    crc_32_bits = remainder[1:]
    
    # Retorna o quadro original com a assinatura CRC anexada no final.
    return frame + crc_32_bits


def verify_and_remove_crc32(frame: list[bool]) -> tuple[list[bool], bool]:
    """Verifica o CRC-32 recebido e remove os 32 bits finais do quadro."""
    # Um quadro válido precisa conter ao menos os 32 bits do CRC.
    if len(frame) <= 32:
        return [], True
        
    POLYNOMIAL_33BITS = [
        True, False, False, False, False, True, False, False,
        True, True, False, False, False, False, False, True,
        False, False, False, True, True, True, False, True,
        True, False, True, True, False, True, True, True, True
    ]
    
    # 1. O dividendo é o quadro completo que chegou.
    remainder = frame[:33]
    
    # 2. Repete a mesma divisão polinomial usada no transmissor.
    for i in range(33, len(frame)):
        if remainder[0]:
            remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        remainder = remainder[1:] + [frame[i]]
        
    if remainder[0]:
        remainder = [r_bit ^ p_bit for r_bit, p_bit in zip(remainder, POLYNOMIAL_33BITS)]
        
    # 3. Se qualquer bit do resto for 1, o quadro foi corrompido.
    error_detected = any(remainder[1:])
    
    # 4. Remove os 32 bits do CRC para recuperar os dados originais.
    clean_frame = frame[:-32]
    
    return clean_frame, error_detected


def add_hamming(frame: list[bool]) -> list[bool]:
    """Insere bits de paridade do código de Hamming em posições potências de dois."""
    m = len(frame)  # Quantidade de bits de dados.
    r = 0           # Quantidade de bits de paridade necessários.
    
    # Calcula quantos bits de paridade são necessários pela condição de Hamming.
    while (2 ** r) < (m + r + 1):
        r += 1
        
    hamming_code = []
    data_idx = 0
    total_length = m + r
    
    # 1. Monta a palavra de código inserindo placeholders nas posições 1, 2, 4, 8...
    for i in range(1, total_length + 1):
        # Teste clássico de potência de 2: se (i & (i - 1)) == 0, então i é potência de 2.
        if (i & (i - 1)) == 0:
            hamming_code.append(False)  # Espaço reservado para o bit de paridade.
        else:
            hamming_code.append(frame[data_idx])
            data_idx += 1
            
    # 2. Calcula o valor correto de cada bit de paridade.
    for i in range(r):
        pos = 2 ** i  # Posição 1-based do bit de paridade atual.
        parity_accumulator = 0
        
        for j in range(1, total_length + 1):
            # Se a posição atual participa da cobertura deste bit de paridade, entra na conta.
            if j & pos:
                parity_accumulator ^= int(hamming_code[j - 1])
                
        hamming_code[pos - 1] = bool(parity_accumulator)
        
    return hamming_code


def verify_and_correct_hamming(frame: list[bool]) -> tuple[list[bool], bool]:
    """Calcula o síndrome de Hamming, corrige um erro simples e remove os bits de paridade."""
    n = len(frame)
    if n == 0:
        return [], True
        
    r = 0
    # Estima quantos bits de paridade existem com base no tamanho total do quadro.
    while (2 ** r) < n:
        r += 1
        
    error_position = 0
    
    # 1. Verifica todas as paridades para descobrir a posição do bit corrompido.
    for i in range(r):
        pos = 2 ** i
        parity_check_val = 0
        for j in range(1, n + 1):
            if j & pos:
                parity_check_val ^= int(frame[j - 1])
        if parity_check_val != 0:
            error_position += pos
            
    error_detected = error_position != 0
    
    # 2. Se o erro estiver dentro dos limites válidos, corrige o bit diretamente no quadro.
    if error_detected and error_position <= n:
        frame[error_position - 1] = not frame[error_position - 1]
        
    # 3. Remove os bits de paridade, que ocupam posições potências de dois.
    clean_data = []
    for i in range(1, n + 1):
        if (i & (i - 1)) != 0:  # Se não for potência de 2, então é dado útil.
            clean_data.append(frame[i - 1])
            
    return clean_data, error_detected
