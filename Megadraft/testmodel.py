# trainer_state_value.py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import sqlite3

DB_NAME = "testdb.db"
INPUT_LEN = 357
BATCH_SIZE = 256
NUM_WORKERS = 0
EPOCHS = 60
LR = 1e-3
DROPOUT = 0.25
VAL_SPLIT = 0.1
SCALE = 10000.0   # divide score by this to get roughly [-1,1]

# -----------------------
# Dataset: loads input blob and scalar score
# -----------------------
class StateValueDataset(Dataset):
    def __init__(self, db_name):
        con = sqlite3.connect(db_name)
        cur = con.cursor()
        # select input and score (ignore next_card if present)
        cur.execute("SELECT input, score FROM training")
        rows = cur.fetchall()
        con.close()

        self.inputs = []
        self.scores = []
        for input_blob, score in rows:
            # convert blob -> bit vector (uint8 -> bits)
            packed = torch.tensor(list(input_blob), dtype=torch.uint8)
            t = packed.view(-1, 1)
            bits = ((t & (1 << torch.arange(8))) > 0).to(torch.float32)
            bits = torch.flip(bits, dims=[1]).flatten()[:INPUT_LEN]
            # bits is float tensor 0/1 length INPUT_LEN
            self.inputs.append(bits)
            self.scores.append(float(score) / SCALE)

        if len(self.inputs) == 0:
            raise RuntimeError("No training rows found in DB training table.")

        # stack into tensors for fast dataloader
        self.inputs = torch.stack(self.inputs)
        self.scores = torch.tensor(self.scores, dtype=torch.float32)

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

            nn.Linear(64, 1)   # scalar output
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)  # shape: [B]


# -----------------------
# Training loop
# -----------------------
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    dataset = StateValueDataset(DB_NAME)
    n_val = int(len(dataset) * VAL_SPLIT)
    n_train = len(dataset) - n_val
    train_set, val_set = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=NUM_WORKERS, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=NUM_WORKERS, pin_memory=True)

    model = ValueNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-6)
    criterion = nn.MSELoss()
    scaler = torch.amp.GradScaler()

    best_val = float("inf")
    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for inputs, targets in train_loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            optimizer.zero_grad()
            with torch.amp.autocast(device_type='cuda'):
                preds = model(inputs)  # [B]
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
                inputs = inputs.to(device, non_blocking=True)
                targets = targets.to(device, non_blocking=True)
                preds = model(inputs)
                val_loss += criterion(preds, targets).item() * inputs.size(0)
        val_loss /= len(val_loader.dataset)

        print(f"Epoch {epoch}/{EPOCHS} — Train MSE: {train_loss:.6f}  Val MSE: {val_loss:.6f}")

        # save best
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), "value_net_best.pth")
            print(" Saved best -> value_net_best.pth")

    # final save
    torch.save(model.state_dict(), "value_net_final.pth")
    print("Training done. final saved to value_net_final.pth")


if __name__ == "__main__":
    train()
