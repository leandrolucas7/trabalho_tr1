import numpy as np

def inject_gaussian_noise(signal: list[float] | list[int], media: float = 0.0, desvio: float = 1.0) -> list[float]:
    """
    Simula o canal físico aplicando Ruído Branco Gaussiano Aditivo (AWGN).
    
    :param signal: O sinal original (onda ou pulsos)
    :param media: A média (μ) do deslocamento do ruído (geralmente 0.0)
    :param desvio: O desvio padrão (σ) ou variância da interferência
    """
    if not signal:
        return []
        
    signal_arr = np.array(signal, dtype=float)
    
    # Se o desvio e a média forem zero, o canal é ideal (sem ruído)
    if desvio == 0.0 and media == 0.0:
        return signal_arr.tolist()
        
    # Gera a distribuição Gaussiana exata
    noise = np.random.normal(loc=media, scale=desvio, size=len(signal_arr))
    
    # Adiciona o ruído ao sinal físico
    corrupted_signal = signal_arr + noise
    
    return corrupted_signal.tolist()