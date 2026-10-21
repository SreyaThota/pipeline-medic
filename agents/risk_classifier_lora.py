"""LoRA risk classifier (v0.5): MiniLM-L6 + LoRA adapter, trained by
ml/lora_finetune/train.py. Experimental: the graph keeps the prompted
classifier unless experiments/003 shows this one is better.
"""

from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.graph import RiskAssessment, RiskLevel
from ml.lora_finetune.data import LEVELS, risk_input_text
from ml.lora_finetune.train import BASE_MODEL


class LoraRiskClassifier:
    def __init__(self, adapter_dir: Path, max_tokens: int = 256):
        self.tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
        self.tokenizer.truncation_side = "left"
        base = AutoModelForSequenceClassification.from_pretrained(
            BASE_MODEL, num_labels=len(LEVELS), local_files_only=True)
        self.model = PeftModel.from_pretrained(base, adapter_dir).eval()
        self.max_tokens = max_tokens

    def predict(self, workflow: str | None, tail_lines: list[str]) -> tuple[RiskLevel, list[float]]:
        enc = self.tokenizer(risk_input_text(workflow, tail_lines), truncation=True,
                             max_length=self.max_tokens, return_tensors="pt")
        with torch.no_grad():
            probs = torch.softmax(self.model(**enc).logits[0], dim=-1).tolist()
        level: RiskLevel = LEVELS[max(range(len(LEVELS)), key=lambda i: probs[i])]  # type: ignore[assignment]
        return level, [round(p, 4) for p in probs]

    def run(self, workflow: str | None, tail_lines: list[str]) -> RiskAssessment:
        level, probs = self.predict(workflow, tail_lines)
        return RiskAssessment(level=level, method="lora",
                              rationale=f"p(low, medium, high) = {probs}")
