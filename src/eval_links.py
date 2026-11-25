"""Measure the RULE-BASED link checker (feed switched OFF) on real phishing URLs from the saved
OpenPhish feed, and on a hand-picked list of legitimate Indian / popular websites.
   python eval_links.py      -> link_eval_results.json"""
import json
import os
import random
from kavach import urlcheck

LEGIT = """https://www.onlinesbi.sbi/ https://www.hdfcbank.com/personal https://www.icicibank.com/ https://www.axisbank.com/
https://www.kotak.com/en/home.html https://www.amazon.in/gp/your-orders https://www.flipkart.com/account/orders
https://www.irctc.co.in/nget/train-search https://www.incometax.gov.in/iec/foportal/ https://uidai.gov.in/
https://www.cybercrime.gov.in/ https://www.npci.org.in/ https://paytm.com/ https://www.phonepe.com/
https://www.swiggy.com/ https://www.zomato.com/chennai https://www.jio.com/selfcare https://www.airtel.in/
https://www.wikipedia.org/ https://github.com/ https://stackoverflow.com/questions https://www.thehindu.com/
https://www.ndtv.com/ https://timesofindia.indiatimes.com/ https://www.hotstar.com/in https://www.netflix.com/in/
https://www.linkedin.com/feed/ https://www.instagram.com/ https://www.facebook.com/ https://x.com/home
https://www.microsoft.com/en-in https://www.apple.com/in/ https://www.zoho.com/mail/ https://www.naukri.com/
https://www.makemytrip.com/ https://www.olx.in/ https://www.bigbasket.com/ https://www.nykaa.com/
https://www.ajio.com/ https://www.meesho.com/ https://in.bookmyshow.com/ https://www.redbus.in/
https://www.uber.com/in/en/ https://www.practo.com/ https://www.1mg.com/ https://www.apollo247.com/
https://www.coursera.org/ https://nptel.ac.in/courses https://www.annauniv.edu/ https://home.iitd.ac.in/
https://www.iitm.ac.in/ https://www.kaggle.com/ https://huggingface.co/ https://pytorch.org/
https://www.raspberrypi.com/ https://www.arm.com/ https://www.python.org/ https://www.digilocker.gov.in/
https://web.umang.gov.in/ https://www.mygov.in/ https://www.rbi.org.in/ https://www.sebi.gov.in/
https://www.nseindia.com/ https://www.bseindia.com/ https://zerodha.com/ https://groww.in/
https://www.policybazaar.com/ https://licindia.in/ https://www.epfindia.gov.in/ https://www.tnpsc.gov.in/
https://chennaimetrorail.org/ https://www.tnstc.in/ https://www.sbicard.com/ https://www.jiocinema.com/
https://www.youtube.com/watch?v=abc https://maps.google.com/ https://mail.google.com/ https://www.dropbox.com/
https://www.canva.com/ https://www.notion.so/ https://www.spotify.com/in-en/ https://www.cricbuzz.com/
https://www.espncricinfo.com/ https://www.amazon.com/ https://www.ebay.com/ https://www.reddit.com/
https://www.quora.com/ https://www.bbc.com/news https://www.indiatoday.in/ https://www.moneycontrol.com/
https://www.myntra.com/ https://www.decathlon.in/ https://www.croma.com/ https://www.reliancedigital.in/
https://www.tataneu.com/ https://www.bajajfinserv.in/ https://www.pnbindia.in/ https://www.bankofbaroda.in/
https://www.canarabank.com/ https://www.unionbankofindia.co.in/ https://www.indianbank.in/ https://www.iob.in/
https://fastag.ihmcl.com/ https://www.tangedco.org/ https://www.bsesdelhi.com/ https://www.wbsedcl.in/
https://www.whatsapp.com/ https://telegram.org/ https://zoom.us/ https://teams.microsoft.com/
https://www.w3schools.com/ https://www.geeksforgeeks.org/ https://leetcode.com/ https://www.hackerrank.com/""".split()


def rate(urls, use_feed):
    out = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "none": 0}
    for u in urls:
        r = urlcheck.check_links(u, use_feed=use_feed)
        out[r[0]["risk"] if r else "none"] += 1
    n = len(urls)
    return {"n": n, **out, "high_pct": round(100 * out["HIGH"] / n, 1),
            "high_or_medium_pct": round(100 * (out["HIGH"] + out["MEDIUM"]) / n, 1)}


feed = sorted(urlcheck.FEED_URLS)
if not feed:
    raise SystemExit("No offline feed found. Run:  python update_feed.py")
phish = ["https://" + u if not u.startswith("http") else u for u in feed]

res = {"feed": urlcheck.feed_info(),
       "phishing_rules_only": rate(phish, use_feed=False),
       "phishing_with_feed": rate(phish, use_feed=True),
       "legit_rules_only": rate(LEGIT, use_feed=False),
       "legit_with_feed": rate(LEGIT, use_feed=True)}
fp = [u for u in LEGIT if urlcheck.check_links(u, use_feed=False)[0]["risk"] != "LOW"]
res["legit_flagged_examples"] = [(u, urlcheck.check_links(u, use_feed=False)[0]["risk"],
                                  urlcheck.check_links(u, use_feed=False)[0]["reasons"]) for u in fp]
random.seed(0)
missed = [u for u in phish if urlcheck.check_links(u, use_feed=False)[0]["risk"] == "LOW"]
res["phish_missed_by_rules_examples"] = random.sample(missed, min(10, len(missed)))

json.dump(res, open("link_eval_results.json", "w"), indent=2)
print(json.dumps({k: v for k, v in res.items() if "examples" not in k}, indent=2))
print("\nLegit sites flagged by rules:")
for u, r, why in res["legit_flagged_examples"]:
    print(f"  {r:6s} {u}  <- {'; '.join(why)}")
print("\nSaved link_eval_results.json")
