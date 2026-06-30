from math import ceil

def split_bitstream_into_payloads(bitstream: list[bool], payload_size: int) -> list[list[bool]]:
    """Divide um bitstream contínuo em vários payloads de tamanho fixo para facilitar o enquadramento."""
    payloads = []
    # Calcula quantos blocos serão necessários, arredondando para cima quando houver sobra.
    num_payloads = ceil(len(bitstream) / payload_size)
    
    for i in range(num_payloads):
        # Define os índices inicial e final do pedaço atual.
        start = i * payload_size
        end = start + payload_size
        
        # Separa o trecho correspondente e adiciona o payload à lista.
        payloads.append(bitstream[start:end])
        
    return payloads


def add_character_count_framing(payloads: list[list[bool]]) -> list[list[bool]]:
    """Adiciona enquadramento por contagem de caracteres usando um cabeçalho de 8 bits."""
    framed_payloads = []
    
    for payload in payloads:
        # 1. Alinha o payload para múltiplos de 8 bits, completando com zeros se necessário.
        padding_needed = (8 - (len(payload) % 8)) % 8
        padded_payload = payload + ([False] * padding_needed)
        
        # 2. Calcula quantos bytes o quadro final terá, incluindo o próprio cabeçalho.
        total_bytes = (len(padded_payload) // 8) + 1
        
        # 3. Converte o tamanho total para representação binária com 8 bits.
        binary_str = f'{total_bytes:08b}'
        header = [character == '1' for character in binary_str]
        
        # 4. Monta o quadro final juntando cabeçalho e dados.
        framed_payloads.append(header + padded_payload)
        
    return framed_payloads


def remove_character_count_framing(framed_payloads: list[list[bool]]) -> list[list[bool]]:
    """Remove o cabeçalho de contagem de caracteres e recupera o payload original."""
    raw_payloads = []
    
    for frame in framed_payloads:
        # Um quadro válido precisa conter pelo menos o cabeçalho de 8 bits.
        if len(frame) < 8:
            continue
            
        # 1. Lê os 8 primeiros bits, que representam o tamanho do quadro.
        header_bits = frame[:8]
        
        # 2. Converte os bits booleanos do cabeçalho em uma string binária.
        binary_str = "".join(['1' if bit else '0' for bit in header_bits])
        
        # 3. Transforma a string binária em inteiro decimal para descobrir o tamanho esperado.
        total_bytes_expected = int(binary_str, 2)
        
        # 4. Remove o cabeçalho e recupera apenas os bits úteis do payload.
        payload_data = frame[8 : total_bytes_expected * 8]
        raw_payloads.append(payload_data)
        
    return raw_payloads


def add_byte_stuffing_framing(payloads: list[list[bool]]) -> list[list[bool]]:
    """Aplica enquadramento por inserção de bytes, protegendo flags e bytes de escape."""
    # Define os padrões de 8 bits para o flag de início/fim e para o escape.
    FLAG_PATTERN = [False, True, True, True, True, True, True, False]   # 0x7E
    ESC_PATTERN  = [False, True, True, True, True, True, False, True]   # 0x7D
    
    framed_payloads = []
    
    for payload in payloads:
        # 1. Garante alinhamento em bytes para facilitar a comparação de padrões.
        padding_needed = (8 - (len(payload) % 8)) % 8
        padded_payload = payload + ([False] * padding_needed)
        
        stuffed_payload = []
        
        # 2. Processa o payload byte a byte para detectar padrões especiais.
        for i in range(0, len(padded_payload), 8):
            current_byte = padded_payload[i:i+8]
            
            # Se o byte atual for igual ao flag ou ao escape, insere um escape antes dele.
            if current_byte == FLAG_PATTERN or current_byte == ESC_PATTERN:
                stuffed_payload.extend(ESC_PATTERN)
                
            stuffed_payload.extend(current_byte)
            
        # 3. Envolve os dados com flag no início e no fim.
        final_frame = FLAG_PATTERN + stuffed_payload + FLAG_PATTERN
        framed_payloads.append(final_frame)
        
    return framed_payloads


def remove_byte_stuffing_framing(framed_payloads: list[list[bool]]) -> list[list[bool]]:
    """Remove os flags externos e desfaz a inserção de bytes feita no transmissor."""
    FLAG_PATTERN = [False, True, True, True, True, True, True, False]   # 0x7E
    ESC_PATTERN  = [False, True, True, True, True, True, False, True]   # 0x7D
    
    raw_payloads = []
    
    for frame in framed_payloads:
        # Um quadro válido precisa ter pelo menos um flag de abertura e um de fechamento.
        if len(frame) < 16:
            continue
            
        # Remove os flags externos e analisa apenas a parte interna do quadro.
        inner_data = frame[8:-8]
        clean_payload = []
        
        skip_next_byte = False
        i = 0
        
        while i + 8 <= len(inner_data):
            current_byte = inner_data[i:i+8]
            
            if skip_next_byte:
                # Este byte foi escapado antes, então ele entra no payload sem interpretação extra.
                clean_payload.extend(current_byte)
                skip_next_byte = False
                i += 8
            elif current_byte == ESC_PATTERN:
                # Encontramos um escape inserido: ele não é dado útil, só sinaliza o próximo byte.
                skip_next_byte = True
                i += 8
            else:
                # Byte comum: adiciona diretamente ao payload limpo.
                clean_payload.extend(current_byte)
                i += 8
                
        raw_payloads.append(clean_payload)
        
    return raw_payloads


def add_bit_stuffing_framing(payloads: list[list[bool]]) -> list[list[bool]]:
    """Aplica enquadramento por inserção de bits, evitando a formação acidental do padrão de flag."""
    FLAG_PATTERN = [False, True, True, True, True, True, True, False]  # 01111110
    framed_payloads = []
    
    for payload in payloads:
        stuffed_payload = []
        consecutive_ones = 0
        
        for bit in payload:
            stuffed_payload.append(bit)
            
            if bit:
                consecutive_ones += 1
                # Depois de cinco bits 1 seguidos, insere um 0 para impedir a criação do flag.
                if consecutive_ones == 5:
                    stuffed_payload.append(False)
                    consecutive_ones = 0
            else:
                consecutive_ones = 0
                
        # Coloca o flag no começo e no final do quadro.
        final_frame = FLAG_PATTERN + stuffed_payload + FLAG_PATTERN
        framed_payloads.append(final_frame)
        
    return framed_payloads


def remove_bit_stuffing_framing(framed_payloads: list[list[bool]]) -> list[list[bool]]:
    """Remove os flags de borda e desfaz a inserção de bits feita no transmissor."""
    raw_payloads = []
    
    for frame in framed_payloads:
        # Um quadro válido precisa ter pelo menos os dois flags de borda.
        if len(frame) < 16:
            continue
            
        # Remove os 8 bits do início e os 8 bits do fim.
        inner_bits = frame[8:-8]
        clean_payload = []
        
        consecutive_ones = 0
        i = 0
        
        while i < len(inner_bits):
            bit = inner_bits[i]
            
            if consecutive_ones == 5:
                # Ao encontrar cinco 1 seguidos, o próximo 0 é descartado por regra do bit stuffing.
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
