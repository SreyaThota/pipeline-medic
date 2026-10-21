"""Fine-tune MiniLM-L6 with LoRA adapters to classify CI-failure risk.

Model choice: sentence-transformers/all-MiniLM-L6-v2 (22M parameters) is
already the project's embedding model, runs on a laptop CPU, and is cached
locally. LoRA (r=8) trains rank-8 updates to the attention query/value
matrices plus the new 3-way classification head, about 1% of the weights.

Hyper-parameters are fixed in advance, not tuned on the test split:
20 epochs, batch 8, learning rate 1e-3, max 256 tokens (truncated from the
left so the end of the log, where the error is, survives).

    python -m ml.lora_finetune.train --seed 0
"""

import argparse
import random
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml.lora_finetune.data import LEVELS, Example, load_examples

BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


@dataclass(frozen=True)
class TrainConfig:
    epochs: int = 20
    batch_size: int = 8
    learning_rate: float = 1e-3
    max_tokens: int = 256
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1


def _load_base(num_labels: int):  # type: ignore[no-untyped-def]
    try:
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            BASE_MODEL, num_labels=num_labels, local_files_only=True)
    except OSError:  # not cached in a form transformers can read: download once
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL, num_labels=num_labels)
    tokenizer.truncation_side = "left"
    return tokenizer, model


def train(seed: int, config: TrainConfig | None = None, out_dir: Path | None = None,
          examples: list[Example] | None = None) -> tuple[Path, dict[str, float]]:
    config = config or TrainConfig()
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, (torch.get_num_threads() or 2) // 2))
    examples = examples if examples is not None else load_examples()
    train_set = [e for e in examples if e.split in ("dev", "synthetic")]

    tokenizer, base = _load_base(len(LEVELS))
    model = get_peft_model(base, LoraConfig(
        task_type=TaskType.SEQ_CLS, r=config.lora_r, lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout, target_modules=["query", "value"]))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())

    counts = torch.tensor([sum(e.label == lvl for e in train_set) for lvl in LEVELS], dtype=torch.float)
    weights = counts.sum() / (len(LEVELS) * counts.clamp(min=1))
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                  lr=config.learning_rate)

    model.train()
    start = time.perf_counter()
    for _ in range(config.epochs):
        order = list(range(len(train_set)))
        random.shuffle(order)
        for i in range(0, len(order), config.batch_size):
            batch = [train_set[j] for j in order[i:i + config.batch_size]]
            enc = tokenizer([e.text for e in batch], truncation=True, max_length=config.max_tokens,
                            padding=True, return_tensors="pt")
            labels = torch.tensor([LEVELS.index(e.label) for e in batch])
            loss = loss_fn(model(**enc).logits, labels)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

    out_dir = out_dir or ARTIFACTS / f"seed{seed}"
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(out_dir)
    stats = {"train_examples": len(train_set), "trainable_params": trainable, "total_params": total,
             "train_seconds": round(time.perf_counter() - start, 1)}
    return out_dir, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the LoRA risk classifier.")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    path, stats = train(args.seed)
    print(f"adapter saved to {path}: {stats}")


if __name__ == "__main__":
    main()
