"""Verified fallback messages, used when the on-device LLM output fails validation.

Each message is 3 lines: why / what NOT to do / what to do. Written and checked by hand,
so the user always receives correct advice even if the small LLM produces a broken answer.
"""
import re

# Order matters: the first category whose keywords match wins.
CATEGORY_KEYWORDS = [
    ("POLICE", ["police", "cbi", "arrest", "court", "customs", "drugs", "narcotics", "digital arrest", "warrant",
                "போலீஸ்", "கைது", "போதை", "पुलिस", "गिरफ्तार", "ड्रग्स", "पुलिस", "পুলিশ", "গ্রেপ্তার", "মাদক",
                "పోలీస్", "అరెస్ట్", "డ్రగ్స్"]),
    ("IMPERSONATION", ["new number", "pudhu number", "puthu number", "naya number", "notun number", "kotha number",
                       "army", "olx", "by mistake", "galti se", "thappa", "bhul kore", "wrong transfer", "boss",
                       "manager", "beta", "amma", "mom", "papa", "appa", "gift card",
                       "புது நம்பர்", "ராணுவ", "மேனேஜர்", "अम्मा", "नया नंबर", "आर्मी", "मैनेजर", "बेटा", "पापा",
                       "নতুন নম্বর", "আর্মি", "ম্যানেজার", "মা,", "కొత్త నంబర్", "ఆర్మీ", "మేనేజర్", "అమ్మా"]),
    ("BILL", ["electricity", "bijli", "current", "eb bill", "power cut", "fastag", "challan", "gas connection",
              "tneb", "tangedco", "bses", "uppcl", "msedcl", "cesc", "wbsedcl", "tsspdcl", "apspdcl",
              "மின்", "बिजली", "চালান", "বিদ্যুৎ", "కరెంట్", "విద్యుత్"]),
    ("FEE", ["prize", "lottery", "kbc", "refund", "cashback", "loan", "job", "task", "earn", "deposit", "fee",
             "invest", "profit", "double", "crypto", "trading", "scholarship", "bonus", "reward", "like videos",
             "பரிசு", "கடன்", "வேலை", "லாபம்", "इनाम", "लोन", "नौकरी", "पुरस्कार", "लॉटरी", "कमाएं",
             "লোন", "চাকরি", "লটারি", "পুরস্কার", "లోన్", "లాటరీ", "ఉద్యోగం", "బహుమతి"]),
    ("BANK_OTP", ["kyc", "otp", "upi pin", " pin", "account", "a/c", "debit", "credit card", "net banking", "bank", "pan card", "aadhaar", "sim",
                  "வங்கி", "கணக்கு", "बैंक", "खाता", "ব্যাংক", "অ্যাকাউন্ট", "బ్యాంక్", "ఖాతా"]),
]


def detect_category(sms):
    t = sms.lower()
    if "otp" in t or "upi pin" in t:          # an OTP/PIN request is the core trick, whatever the story around it
        return "BANK_OTP" if not any(w in t for w in ["police", "cbi", "arrest", "पुलिस", "போலீஸ்", "পুলিশ", "పోలీస్"]) else "POLICE"
    for cat, words in CATEGORY_KEYWORDS:
        if any(w in t for w in words):
            return cat
    return "OTHER"


