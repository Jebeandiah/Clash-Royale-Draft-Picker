import torch
import torch.nn as nn
import torch.nn.functional as F

# --- Model Parameters ---
NUM_CARDS = 116      # total cards in the game
NUM_FEATURES = NUM_CARDS * 2 + 2  
# my deck (120), opponent deck (120), + 2 numeric features (e.g. avg elixir for each side)


# --- Define Model ---
class ClashDraftPredictor(nn.Module):
    def __init__(self):
        super().__init__()
        
        # Layer 1: from large input vector → compressed representation
        self.fc1 = nn.Linear(NUM_FEATURES, 256)
        
        # Layer 2: deeper representation
        self.fc2 = nn.Linear(256, 128)
        
        # Output layer: predict win probability
        self.fc3 = nn.Linear(128, 1)
        
        # Optional dropout to reduce overfitting
        self.dropout = nn.Dropout(0.3)
    
    def forward(self, x):
        """
        x: tensor of shape (batch_size, NUM_FEATURES)
        """
        x = F.relu(self.fc1(x))      # nonlinear feature extraction
        x = self.dropout(x)
        x = F.relu(self.fc2(x))      # deeper interaction modeling
        x = self.fc3(x)              # final linear projection to 1 value
        return torch.sigmoid(x)      # convert to probability (0–1)


def main():
    # --- Example Usage ---

    # Suppose we have 1 sample (batch_size=1)
    # my_deck and opp_deck are binary vectors of length 120 each
    my_deck = torch.zeros(NUM_CARDS)
    opp_deck = torch.zeros(NUM_CARDS)

    # Example: I have cards 0, 5, 12, 48
    my_deck[[0, 5, 12, 48]] = 1

    # Opponent has cards 3, 7, 22, 59
    opp_deck[[3, 7, 22, 59]] = 1

    # Elixir averages (could be normalized to 0–1)
    avg_elixir_me = torch.tensor([3.8])
    avg_elixir_opp = torch.tensor([4.1])

    # Combine all inputs into one vector
    x = torch.cat([my_deck, opp_deck, avg_elixir_me, avg_elixir_opp]).unsqueeze(0)  # shape (1, 234)

    # Initialize model and predict
    model = ClashDraftPredictor()
    pred = model(x)

    print(f"Predicted win probability: {pred.item():.3f}")

if __name__ == "__main__":
    main()