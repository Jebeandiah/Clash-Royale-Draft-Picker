import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import sqlite3

DB_NAME = "testdb.db"
INPUT_LEN = 357
OUTPUT_LEN = 116
BATCH_SIZE = 512
EPOCHS = 100
LR = 1e-3
DROPOUT = 0.2
REG_WEIGHT = 1e-4

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

            # --- normalize each section by constant, not sum ---
            s0 = bits[:116] 
            s1 = bits[116:232] 
            s2 = bits[232:348] 
            s3 = bits[348:357]  # one-hot draft step

            normalized_bits = torch.cat([s0, s1, s2, s3], dim=0)
            self.samples.append((normalized_bits, next_card, score))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        x, y, score = self.samples[idx]
        return x, y, score


# -----------------------
# Structured MLP Model
# -----------------------
class SubMLP(nn.Module):
    def __init__(self, input_dim=116, hidden_dim=256, dropout=DROPOUT):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim // 2),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return self.net(x)


class StructuredDraftMLP(nn.Module):
    def __init__(self, dropout=DROPOUT):
        super().__init__()
        self.s0_net = SubMLP()
        self.s1_net = SubMLP()
        self.s2_net = SubMLP()

        fusion_input_dim = (256 // 2) * 3 + 9
        self.norm_fuse = nn.LayerNorm(fusion_input_dim)
        self.fusion_net = nn.Sequential(
            nn.Linear(fusion_input_dim, 512),
            nn.ReLU(),
            nn.LayerNorm(512),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.LayerNorm(256),
            nn.Dropout(dropout),
            nn.Linear(256, OUTPUT_LEN)
        )

    def forward(self, x):
        s0 = x[:, :116]
        s1 = x[:, 116:232]
        s2 = x[:, 232:348]
        s3 = x[:, 348:357]
        z0, z1, z2 = self.s0_net(s0), self.s1_net(s1), self.s2_net(s2)
        fused = torch.cat([z0, z1, z2, s3], dim=1)
        fused = self.norm_fuse(fused)
        return self.fusion_net(fused)


# -----------------------
# Training
# -----------------------
def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    dataset = DraftDataset(DB_NAME)
    n_train = int(0.9 * len(dataset))
    train_set, val_set = torch.utils.data.random_split(dataset, [n_train, len(dataset) - n_train])

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False, pin_memory=True)

    model = StructuredDraftMLP().to(device)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    scaler = torch.cuda.amp.GradScaler()

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for x, next_card, score in train_loader:
            x = x.to(device)
            next_card = next_card.to(device, dtype=torch.long)
            score_norm = score.to(device, dtype=torch.float) / 1000.0  # smaller denom = stronger gradients

            optimizer.zero_grad()
            with torch.cuda.amp.autocast():
                out = model(x)
                pred = out.gather(1, next_card.view(-1, 1)).squeeze(1)
                target_loss = criterion(pred, score_norm)

                mask = torch.ones_like(out)
                mask.scatter_(1, next_card.view(-1, 1), 0.0)
                reg_loss = (out * mask).pow(2).mean()

                loss = target_loss + REG_WEIGHT * reg_loss

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, next_card, score in val_loader:
                x = x.to(device)
                next_card = next_card.to(device, dtype=torch.long)
                score_norm = score.to(device, dtype=torch.float) / 1000.0

                out = model(x)
                pred = out.gather(1, next_card.view(-1, 1)).squeeze(1)
                target_loss = criterion(pred, score_norm)
                mask = torch.ones_like(out)
                mask.scatter_(1, next_card.view(-1, 1), 0.0)
                reg_loss = (out * mask).pow(2).mean()

                val_loss += (target_loss + REG_WEIGHT * reg_loss).item()

        val_loss /= len(val_loader)
        print(f"Epoch {epoch+1}/{EPOCHS} — Train Loss: {avg_loss:.6f} — Val Loss: {val_loss:.6f}")

    torch.save(model.state_dict(), "structured_draft_mlp_fixed.pth")
    print("✅ Training complete — model saved to structured_draft_mlp_fixed.pth")


if __name__ == "__main__":
    train()
