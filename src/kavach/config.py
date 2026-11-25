"""Paths and settings. Override any path with an environment variable."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STAGE1_PTE = os.environ.get("KAVACH_STAGE1_PTE", os.path.join(ROOT, "models", "kavach_int8_small.pte"))
STAGE1_TOKENIZER = os.environ.get("KAVACH_STAGE1_TOKENIZER", os.path.join(ROOT, "models"))
STAGE1_SEQ = 64            # input length the Stage-1 model was exported with (overridden by models/kavach_meta.json)
_meta = os.path.join(os.path.dirname(STAGE1_PTE), "kavach_meta.json")
if os.path.exists(_meta):
    import json as _json
    STAGE1_SEQ = int(_json.load(open(_meta)).get("stage1_seq", STAGE1_SEQ))

STAGE2_PTE = os.environ.get("KAVACH_STAGE2_PTE", os.path.join(ROOT, "models", "llama", "kavach_llama_fp16.pte"))
STAGE2_TOKENIZER = os.environ.get("KAVACH_STAGE2_TOKENIZER", os.path.join(ROOT, "models", "llama", "kavach_tokenizer"))

SCAM_THRESHOLD = 0.5       # Stage-1 probability above this = SCAM

# Must match the system prompt used during LoRA fine-tuning (KAVACH_llama_kaggle_v3)
SYSTEM_PROMPT = ("You are KAVACH, an on-device scam-safety assistant for Indian phone users. "
                 "The on-device classifier has already decided whether the SMS is a SCAM or GENUINE. "
                 "Explain that verdict in the same language and script as the SMS, in exactly 3 short lines: "
                 "1) why, pointing to the specific clue in this SMS, 2) what NOT to do, 3) what to do.")
EOS_IDS = (128009, 128001)
MAX_NEW_LATIN = 180        # English / Tanglish / Hinglish ...
MAX_NEW_INDIC = 420        # Tamil / Telugu / Bengali / Hindi scripts need more tokens per word
