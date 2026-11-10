import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import sqlite3
import dBManager
import cardhelpers as ch

HALF_INPUT_LEN = len(ch.card_list)+1+len(ch.category_to_id) # 1 for elixer, 1 for each category, multi hot for each deck
BATCH_SIZE = 8192
NUM_WORKERS = 0
EPOCHS = 500
LR = 1e-5
DROPOUT = 0.25
VAL_SPLIT = 0.1
SCALE = 10000.0  # rough scale for score
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
def vectorize_deck(multi_hot):
   
    num_cards = len(ch.card_list)
    card_ids = torch.nonzero(multi_hot).flatten().tolist()
    cat_counts_norm = [0.0] * len(ch.category_to_id)
    elixir_norm =0
    for card_id in card_ids:
        elixir_norm += (ch.card_list[card_id].elixir/5)/8 #5 is apprx max avg elxer used to normalize
        cat_counts_norm[ch.category_to_id[ch.card_list[card_id].categories[0]]] += 1.0/8

    feature_vector = torch.cat([multi_hot, torch.tensor([elixir_norm] + cat_counts_norm,  dtype=torch.float32, device=multi_hot.device)])
  
    return feature_vector



class read_training_dataset(Dataset):
    
    def __init__(self, db_name=dBManager.DB_NAME, device=DEVICE):
        con = sqlite3.connect(f'{db_name}.db')
        cur = con.cursor()
        cur.execute("SELECT packed_decks, low_tower_dif FROM battles")
        rows = cur.fetchall()
        con.close()

        if len(rows) == 0:
            raise RuntimeError("No battle rows found in database.")

        num_cards = len(ch.card_list)
        inputs, scores = [], []

        for packed_blob, low_tower_dif in rows:
            # 1. Unpack bits from bytes
            packed = torch.tensor(list(packed_blob), dtype=torch.uint8)
            t = packed.view(-1, 1)
            bits = ((t & (1 << torch.arange(8))) > 0).to(torch.float32)
            bits = torch.flip(bits, dims=[1]).flatten()[:num_cards * 2]

            # 2. Slice out the two 120-dim multi-hot vectors (NO re-encoding needed!)
            p_multi_hot = bits[:num_cards]
            o_multi_hot = bits[num_cards:]
            p_vector = vectorize_deck(p_multi_hot)
            o_vector = vectorize_deck(o_multi_hot)
            combined_vector = torch.cat([p_vector, o_vector])
            score = float(low_tower_dif) / 9156.0
            inputs.append(combined_vector)
            scores.append(score)

            # 3. Add Swapped Perspective (B vs A) for perfect symmetry
            # swapped_bits = torch.cat([combined_vector[HALF_INPUT_LEN:], combined_vector[:HALF_INPUT_LEN]])
            # inputs.append(swapped_bits)
            # scores.append(-score)

        self.inputs = torch.stack(inputs).to(device)
        self.scores = torch.tensor(scores, dtype=torch.float32, device=device)

    def __len__(self):
        return self.inputs.size(0)

    def __getitem__(self, idx):
        return self.inputs[idx], self.scores[idx]

class ResidualBlock(nn.Module): 
    """Residual Block with GELU, LayerNorm, and Dropout for stable deep learning."""
    def __init__(self, dim, dropout=0.2):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.Dropout(dropout)
        )
        self.act = nn.GELU()

    def forward(self, x):
        return self.act(x + self.block(x))

