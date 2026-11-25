"""Stage 1: IndicBERT INT8 classifier (ExecuTorch .pte, XNNPACK) -> SCAM / GENUINE."""
import time
import torch
from transformers import AutoTokenizer
from executorch.runtime import Runtime
from . import config


class Stage1:
    def __init__(self, pte=config.STAGE1_PTE, tok_dir=config.STAGE1_TOKENIZER):
        self.tok = AutoTokenizer.from_pretrained(tok_dir, keep_accents=True, use_fast=False)
        self.method = Runtime.get().load_program(pte).load_method("forward")
        self.predict("warm up")

    def predict(self, sms):
        e = self.tok(sms, truncation=True, padding="max_length", max_length=config.STAGE1_SEQ, return_tensors="pt")
        t0 = time.perf_counter()
        logits = self.method.execute([e["input_ids"], e["attention_mask"]])[0]
        ms = (time.perf_counter() - t0) * 1000
        p_scam = float(torch.softmax(logits.float(), -1)[0, 1])
        verdict = "SCAM" if p_scam >= config.SCAM_THRESHOLD else "GENUINE"
        return {"verdict": verdict, "p_scam": p_scam, "latency_ms": ms}
