from torch.utils.data import Dataset, DataLoader
import torch
import pandas as pd

# L7: [50,0,0...,50,0,0...]
class SineWaveDataset7(Dataset):
    def __init__(self, csv_file):
        self.data = pd.read_csv(csv_file)
        self.num_timesteps = 300

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        amplitude = self.data.iloc[idx, 0]
        period = self.data.iloc[idx, 1]
        sine_wave = eval(self.data.iloc[idx, 2])  # assuming the sine_wave is stored as a string representation of a list
        
        
        # L1: Explicit Time Resetting with period 
        amplitude_vector = torch.tensor([amplitude] * self.num_timesteps, dtype=torch.float32)
        period_vector = torch.tensor([period] * self.num_timesteps, dtype=torch.float32)
        time_vector = torch.tensor([50 if i % period == 0 else 0 for i in range(self.num_timesteps)] , dtype=torch.float32)
        sine_wave_vector = torch.tensor(sine_wave, dtype=torch.float32)
        
        input_vector = torch.stack([amplitude_vector,period_vector,time_vector],dim=1)  # Shape: [num_timesteps, 2]
        target_vector = torch.stack([sine_wave_vector],dim=1)
        return input_vector, sine_wave_vector