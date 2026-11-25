"""Stage 2: fine-tuned Llama 3.2 1B (ExecuTorch FP16 .pte) explains the Stage-1 verdict, streamed token by token."""
import time
import torch
from executorch.extension.llm.custom_ops import custom_ops  # noqa: F401  registers llama::update_cache, custom_sdpa
from executorch.kernels import quantized                     # noqa: F401
from executorch.runtime import Runtime
from transformers import AutoTokenizer
from . import config
from .lang import dominant_script


class Stage2:
    def __init__(self, pte=config.STAGE2_PTE, tok_dir=config.STAGE2_TOKENIZER):
        self.tok = AutoTokenizer.from_pretrained(tok_dir)
        self.method = Runtime.get().load_program(pte).load_method("forward")
        self.batch_prefill = None          # decided on first call: can the model take the whole prompt at once?

    def _run(self, ids, pos):
        out = self.method.execute([torch.tensor([ids], dtype=torch.long), torch.tensor([pos], dtype=torch.long)])[0]
        return out.reshape(-1, out.shape[-1])[-1]

    def _prefill(self, ids):
        if self.batch_prefill is not False:
            try:
                logits = self._run(ids, 0)
                self.batch_prefill = True
                return logits
            except Exception:
                self.batch_prefill = False
        logits = None
        for i, t in enumerate(ids):
            logits = self._run([t], i)
        return logits

    def prompt_ids(self, sms, verdict):
        msgs = [{"role": "system", "content": config.SYSTEM_PROMPT},
                {"role": "user", "content": f"Classifier verdict: {verdict}\nSMS: {sms}"}]
        text = self.tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def stream(self, sms, verdict, max_new=None):
        """Yields (text_so_far, stats). stats['done'] is True on the last yield."""
        if max_new is None:
            max_new = config.MAX_NEW_LATIN if dominant_script(sms) == "latin" else config.MAX_NEW_INDIC
        ids = self.prompt_ids(sms, verdict)
        t0 = time.perf_counter()
        logits = self._prefill(ids)
        ttft = time.perf_counter() - t0
        out, pos, t1 = [], len(ids), time.perf_counter()
        stats = {"prompt_tokens": len(ids), "ttft_s": ttft, "new_tokens": 0, "tok_s": 0.0,
                 "truncated": False, "done": False, "batch_prefill": self.batch_prefill}
        for _ in range(max_new):
            nxt = int(logits.argmax())
            if nxt in config.EOS_IDS:
                break
            out.append(nxt)
            logits = self._run([nxt], pos)
            pos += 1
            dt = max(time.perf_counter() - t1, 1e-6)
            stats.update(new_tokens=len(out), tok_s=len(out) / dt)
            yield self.tok.decode(out, skip_special_tokens=True), stats
        else:
            stats["truncated"] = True
        stats["done"] = True
        yield self.tok.decode(out, skip_special_tokens=True), stats
