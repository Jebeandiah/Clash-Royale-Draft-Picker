

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import sqlite3
import dBManager
import cardhelpers as ch

MATCHUP_MODE = "concat"  # "concat" or "difference"
TARGET_MODE = "win"      # "win" (BCE) or "health_diff" (MSE)
HALF_INPUT_LEN = len(ch.card_list)+1+len(ch.properties_to_id) # 1 for elixer, 1 for each category, multi hot for each deck
# HALF_INPUT_LEN = len(ch.card_list)# 1 for elixer, 1 for each category, multi hot for each deck
BATCH_SIZE = 256
NUM_WORKERS = 0
EPOCHS = 500
LR = 1e-4
DROPOUT = 0.25
VAL_SPLIT = 0.1
SCALE = 10000.0  # rough scale for score
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
def vectorize_deck(multi_hot):
   
    num_cards = len(ch.card_list)
    card_ids = torch.nonzero(multi_hot).flatten().tolist()
    prop_counts_norm = [0.0] * len(ch.properties_to_id)
    elixir_norm =0
    for card_id in card_ids:
        elixir_norm += (ch.card_list[card_id].elixir/5)/8 #5 is apprx max avg elxer used to normalize
        for property in ch.card_list[card_id].properties:
            prop_counts_norm[ch.properties_to_id[property]] += 1.0/8

    feature_vector = torch.cat([multi_hot, torch.tensor([elixir_norm] + prop_counts_norm,  dtype=torch.float32, device=multi_hot.device)])
  
    return feature_vector
    # return multi_hot.float()  # Return the multi-hot vector as a float tensor



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
    def __init__(
        self,
        input_len=HALF_INPUT_LEN,
        embed_dim=64,
        dropout=DROPOUT,
        matchup_mode=MATCHUP_MODE,
        target_mode=TARGET_MODE,
    ):
        super().__init__()
        if matchup_mode not in ("concat", "difference"):
            raise ValueError(f"Unknown matchup mode: {matchup_mode}")
        if target_mode not in ("win", "health_diff"):
            raise ValueError(f"Unknown target mode: {target_mode}")

        self.matchup_mode = matchup_mode
        self.target_mode = target_mode
        self.encoder = OptimizedDeckEncoder(
            input_len=input_len, embed_dim=embed_dim, dropout=dropout
        )

        head_input = 2 * embed_dim if matchup_mode == "concat" else embed_dim
        self.classifier = nn.Sequential(
            nn.Linear(head_input, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, 1),
        )

    def forward(self, player_deck, opp_deck):
        h_a = self.encoder(player_deck)
        h_b = self.encoder(opp_deck)

        if self.matchup_mode == "concat":
            ab = torch.cat([h_a, h_b], dim=-1)
            ba = torch.cat([h_b, h_a], dim=-1)
        else:
            ab = h_a - h_b
            ba = -ab

        score = 0.5 * (self.classifier(ab) - self.classifier(ba))
        score = score.squeeze(-1)
        return score.tanh() if self.target_mode == "health_diff" else score


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None):
    training = optimizer is not None
    model.train(training)
    loss_total = 0.0
    loss_count = 0
    correct = 0
    nonzero_count = 0

    with torch.set_grad_enabled(training):
        for inputs, targets in loader:
            if model.target_mode == "win":
                keep = targets != 0
                inputs, targets = inputs[keep], targets[keep]
                if targets.numel() == 0:
                    continue
                labels = (targets > 0).float()
            else:
                labels = targets

            if training:
                optimizer.zero_grad()

            with torch.amp.autocast(
                device_type=device.type, enabled=device.type == "cuda"
            ):
                player_deck = inputs[:, :HALF_INPUT_LEN]
                opp_deck = inputs[:, HALF_INPUT_LEN:]
                predictions = model(player_deck, opp_deck)
                loss = criterion(predictions, labels)

            if training:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                nonzero = targets != 0
                correct += (
                    (predictions.sign() == targets.sign()) & nonzero
                ).sum().item()
                nonzero_count += nonzero.sum().item()

            loss_total += loss.item() * targets.numel()
            loss_count += targets.numel()

    if loss_count == 0:
        split = "Training" if training else "Validation"
        raise RuntimeError(f"{split} split has no usable targets.")

    accuracy = correct / nonzero_count if nonzero_count else None
    return loss_total / loss_count, accuracy


def train():
    device = torch.device(DEVICE)
    print(f"Training on {device} | matchup={MATCHUP_MODE} | target={TARGET_MODE}")

    dataset = read_training_dataset(db_name=dBManager.DB_NAME, device=device)
    n_val = int(len(dataset) * VAL_SPLIT)
    n_train = len(dataset) - n_val
    train_set, val_set = random_split(
        dataset,
        [n_train, n_val]
    )
    train_loader = DataLoader(
        SwappedPerspectives(train_set),
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
    )
    val_loader = DataLoader(
        val_set, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS
    )

    model = OptimizedValueNet().to(device)
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=EPOCHS, eta_min=1e-6
    )
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    if TARGET_MODE == "win":
        criterion = nn.BCEWithLogitsLoss()
        loss_name = "BCE"
    else:
        criterion = nn.MSELoss()
        loss_name = "MSE"

    checkpoint = f"value_net_{MATCHUP_MODE}_{TARGET_MODE}"
    best_val_acc = 0.0

    for epoch in range(1, EPOCHS + 1):
        train_loss, _ = run_epoch(
            model, train_loader, criterion, device, optimizer, scaler
        )
        val_loss, val_acc = run_epoch(model, val_loader, criterion, device)
        scheduler.step()

        accuracy = f"{val_acc:.2%}" if val_acc is not None else "N/A"
        print(
            f"Epoch {epoch:03d}/{EPOCHS} | Train {loss_name}: {train_loss:.6f} "
            f"| Val {loss_name}: {val_loss:.6f} | Val sign accuracy: {accuracy}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), f"{checkpoint}_best.pth")
            print(f"^ checkpoint ^")

    torch.save(model.state_dict(), f"{checkpoint}_final.pth")


if __name__ == "__main__":
    train()