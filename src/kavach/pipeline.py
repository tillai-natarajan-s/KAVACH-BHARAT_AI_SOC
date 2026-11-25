"""KAVACH pipeline: Stage 1 verdict -> link check -> Stage 2 explanation (streamed) -> checker -> fallback."""
import os
from . import config
from .lang import detect_language
from .urlcheck import check_links
from .checker import check
from .fallback import fallback_message


class Kavach:
    def __init__(self, load_stage2=True):
        from .stage1 import Stage1
        self.stage1 = Stage1()
        self.stage2 = None
        self.stage2_error = None
        if load_stage2:
            if os.path.exists(config.STAGE2_PTE):
                try:
                    from .stage2 import Stage2
                    self.stage2 = Stage2()
                except Exception as e:  # keep running with verified fallbacks only
                    self.stage2_error = repr(e)
            else:
                self.stage2_error = f"Stage-2 model not found at {config.STAGE2_PTE}"

    def detect(self, sms):
        r = self.stage1.predict(sms)
        r["lang"] = detect_language(sms)
        r["links"] = check_links(sms)
        r["final"] = r["verdict"]
        if r["verdict"] == "GENUINE" and any(l["risk"] == "HIGH" for l in r["links"]):
            r["final"] = "SCAM"                     # a dangerous link overrides a 'genuine' text verdict
            r["override"] = "phishing link"
        return r

    def explain_stream(self, sms, verdict, lang):
        """Yields (display_text, info). info['source'] is 'llm' or 'fallback' on the last yield."""
        if self.stage2 is None:
            cat, msg = fallback_message(sms, lang, verdict)
            yield msg, {"source": "fallback", "reason": self.stage2_error, "category": cat, "done": True}
            return
        text, stats = "", {}
        for text, stats in self.stage2.stream(sms, verdict):
            if not stats["done"]:
                yield text, {"source": "llm", "done": False, **stats}
        ok, reason, lines = check(text, sms, truncated=stats.get("truncated", False))
        if ok:
            yield "\n".join(lines), {"source": "llm", "reason": reason, "done": True, **stats}
        else:
            cat, msg = fallback_message(sms, lang, verdict)
            yield msg, {"source": "fallback", "reason": reason, "category": cat, "llm_text": text,
                        "done": True, **stats}
