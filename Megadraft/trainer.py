import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import sqlite3
import dBManager
import cardhelpers as ch
# -----------------------
# Config
# -----------------------
DB_NAME = "testdb.db"
INPUT_LEN = len(ch.card_list)*2
BATCH_SIZE = 256
NUM_WORKERS = 0
EPOCHS = 300
LR = 1e-5
DROPOUT = 0.25
VAL_SPLIT = 0.1
SCALE = 10000.0  # rough scale for score
class read_training_dataset(Dataset):
    
    def __init__(self, db_name = dBManager.dbname, device='cuda'):
        con = sqlite3.connect(f'{db_name}.db')
        cur = con.cursor()
        cur.execute("SELECT input, score FROM training")
        rows = cur.fetchall()
        con.close()

        if len(rows) == 0:
            raise RuntimeError("No training rows found in DB training table.")

        inputs, scores = [], []

        for input_blob,  score in rows:
            packed = torch.tensor(list(input_blob), dtype=torch.uint8)
            t = packed.view(-1, 1)
            bits = ((t & (1 << torch.arange(8))) > 0).to(torch.float32)
            bits = torch.flip(bits, dims=[1]).flatten()
            bits = bits[:len(ch.card_list)*2]
            inputs.append(bits)
            scores.append(score)
        self.inputs = torch.stack(inputs).to(device)
        self.scores = torch.tensor(scores, dtype=torch.float32, device=device)
    def __len__(self):
        return self.inputs.size(0)

    def __getitem__(self, idx):
        return self.inputs[idx], self.scores[idx]


class ValueNet(nn.Module):
    def __init__(self, dropout=0.4):
        super().__init__()
        
        self.matchup_score = nn.Sequential(
             nn.Linear(len(ch.card_list)*2, 1024),
            # nn.BatchNorm1d(1024),
            nn.ReLU(0.1),
            nn.Dropout(dropout),

            nn.Linear(1024, 256),
            # nn.BatchNorm1d(256),
            nn.ReLU(0.1),
            nn.Dropout(dropout),

            # nn.Linear(512, 256),
            
            # nn.LeakyReLU(0.1),
            # nn.Dropout(dropout),
            # nn.Linear(512, 256),
            # # nn.BatchNorm1d(128),
            # nn.LeakyReLU(0.1),
            # nn.Dropout(dropout),
            nn.Linear(256, 128),
            # nn.BatchNorm1d(64),
            nn.ReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            # nn.BatchNorm1d(64),
            nn.ReLU(0.1),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Tanh()
        )

    def forward(self, cards_vec):
        return self.matchup_score(cards_vec).squeeze(-1)

# -----------------------
# Training loop
# -----------------------
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    dataset = read_training_dataset()

    # --- Print first entry for inspection ---
    # first_input, first_score = dataset[0]
    # print("First input vector (bits):", first_input)
    # print("First score:", first_score)
    # print("Sum of bits in first input:", first_input.sum().item())
    # print("Length of input vector:", len(first_input))
    # print("--- End of first entry ---")

    n_val = int(len(dataset) * VAL_SPLIT)
    n_train = len(dataset) - n_val
    train_set, val_set = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

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

        # Validation
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