MESSAGES = {
 "en": {
  "BANK_OTP": "This is a scam: banks never ask you to update KYC, share an OTP or enter your UPI PIN through an SMS or call.\nDo not click the link, reply, or share any OTP, PIN or card details.\nCheck only in your bank's official app or branch, and report it on 1930 or cybercrime.gov.in.",
  "FEE": "This is a scam: real prizes, refunds, loans and jobs never ask you to pay a fee or deposit first.\nDo not pay any fee, enter your UPI PIN, or install apps from the link.\nIgnore the offer, block the number, and report it on 1930 or cybercrime.gov.in.",
  "BILL": "This is a scam: electricity, gas and FASTag providers do not threaten same-day cut-off by SMS and ask you to call a personal number.\nDo not call that number, pay through the link, or install any app.\nCheck your bill only on the official website or app, and report it on 1930 or cybercrime.gov.in.",
  "POLICE": "This is a scam: police, CBI, courts or customs never arrest anyone or demand money over a call or SMS; 'digital arrest' does not exist.\nDo not pay, share documents, or stay on a video call with them.\nHang up, tell your family, and report it on 1930 or cybercrime.gov.in.",
  "IMPERSONATION": "This is a scam: someone is pretending to be a relative, officer, buyer or boss to get money quickly.\nDo not send money or scan any QR code to 'receive' a payment.\nCall the real person on their old number first, and report it on 1930 or cybercrime.gov.in.",
  "OTHER": "This message looks like a scam: it creates urgency and asks for money or personal details.\nDo not reply, click links, or pay anything.\nVerify through official channels, and report it on 1930 or cybercrime.gov.in.",
  "GENUINE": "This looks genuine: it does not ask for money, an OTP, a PIN or a click on an unknown link.\nStill, never share an OTP or PIN with anyone who calls about this message.\nIf in doubt, check directly in the official app or with the sender you know.",
 },
 "ta": {
  "BANK_OTP": "இது மோசடி: வங்கிகள் SMS அல்லது அழைப்பு மூலம் KYC அப்டேட், OTP அல்லது UPI PIN ஒருபோதும் கேட்காது.\nலிங்கை கிளிக் செய்யவோ, OTP, PIN, கார்டு விவரங்களைப் பகிரவோ வேண்டாம்.\nஉங்கள் வங்கியின் அதிகாரப்பூர்வ செயலி அல்லது கிளையில் மட்டும் சரிபார்க்கவும்; 1930 அல்லது cybercrime.gov.in-ல் புகார் செய்யவும்.",
  "FEE": "இது மோசடி: உண்மையான பரிசு, ரீஃபண்ட், கடன், வேலை எதற்கும் முதலில் கட்டணம் அல்லது டெபாசிட் கேட்கப்படாது.\nஎந்தக் கட்டணமும் செலுத்தவோ, UPI PIN போடவோ, லிங்கிலிருந்து ஆப் நிறுவவோ வேண்டாம்.\nஅந்த எண்ணை பிளாக் செய்து 1930 அல்லது cybercrime.gov.in-ல் புகார் செய்யவும்.",
  "BILL": "இது மோசடி: மின்சாரம், கேஸ், FASTag நிறுவனங்கள் SMS மூலம் இன்றே இணைப்பு துண்டிப்பு என மிரட்டி தனிப்பட்ட எண்ணுக்கு அழைக்கச் சொல்லாது.\nஅந்த எண்ணுக்கு அழைக்கவோ, லிங்கில் பணம் கட்டவோ, ஆப் நிறுவவோ வேண்டாம்.\nஅதிகாரப்பூர்வ இணையதளம் அல்லது செயலியில் மட்டும் பில்லைச் சரிபார்க்கவும்; 1930 அல்லது cybercrime.gov.in-ல் புகார் செய்யவும்.",
  "POLICE": "இது மோசடி: போலீஸ், CBI, நீதிமன்றம், சுங்கத்துறை யாரும் அழைப்பு அல்லது SMS மூலம் கைது செய்யவோ பணம் கேட்கவோ மாட்டார்கள்; 'டிஜிட்டல் கைது' என்று எதுவும் இல்லை.\nபணம் அனுப்பவோ, ஆவணங்களைப் பகிரவோ, வீடியோ காலில் தொடரவோ வேண்டாம்.\nஅழைப்பைத் துண்டித்து குடும்பத்தினரிடம் சொல்லுங்கள்; 1930 அல்லது cybercrime.gov.in-ல் புகார் செய்யவும்.",
  "IMPERSONATION": "இது மோசடி: உறவினர், அதிகாரி, வாங்குபவர் அல்லது மேலதிகாரி போல நடித்து அவசரமாகப் பணம் கேட்கிறார்கள்.\nபணம் அனுப்பவோ, 'பணம் பெற' QR கோடை ஸ்கேன் செய்யவோ வேண்டாம்.\nமுதலில் அந்த நபரின் பழைய எண்ணுக்கு அழைத்து உறுதி செய்யுங்கள்; 1930 அல்லது cybercrime.gov.in-ல் புகார் செய்யவும்.",
  "OTHER": "இந்தச் செய்தி மோசடி போலத் தெரிகிறது: அவசரப்படுத்தி பணம் அல்லது தனிப்பட்ட விவரங்களைக் கேட்கிறது.\nபதில் அனுப்பவோ, லிங்கை கிளிக் செய்யவோ, பணம் கட்டவோ வேண்டாம்.\nஅதிகாரப்பூர்வ வழிகளில் சரிபார்த்து 1930 அல்லது cybercrime.gov.in-ல் புகார் செய்யவும்.",
  "GENUINE": "இது உண்மையான செய்தியாகத் தெரிகிறது: பணம், OTP, PIN அல்லது தெரியாத லிங்க் எதுவும் கேட்கவில்லை.\nஇருந்தாலும், இதைப் பற்றி யாராவது அழைத்தால் OTP அல்லது PIN-ஐப் பகிர வேண்டாம்.\nசந்தேகம் இருந்தால் அதிகாரப்பூர்வ செயலி அல்லது தெரிந்த நபரிடம் நேரடியாக உறுதி செய்யுங்கள்.",
 },
 "hi": {
  "BANK_OTP": "यह धोखा है: बैंक कभी SMS या कॉल से KYC अपडेट, OTP या UPI PIN नहीं मांगते।\nलिंक पर क्लिक न करें, और OTP, PIN या कार्ड की जानकारी किसी को न दें।\nकेवल बैंक के आधिकारिक ऐप या शाखा में जांचें, और 1930 या cybercrime.gov.in पर शिकायत करें।",
  "FEE": "यह धोखा है: असली इनाम, रिफंड, लोन या नौकरी के लिए पहले कोई फीस या जमा राशि नहीं मांगी जाती।\nकोई फीस न भरें, UPI PIN न डालें, और लिंक से कोई ऐप इंस्टॉल न करें।\nनंबर ब्लॉक करें और 1930 या cybercrime.gov.in पर शिकायत करें।",
  "BILL": "यह धोखा है: बिजली, गैस या FASTag कंपनियां SMS से उसी दिन कनेक्शन काटने की धमकी देकर निजी नंबर पर कॉल नहीं करवातीं।\nउस नंबर पर कॉल न करें, लिंक से भुगतान न करें, कोई ऐप इंस्टॉल न करें।\nबिल केवल आधिकारिक वेबसाइट या ऐप पर जांचें, और 1930 या cybercrime.gov.in पर शिकायत करें।",
  "POLICE": "यह धोखा है: पुलिस, CBI, अदालत या कस्टम कभी कॉल या SMS पर गिरफ्तारी या पैसे की मांग नहीं करते; 'डिजिटल अरेस्ट' जैसा कुछ नहीं होता।\nपैसे न भेजें, दस्तावेज़ न दें, और वीडियो कॉल पर न रुकें।\nकॉल काटें, परिवार को बताएं, और 1930 या cybercrime.gov.in पर शिकायत करें।",
  "IMPERSONATION": "यह धोखा है: कोई रिश्तेदार, अधिकारी, खरीदार या बॉस बनकर जल्दी पैसे मांग रहा है।\nपैसे न भेजें और 'पैसे पाने' के लिए कोई QR कोड स्कैन न करें।\nपहले उस व्यक्ति को उनके पुराने नंबर पर कॉल करें, और 1930 या cybercrime.gov.in पर शिकायत करें।",
  "OTHER": "यह संदेश धोखा लगता है: यह जल्दबाजी कराकर पैसे या निजी जानकारी मांगता है।\nजवाब न दें, लिंक पर क्लिक न करें, कोई भुगतान न करें।\nआधिकारिक माध्यम से जांचें और 1930 या cybercrime.gov.in पर शिकायत करें।",
  "GENUINE": "यह संदेश असली लगता है: इसमें पैसे, OTP, PIN या किसी अनजान लिंक की मांग नहीं है।\nफिर भी, इसके बारे में कोई कॉल करे तो OTP या PIN साझा न करें।\nशक हो तो आधिकारिक ऐप या जान-पहचान वाले व्यक्ति से सीधे पुष्टि करें।",
 },
 "bn": {
  "BANK_OTP": "এটি প্রতারণা: ব্যাংক কখনো SMS বা কলে KYC আপডেট, OTP বা UPI PIN চায় না।\nলিংকে ক্লিক করবেন না, আর OTP, PIN বা কার্ডের তথ্য কাউকে দেবেন না।\nশুধু ব্যাংকের অফিসিয়াল অ্যাপ বা শাখায় যাচাই করুন, আর 1930 বা cybercrime.gov.in-এ অভিযোগ করুন।",
  "FEE": "এটি প্রতারণা: আসল পুরস্কার, রিফান্ড, লোন বা চাকরির জন্য আগে কোনো ফি বা জমা চাওয়া হয় না।\nকোনো ফি দেবেন না, UPI PIN দেবেন না, লিংক থেকে কোনো অ্যাপ ইনস্টল করবেন না।\nনম্বরটি ব্লক করুন এবং 1930 বা cybercrime.gov.in-এ অভিযোগ করুন।",
  "BILL": "এটি প্রতারণা: বিদ্যুৎ, গ্যাস বা FASTag সংস্থা SMS-এ আজই সংযোগ কাটার হুমকি দিয়ে ব্যক্তিগত নম্বরে কল করতে বলে না।\nওই নম্বরে কল করবেন না, লিংকে টাকা দেবেন না, কোনো অ্যাপ ইনস্টল করবেন না।\nশুধু অফিসিয়াল ওয়েবসাইট বা অ্যাপে বিল দেখুন, আর 1930 বা cybercrime.gov.in-এ অভিযোগ করুন।",
  "POLICE": "এটি প্রতারণা: পুলিশ, CBI, আদালত বা কাস্টমস কখনো কল বা SMS-এ গ্রেপ্তার বা টাকা দাবি করে না; 'ডিজিটাল অ্যারেস্ট' বলে কিছু নেই।\nটাকা পাঠাবেন না, নথি দেবেন না, ভিডিও কলে থাকবেন না।\nকল কেটে দিন, পরিবারকে জানান, আর 1930 বা cybercrime.gov.in-এ অভিযোগ করুন।",
  "IMPERSONATION": "এটি প্রতারণা: কেউ আত্মীয়, অফিসার, ক্রেতা বা বস সেজে তাড়াতাড়ি টাকা চাইছে।\nটাকা পাঠাবেন না এবং 'টাকা পাওয়ার' জন্য কোনো QR কোড স্ক্যান করবেন না।\nআগে সেই ব্যক্তির পুরনো নম্বরে কল করে নিশ্চিত হন, আর 1930 বা cybercrime.gov.in-এ অভিযোগ করুন।",
  "OTHER": "এই বার্তাটি প্রতারণা মনে হচ্ছে: তাড়াহুড়ো করিয়ে টাকা বা ব্যক্তিগত তথ্য চাইছে।\nউত্তর দেবেন না, লিংকে ক্লিক করবেন না, কোনো টাকা দেবেন না।\nঅফিসিয়াল উপায়ে যাচাই করুন এবং 1930 বা cybercrime.gov.in-এ অভিযোগ করুন।",
  "GENUINE": "এটি আসল বার্তা মনে হচ্ছে: এতে টাকা, OTP, PIN বা অচেনা লিংক চাওয়া হয়নি।\nতবুও, এ নিয়ে কেউ কল করলে OTP বা PIN দেবেন না।\nসন্দেহ হলে অফিসিয়াল অ্যাপ বা পরিচিত ব্যক্তির কাছে সরাসরি যাচাই করুন।",
 },
 "te": {
  "BANK_OTP": "ఇది మోసం: బ్యాంకులు SMS లేదా కాల్ ద్వారా KYC అప్‌డేట్, OTP లేదా UPI PIN ఎప్పుడూ అడగవు.\nలింక్‌పై క్లిక్ చేయవద్దు, OTP, PIN లేదా కార్డ్ వివరాలు ఎవరికీ చెప్పవద్దు.\nమీ బ్యాంక్ అధికారిక యాప్ లేదా బ్రాంచ్‌లో మాత్రమే తనిఖీ చేయండి, 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
  "FEE": "ఇది మోసం: నిజమైన బహుమతి, రీఫండ్, లోన్ లేదా ఉద్యోగానికి ముందుగా ఫీజు లేదా డిపాజిట్ అడగరు.\nఎలాంటి ఫీజు చెల్లించవద్దు, UPI PIN ఎంటర్ చేయవద్దు, లింక్ నుండి యాప్ ఇన్‌స్టాల్ చేయవద్దు.\nఆ నంబర్‌ను బ్లాక్ చేసి 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
  "BILL": "ఇది మోసం: కరెంట్, గ్యాస్ లేదా FASTag సంస్థలు SMS ద్వారా ఈరోజే కనెక్షన్ కట్ చేస్తామని బెదిరించి వ్యక్తిగత నంబర్‌కు కాల్ చేయమనవు.\nఆ నంబర్‌కు కాల్ చేయవద్దు, లింక్‌లో డబ్బు కట్టవద్దు, యాప్ ఇన్‌స్టాల్ చేయవద్దు.\nఅధికారిక వెబ్‌సైట్ లేదా యాప్‌లో మాత్రమే బిల్లు చూడండి, 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
  "POLICE": "ఇది మోసం: పోలీస్, CBI, కోర్టు లేదా కస్టమ్స్ ఎవరూ కాల్ లేదా SMS ద్వారా అరెస్ట్ చేయరు, డబ్బు అడగరు; 'డిజిటల్ అరెస్ట్' అనేది లేదు.\nడబ్బు పంపవద్దు, పత్రాలు ఇవ్వవద్దు, వీడియో కాల్‌లో ఉండవద్దు.\nకాల్ కట్ చేసి కుటుంబానికి చెప్పండి, 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
  "IMPERSONATION": "ఇది మోసం: ఎవరో బంధువు, అధికారి, కొనుగోలుదారు లేదా బాస్‌లా నటించి త్వరగా డబ్బు అడుగుతున్నారు.\nడబ్బు పంపవద్దు, 'డబ్బు అందుకోవడానికి' QR కోడ్ స్కాన్ చేయవద్దు.\nముందుగా ఆ వ్యక్తి పాత నంబర్‌కు కాల్ చేసి నిర్ధారించుకోండి, 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
  "OTHER": "ఈ సందేశం మోసంలా ఉంది: తొందరపెట్టి డబ్బు లేదా వ్యక్తిగత వివరాలు అడుగుతోంది.\nసమాధానం ఇవ్వవద్దు, లింక్‌పై క్లిక్ చేయవద్దు, డబ్బు చెల్లించవద్దు.\nఅధికారిక మార్గాల్లో తనిఖీ చేసి 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
  "GENUINE": "ఇది నిజమైన సందేశంలా ఉంది: ఇందులో డబ్బు, OTP, PIN లేదా తెలియని లింక్ అడగలేదు.\nఅయినా, దీని గురించి ఎవరైనా కాల్ చేస్తే OTP లేదా PIN చెప్పవద్దు.\nసందేహం ఉంటే అధికారిక యాప్ లేదా తెలిసిన వ్యక్తితో నేరుగా నిర్ధారించుకోండి.",
 },
 "tanglish": {
  "BANK_OTP": "Idhu mosadi: bank-ga SMS illa call moolama KYC update, OTP illa UPI PIN eppavume kekka maattaanga.\nLink-ai click pannadheenga, OTP, PIN, card details yaarkittayum sollaadheenga.\nUnga bank-oda official app illa branch-la mattum check pannunga; 1930 illa cybercrime.gov.in-la complaint pannunga.",
  "FEE": "Idhu mosadi: unmaiyaana parisu, refund, loan, velai edhukkum mudhalla fee illa deposit kekka maattaanga.\nEndha fee-um kattadheenga, UPI PIN podaadheenga, link-la irundhu app install pannadheenga.\nAndha number-ai block panni 1930 illa cybercrime.gov.in-la complaint pannunga.",
  "BILL": "Idhu mosadi: EB, gas, FASTag company-ga SMS-la inniku connection cut-nu mirati personal number-ku call panna solla maattaanga.\nAndha number-ku call pannadheenga, link-la panam kattadheenga, app install pannadheenga.\nOfficial website illa app-la mattum bill check pannunga; 1930 illa cybercrime.gov.in-la complaint pannunga.",
  "POLICE": "Idhu mosadi: police, CBI, court, customs yaarum call illa SMS-la arrest panna maattaanga, panam kekka maattaanga; 'digital arrest'-nu onnum illa.\nPanam anuppaadheenga, documents kudukkaadheenga, video call-la irukkaadheenga.\nCall-ai cut panni veetla sollunga; 1930 illa cybercrime.gov.in-la complaint pannunga.",
  "IMPERSONATION": "Idhu mosadi: yaaro sondhakaarar, officer, buyer illa boss maadhiri nadichu avasarama panam kekkuraanga.\nPanam anuppaadheenga, 'panam vara' QR code scan pannadheenga.\nMudhalla andha aaloda pazhaya number-ku call panni confirm pannunga; 1930 illa cybercrime.gov.in-la complaint pannunga.",
  "OTHER": "Indha message mosadi maadhiri irukku: avasarappaduthi panam illa personal details kekkudhu.\nReply pannadheenga, link click pannadheenga, panam kattadheenga.\nOfficial vazhiyila check panni 1930 illa cybercrime.gov.in-la complaint pannunga.",
  "GENUINE": "Idhu unmaiyaana message maadhiri irukku: panam, OTP, PIN illa theriyaadha link edhuvum kekkala.\nAanaalum, idha pathi yaaraavadhu call panna OTP illa PIN sollaadheenga.\nSandhegam irundha official app illa therinja aal kitta nerla confirm pannunga.",
 },
 "hinglish": {
  "BANK_OTP": "Yeh fraud hai: bank kabhi SMS ya call par KYC update, OTP ya UPI PIN nahi maangte.\nLink par click na karein, OTP, PIN ya card details kisi ko na dein.\nSirf bank ke official app ya branch mein check karein, aur 1930 ya cybercrime.gov.in par complaint karein.",
  "FEE": "Yeh fraud hai: asli inaam, refund, loan ya naukri ke liye pehle koi fee ya deposit nahi maanga jaata.\nKoi fee na bharein, UPI PIN na daalein, link se koi app install na karein.\nNumber block karein aur 1930 ya cybercrime.gov.in par complaint karein.",
  "BILL": "Yeh fraud hai: bijli, gas ya FASTag company SMS par aaj hi connection kaatne ki dhamki dekar personal number par call nahi karvaati.\nUs number par call na karein, link se payment na karein, koi app install na karein.\nBill sirf official website ya app par check karein, aur 1930 ya cybercrime.gov.in par complaint karein.",
  "POLICE": "Yeh fraud hai: police, CBI, court ya customs kabhi call ya SMS par arrest ya paise ki maang nahi karte; 'digital arrest' jaisa kuch nahi hota.\nPaise na bhejein, documents na dein, video call par na rukein.\nCall kaatein, family ko batayein, aur 1930 ya cybercrime.gov.in par complaint karein.",
  "IMPERSONATION": "Yeh fraud hai: koi rishtedaar, officer, buyer ya boss bankar jaldi paise maang raha hai.\nPaise na bhejein aur 'paise paane' ke liye koi QR code scan na karein.\nPehle us insaan ko unke purane number par call karke confirm karein, aur 1930 ya cybercrime.gov.in par complaint karein.",
  "OTHER": "Yeh message fraud lagta hai: jaldbaazi karwa ke paise ya personal details maang raha hai.\nReply na karein, link par click na karein, koi payment na karein.\nOfficial tareeke se check karein aur 1930 ya cybercrime.gov.in par complaint karein.",
  "GENUINE": "Yeh message asli lagta hai: isme paise, OTP, PIN ya kisi anjaan link ki maang nahi hai.\nPhir bhi, iske baare mein koi call kare to OTP ya PIN share na karein.\nShak ho to official app ya jaan-pehchaan wale insaan se seedha confirm karein.",
 },
 "banglish": {
  "BANK_OTP": "Eta protarona: bank kokhono SMS ba call-e KYC update, OTP ba UPI PIN chay na.\nLink-e click korben na, OTP, PIN ba card-er tottho karo ke deben na.\nShudhu bank-er official app ba branch-e jachai korun, ar 1930 ba cybercrime.gov.in-e obhijog korun.",
  "FEE": "Eta protarona: ashol puroskar, refund, loan ba chakrir jonno age kono fee ba joma chawa hoy na.\nKono fee deben na, UPI PIN deben na, link theke kono app install korben na.\nNumber-ta block kore 1930 ba cybercrime.gov.in-e obhijog korun.",
  "BILL": "Eta protarona: biddut, gas ba FASTag songstha SMS-e aaji connection katar hoomki diye personal number-e call korte bole na.\nOi number-e call korben na, link-e taka deben na, kono app install korben na.\nShudhu official website ba app-e bill dekhun, ar 1930 ba cybercrime.gov.in-e obhijog korun.",
  "POLICE": "Eta protarona: police, CBI, adalot ba customs kokhono call ba SMS-e greftar ba taka dabi kore na; 'digital arrest' bole kichu nei.\nTaka pathaben na, document deben na, video call-e thakben na.\nCall kete din, poribar-ke janan, ar 1930 ba cybercrime.gov.in-e obhijog korun.",
  "IMPERSONATION": "Eta protarona: keu attiyo, officer, kreta ba boss sheje taratari taka chaiche.\nTaka pathaben na ebong 'taka paowar' jonno kono QR code scan korben na.\nAge shei manush-er purono number-e call kore nishchit hon, ar 1930 ba cybercrime.gov.in-e obhijog korun.",
  "OTHER": "Ei message-ta protarona mone hocche: tarahuro koriye taka ba byaktigoto tottho chaiche.\nUttor deben na, link-e click korben na, kono taka deben na.\nOfficial upaye jachai kore 1930 ba cybercrime.gov.in-e obhijog korun.",
  "GENUINE": "Eta ashol message mone hocche: ete taka, OTP, PIN ba ochena link chawa hoyni.\nTobuo, e niye keu call korle OTP ba PIN deben na.\nSondeho hole official app ba porichito manush-er kache sorasori jachai korun.",
 },
 "tenglish": {
  "BANK_OTP": "Idi mosam: banks SMS leda call dwara KYC update, OTP leda UPI PIN eppudu adagavu.\nLink meeda click cheyakandi, OTP, PIN leda card details evariki cheppakandi.\nMee bank official app leda branch lo matrame check cheyandi, 1930 leda cybercrime.gov.in lo complaint cheyandi.",
  "FEE": "Idi mosam: nijamaina bahumati, refund, loan leda udyogam kosam mundu fee leda deposit adagaru.\nE fee kattakandi, UPI PIN enter cheyakandi, link nundi app install cheyakandi.\nAa number ni block chesi 1930 leda cybercrime.gov.in lo complaint cheyandi.",
  "BILL": "Idi mosam: current, gas leda FASTag companies SMS lo eeroje connection cut chestamani bedirinchi personal number ki call cheyamanavu.\nAa number ki call cheyakandi, link lo dabbu kattakandi, app install cheyakandi.\nOfficial website leda app lo matrame bill chudandi, 1930 leda cybercrime.gov.in lo complaint cheyandi.",
  "POLICE": "Idi mosam: police, CBI, court leda customs evaru call leda SMS lo arrest cheyaru, dabbu adagaru; 'digital arrest' anedi ledu.\nDabbu pampakandi, documents ivvakandi, video call lo undakandi.\nCall cut chesi family ki cheppandi, 1930 leda cybercrime.gov.in lo complaint cheyandi.",
  "IMPERSONATION": "Idi mosam: evaro bandhuvu, officer, buyer leda boss la natinchi twaraga dabbu adugutunnaru.\nDabbu pampakandi, 'dabbu raavadaniki' QR code scan cheyakandi.\nMundu aa vyakti paata number ki call chesi confirm chesukondi, 1930 leda cybercrime.gov.in lo complaint cheyandi.",
  "OTHER": "Ee message mosam la undi: tondarapetti dabbu leda personal details adugutondi.\nReply ivvakandi, link meeda click cheyakandi, dabbu kattakandi.\nOfficial margallo check chesi 1930 leda cybercrime.gov.in lo complaint cheyandi.",
  "GENUINE": "Idi nijamaina message la undi: indulo dabbu, OTP, PIN leda teliyani link adagaledu.\nAyina, deeni gurinchi evaraina call cheste OTP leda PIN cheppakandi.\nSandeham unte official app leda telisina vyakti tho nerugaa confirm chesukondi.",
 },
}


def fallback_message(sms, lang, verdict):
    cat = "GENUINE" if verdict == "GENUINE" else detect_category(sms)
    table = MESSAGES.get(lang, MESSAGES["en"])
    return cat, table[cat]