class SwappedPerspectives(Dataset):
    def __init__(self, subset):
        self.subset = subset

    def __len__(self):
        return 2 * len(self.subset)

    def __getitem__(self, idx):
        inputs, score = self.subset[idx // 2]

        if idx % 2 == 0:
            return inputs, score

        player = inputs[:HALF_INPUT_LEN]
        opponent = inputs[HALF_INPUT_LEN:]
        return torch.cat([opponent, player]), -score
class OptimizedDeckEncoder(nn.Module):
    """
    Shared Siamese Encoder:
    Expands input -> processes via Residual Blocks -> compresses into a latent embedding.
    """
    def __init__(self, input_len=HALF_INPUT_LEN, embed_dim=64, dropout=DROPOUT):
        super().__init__()
        
        # 1. Feature Expansion Layer
        self.input_projection = nn.Sequential(
            nn.Linear(input_len, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        
        # 2. Deep Residual Processing Trunk
        self.res_block1 = ResidualBlock(256, dropout=dropout)
        self.res_block2 = ResidualBlock(256, dropout=dropout)
        
        # 3. Controlled Embedding Compression
        self.compress = nn.Sequential(
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, embed_dim),
            nn.LayerNorm(embed_dim)
        )

    def forward(self, x):
        x = self.input_projection(x)
        x = self.res_block1(x)
        x = self.res_block2(x)
        return self.compress(x)


class OptimizedValueNet(nn.Module):
    """
    Matchup Rating Head:
    Computes vector difference (h_a - h_b) to enforce mathematically perfect anti-symmetry.
    """
    def __init__(self, input_len=HALF_INPUT_LEN, embed_dim=64, dropout=DROPOUT):
        super().__init__()
        self.encoder = OptimizedDeckEncoder(input_len=input_len, embed_dim=embed_dim, dropout=dropout)

        # Takes 64-dim vector difference (h_a - h_b)
        self.classifier = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Tanh()
        )

    def forward(self, player_deck, opp_deck):
        # Pass both decks through identical shared encoder weights
        h_a = self.encoder(player_deck)
        h_b = self.encoder(opp_deck)

        # Vector difference guarantees model(A, B) == -model(B, A)
        diff = h_a - h_b
        return (0.5 * (self.classifier(diff) - self.classifier(-diff))).squeeze(-1)


# -----------------------
# Training Loop
# -----------------------
def train():
    device = torch.device(DEVICE)
    print("Training Device:", device)

    dataset = read_training_dataset(db_name=dBManager.DB_NAME, device=device)

    n_val = int(len(dataset) * VAL_SPLIT)
    n_train = len(dataset) - n_val
    train_set, val_set = random_split(dataset, [n_train, n_val])
    train_set = SwappedPerspectives(train_set)

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

    model = OptimizedValueNet(input_len=HALF_INPUT_LEN, dropout=DROPOUT).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    criterion = nn.MSELoss()
    
    # Cosine annealing learning rate scheduler for smooth convergence
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    use_amp = (device.type == "cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_val = float("inf")
    
    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0

        for inputs, targets in train_loader:
            optimizer.zero_grad()

            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                player_deck = inputs[:, :HALF_INPUT_LEN]
                opp_deck = inputs[:, HALF_INPUT_LEN:]
                preds = model(player_deck, opp_deck)
                loss = criterion(preds, targets)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * inputs.size(0)

        train_loss /= len(train_set)
        scheduler.step()

        # Validation Step
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_nonzero = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                    player_deck = inputs[:, :HALF_INPUT_LEN]
                    opp_deck = inputs[:, HALF_INPUT_LEN:]
                    preds = model(player_deck, opp_deck)
                    val_loss += criterion(preds, targets).item() * inputs.size(0)
                    mask = targets != 0
                    val_correct += ((preds.sign() == targets.sign()) & mask).sum().item()
                    val_nonzero += mask.sum().item()

        val_loss /= len(val_set)

        if epoch % 1 == 0 or epoch == 1:
            print(f"Epoch {epoch:03d}/{EPOCHS} — Train MSE: {train_loss:.6f} | Val MSE: {val_loss:.6f} | LR: {scheduler.get_last_lr()[0]:.6f} | Outcome prediction accuracy: {val_correct / val_nonzero:.2%}")

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), "value_net_best.pth")

    torch.save(model.state_dict(), "value_net_final.pth")
    print("Training finished! Final model saved to value_net_final.pth")


if __name__ == "__main__":
    train()