import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import sqlite3

# -----------------------
# Config
# -----------------------
DB_NAME = "testdb.db"
INPUT_LEN = 357
BATCH_SIZE = 256
NUM_WORKERS = 0
EPOCHS = 300
LR = 1e-3
DROPOUT = 0.25
VAL_SPLIT = 0.1
SCALE = 10000.0  # rough scale for score

# -----------------------
# Dataset
# -----------------------
class StateValueDataset(Dataset):
    def __init__(self, db_name, device='cuda'):
        con = sqlite3.connect(db_name)
        cur = con.cursor()
        cur.execute("SELECT input, score FROM training")
        rows = cur.fetchall()
        con.close()

        if len(rows) == 0:
            raise RuntimeError("No training rows found in DB training table.")

        inputs, scores = [], []

        # First, load raw scores to compute mean for centering
        raw_scores = [float(score)/SCALE for _, score in rows]
        mean_score = sum(raw_scores)/len(raw_scores)
        std_score = (sum((s-mean_score)**2 for s in raw_scores)/len(raw_scores))**0.5

        for input_blob, score in rows:
            packed = torch.tensor(list(input_blob), dtype=torch.uint8)
            t = packed.view(-1, 1)
            bits = ((t & (1 << torch.arange(8))) > 0).to(torch.float32)
            bits = torch.flip(bits, dims=[1]).flatten()[:INPUT_LEN]

            # Normalize each 116-bit segment separately
            s0 = bits[:116]
            if s0.sum() > 0:
                s0 = s0 / s0.sum()
            s1 = bits[116:232]
            if s1.sum() > 0:
                s1 = s1 / s1.sum()
            s2 = bits[232:348]
            if s2.sum() > 0:
                s2 = s2 / s2.sum()
            s3 = bits[348:357]

            normalized_bits = torch.cat([s0, s1, s2, s3], dim=0)
            inputs.append(normalized_bits)

            # Center and scale score to roughly [-1, 1]
            score_norm = (float(score)/SCALE - mean_score) / (std_score + 1e-6)
            scores.append(score_norm)

        self.inputs = torch.stack(inputs).to(device)
        self.scores = torch.tensor(scores, dtype=torch.float32, device=device)

    def __len__(self):
        return self.inputs.size(0)

    def __getitem__(self, idx):
        return self.inputs[idx], self.scores[idx]

# -----------------------
# Structured ValueNet
# -----------------------
class VectorEncoder(nn.Module):
    """Encodes one 116-bit vector into a latent feature."""
    def __init__(self, in_dim=116, hidden_dim=128, out_dim=64, dropout=0.25):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim//2),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            #  nn.Linear(hidden_dim//4, hidden_dim//8),
            # nn.LeakyReLU(0.1),
            # nn.Dropout(dropout),
            nn.Linear(hidden_dim//2, out_dim),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.layers(x)

class StructuredValueNet(nn.Module):
    def __init__(self, vec_dim=116, meta_dim=9, dropout=0.25):
        super().__init__()
        self.cards_encoder = VectorEncoder(3*vec_dim, 2048, 512, dropout)
        # self.pool_encoder = VectorEncoder(vec_dim, 256, 64, dropout)
        # self.opp_encoder = VectorEncoder(vec_dim, 256, 64, dropout)

        fusion_in = 512 + meta_dim
        self.fusion = nn.Sequential(
            nn.Linear(fusion_in, 256),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, cards_vec,  meta_vec):
        d = self.cards_encoder(cards_vec)
        fused = torch.cat([d, meta_vec], dim=-1)
        return self.fusion(fused).squeeze(-1)

# -----------------------
# Training loop
# -----------------------
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    dataset = StateValueDataset(DB_NAME, device=device)
    n_val = int(len(dataset) * VAL_SPLIT)
    n_train = len(dataset) - n_val
    train_set, val_set = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

    model = StructuredValueNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-6)
    criterion = nn.MSELoss()
    scaler = torch.amp.GradScaler(enabled=True)

    best_val = float("inf")
    for epoch in range(1, EPOCHS+1):
        model.train()
        train_loss = 0.0
        for inputs, targets in train_loader:
            optimizer.zero_grad()

            # Split input into structured vectors
            cards_vec = inputs[:, :348]
            # opp_vec = inputs[:, 116:232]
            # pool_vec = inputs[:, 232:348]
            meta_vec = inputs[:, 348:357]

            with torch.amp.autocast(device_type='cuda'):
                preds = model(cards_vec, meta_vec)
                loss = criterion(preds, targets)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item() * inputs.size(0)
        train_loss /= len(train_loader.dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for inputs, targets in val_loader:
                cards_vec = inputs[:, :348]
                # opp_vec = inputs[:, 116:232]
                # pool_vec = inputs[:, 232:348]
                meta_vec = inputs[:, 348:357]

                with torch.amp.autocast(device_type='cuda'):
                    preds = model(cards_vec, meta_vec)
                    val_loss += criterion(preds, targets).item() * inputs.size(0)
        val_loss /= len(val_loader.dataset)

        print(f"Epoch {epoch}/{EPOCHS} — Train MSE: {train_loss:.6f}  Val MSE: {val_loss:.6f}")

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), "value_net_best.pth")
            print(" Saved best -> value_net_best.pth")

    torch.save(model.state_dict(), "value_net_final.pth")
    print("Training done. final saved to value_net_final.pth")


if __name__ == "__main__":
    train()
