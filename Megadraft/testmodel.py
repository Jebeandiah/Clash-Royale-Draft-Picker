import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import sqlite3

DB_NAME = "testdb.db"
INPUT_LEN = 357
OUTPUT_LEN = 116
BATCH_SIZE = 512
NUM_WORKERS = 0
EPOCHS = 50
LR = 1e-3

# -----------------------
# Dataset
# -----------------------
class DraftDataset(Dataset):
    def __init__(self, db_name):
        con = sqlite3.connect(db_name)
        cur = con.cursor()
        cur.execute("SELECT input, next_card, score FROM training")
        rows = cur.fetchall()
        con.close()

        self.samples = []
        for input_blob, next_card, score in rows:
            byte_tensor = torch.frombuffer(input_blob, dtype=torch.uint8).clone()
            bits = ((byte_tensor.unsqueeze(1) >> torch.arange(8)) & 1).view(-1).float()
            bits = bits[:INPUT_LEN]
            self.samples.append((bits, next_card, score))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        x, y, score = self.samples[idx]
        return x, y, score

# -----------------------
# Model
# -----------------------
class DraftMLP(nn.Module):
    def __init__(self, input_size=INPUT_LEN, output_size=OUTPUT_LEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Linear(512, output_size)
        )

    def forward(self, x):
        return self.net(x)

# -----------------------
# Training
# -----------------------
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    dataset = DraftDataset(DB_NAME)
    # split 90% train / 10% validation
    n_train = int(0.9 * len(dataset))
    n_val = len(dataset) - n_train
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=NUM_WORKERS, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=NUM_WORKERS, pin_memory=True
    )

    model = DraftMLP().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)
    scaler = torch.cuda.amp.GradScaler()

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for inputs, next_card, score in train_loader:
            inputs = inputs.to(device, non_blocking=True)
            next_card = next_card.to(device, dtype=torch.long, non_blocking=True)
            score = score.to(device, dtype=torch.float, non_blocking=True)

            optimizer.zero_grad()
            with torch.cuda.amp.autocast():
                outputs = model(inputs)  # [B, 116]
                pred_score = outputs.gather(1, next_card.view(-1, 1)).squeeze(1)
                loss = criterion(pred_score, score)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for inputs, next_card, score in val_loader:
                inputs = inputs.to(device, non_blocking=True)
                next_card = next_card.to(device, dtype=torch.long, non_blocking=True)
                score = score.to(device, dtype=torch.float, non_blocking=True)
                outputs = model(inputs)
                pred_score = outputs.gather(1, next_card.view(-1, 1)).squeeze(1)
                val_loss += criterion(pred_score, score).item()
        val_loss /= len(val_loader)

        print(f"Epoch {epoch+1}/{EPOCHS} - Train Loss: {avg_loss:.4f} - Val Loss: {val_loss:.4f}")

    torch.save(model.state_dict(), "draft_mlp_score.pth")
    print("✅ Training complete — model saved to draft_mlp_score.pth")


if __name__ == "__main__":
    print("PyTorch version:", torch.__version__)
    print("CUDA version:", torch.version.cuda)
    print("CUDA available:", torch.cuda.is_available())
    print("GPU count:", torch.cuda.device_count())
    train()
