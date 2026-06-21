import numpy as np

def inject_gaussian_noise(signal: list[float] | list[int], error_percentage: float = 0.0) -> list[float]:
    """
    Simulates the physical channel using the exact specification from the diagram.
    Takes a percentage (0 to 100) from the UI slider and maps it to Gaussian Noise.
    
    :param signal: Clean input wave sample list
    :param error_percentage: Noise intensity from 0% (none) to 100% (maximum)
    """
    if not signal:
        return []
        
    signal_arr = np.array(signal, dtype=float)
    
    # Map percentage (0-100) to a Standard Deviation scale (0.0 to 1.5)
    # 0% error -> scale = 0.0 (no noise)
    # 100% error -> scale = 1.5 (very high noise, causing severe bit flips)
    standard_deviation = (error_percentage / 100.0) * 1.5
    
    if standard_deviation == 0.0:
        return signal_arr.tolist()
        
    # Generate Gaussian noise matching the signal layout
    noise = np.random.normal(loc=0.0, scale=standard_deviation, size=len(signal_arr))
    
    # Additive noise fusion
    corrupted_signal = signal_arr + noise
    
    return corrupted_signal.tolist()
