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
SCALE = 10000.0   # divide score by this to get roughly [-1,1]


# -----------------------
# Dataset: preloads all data to GPU
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

        NUM_BITS = INPUT_LEN
        inputs = []
        scores = []

        for input_blob, score in rows:
            packed = torch.tensor(list(input_blob), dtype=torch.uint8)
            t = packed.view(-1, 1)
            bits = ((t & (1 << torch.arange(8))) > 0).to(torch.float32)
            bits = torch.flip(bits, dims=[1]).flatten()[:NUM_BITS]

            # --- normalize each 116-bit segment ---
            # segment 0: picker deck
            s0 = bits[:116]
            if s0.sum() > 0:
                s0 = s0 / s0.sum()
            # segment 1: opponent deck
            s1 = bits[116:232]
            if s1.sum() > 0:
                s1 = s1 / s1.sum()
            # segment 2: pool
            s2 = bits[232:348]
            if s2.sum() > 0:
                s2 = s2 / s2.sum()
            # draft step one-hot (348:357)
            s3 = bits[348:357]

            normalized_bits = torch.cat([s0, s1, s2, s3], dim=0)
            inputs.append(normalized_bits)
            scores.append(float(score)/SCALE)

        # stack and move to device
        self.inputs = torch.stack(inputs).to(device)
        self.scores = torch.tensor(scores, dtype=torch.float32, device=device)

    def __len__(self):
        return self.inputs.size(0)

    def __getitem__(self, idx):
        return self.inputs[idx], self.scores[idx]
# -----------------------
# Model (value network)
# -----------------------
class ValueNet(nn.Module):
    def __init__(self, input_size=INPUT_LEN, dropout=DROPOUT):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 1024),
            nn.ReLU(),
            nn.LayerNorm(1024),
            nn.Dropout(dropout),

            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.LayerNorm(512),
            nn.Dropout(dropout),

            nn.Linear(512, 256),
            nn.ReLU(),
            nn.LayerNorm(256),
            nn.Dropout(dropout),

            nn.Linear(256, 64),
            nn.ReLU(),
            nn.LayerNorm(64),
            nn.Dropout(dropout),

            nn.Linear(64, 1)
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


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

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model = ValueNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-6)
    criterion = nn.MSELoss()
    scaler = torch.amp.GradScaler(enabled=True)

    best_val = float("inf")
    for epoch in range(1, EPOCHS+1):
        model.train()
        train_loss = 0.0
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            with torch.amp.autocast(device_type='cuda'):
                preds = model(inputs)
                loss = criterion(preds, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item() * inputs.size(0)
        train_loss /= len(train_loader.dataset)

        # validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for inputs, targets in val_loader:
                with torch.amp.autocast(device_type='cuda'):
                    preds = model(inputs)
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
