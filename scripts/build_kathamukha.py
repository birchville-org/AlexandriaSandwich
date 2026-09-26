#!/usr/bin/env python3
"""
AlexandriaSandwich - Kathamukha Sanskrit Typesetting Generator (V3 Perfect Alignment)
- Allocates a dedicated 3-column layout: Left Marginalia (12mm) | Sanskrit Core (152mm) | Right Marginalia (16mm).
- Font size 10.8pt ensures zero wrapping across all 84-character Sanskrit lines.
- All verse numbers and philological cross-references are 100% visible and unclipped.
- High-resolution cleaned Latin critical apparatus cleanly anchored at bottom of each page.
- Exactly 3 pages matching classical Indian scholarly edition aesthetics.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
PDF_DIR = OUTPUT_DIR / "pdf"
IMG_DIR = OUTPUT_DIR / "images"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)


def generate_html() -> str:
    img_p1 = (IMG_DIR / "apparatus_p1.png").resolve()
    img_p2_l = (IMG_DIR / "apparatus_p2_left.png").resolve()
    img_p2_r = (IMG_DIR / "apparatus_p2_right.png").resolve()

    return f"""<!DOCTYPE html>
<html lang="sa">
<head>
<meta charset="utf-8">
<title>Tantrākhyāyikā — Kathāmukha</title>
<style>
@page {{
  size: 210mm 297mm; /* A4 */
  margin: 12mm 15mm 10mm 15mm;
  @bottom-center {{
    content: none;
  }}
}}

* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

body {{
  font-family: 'Shobhika', 'Devanagari MT', serif;
  color: #111;
  background: #fff;
  -webkit-font-smoothing: antialiased;
}}

.page {{
  page-break-after: always;
  break-after: page;
  page-break-inside: avoid;
  break-inside: avoid;
  height: 275mm;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  position: relative;
}}

/* Page Header */
.page-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 11pt;
  font-weight: 600;
  color: #222;
  border-bottom: 0.6pt solid #888;
  padding-bottom: 1.5mm;
  margin-bottom: 3.5mm;
}}
.header-left {{ width: 20mm; text-align: left; }}
.header-center {{ flex-grow: 1; text-align: center; letter-spacing: 2px; }}
.header-right {{ width: 20mm; text-align: right; }}

/* Invocation */
.invocation {{
  font-size: 14pt;
  font-weight: 700;
  text-align: center;
  margin: 1.5mm 0 3.5mm 0;
  color: #0b1a30;
  letter-spacing: 0.5px;
}}

/* Section Titles */
.section-title {{
  font-size: 13pt;
  font-weight: 700;
  text-align: center;
  margin: 2.2mm 0 1.8mm 0;
  color: #12284c;
}}

/* Colophon */
.colophon {{
  font-size: 13.5pt;
  font-weight: 700;
  text-align: center;
  margin: 2.5mm 0 2mm 0;
  color: #0b1a30;
}}

/* 3-Column Layout Row */
.row {{
  display: flex;
  align-items: baseline;
  width: 100%;
  margin-bottom: 0.9mm;
}}

.col-left {{
  width: 12mm;
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 9.5pt;
  color: #666;
  text-align: left;
  flex-shrink: 0;
}}

.col-center {{
  width: 152mm;
  flex-grow: 1;
  flex-shrink: 0;
}}

.col-right {{
  width: 16mm;
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 9pt;
  color: #666;
  text-align: right;
  flex-shrink: 0;
  white-space: nowrap;
}}

/* Verse Styling */
.verse-text {{
  font-size: 12.2pt;
  font-weight: 600;
  color: #1a1a1a;
  text-align: center;
  letter-spacing: 0.3px;
  line-height: 1.35;
}}

/* Prose Styling */
.prose-text {{
  font-size: 10.6pt;
  line-height: 1.38;
  color: #111;
  text-align: left;
  letter-spacing: 0.2px;
  white-space: nowrap;
}}

/* Footnote divider and apparatus */
.apparatus-divider {{
  width: 45%;
  border-top: 0.6pt solid #333;
  margin: 3.5mm 0 2mm 0;
}}

.apparatus-container {{
  margin-top: auto; /* anchor cleanly at bottom of page */
  width: 100%;
}}

.apparatus-img {{
  max-width: 100%;
  object-fit: contain;
  display: block;
}}
</style>
</head>
<body>

<!-- ==========================================
     PAGE 1: Book Page 1* (Kathāmukha Teil 1)
     ========================================== -->
<div class="page">
  <div class="page-header">
    <div class="header-left"></div>
    <div class="header-center">KATHĀMUKHA.</div>
    <div class="header-right"></div>
  </div>

  <div class="invocation">॥ ॐ स्वस्ति प्रजाभ्यः । ॐ नमो विघ्नहन्त्रे ॥</div>

  <!-- Verse 1 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">यत्रानिशं मधुकरीव मही निषण्णा</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">यत्पावनस्य मधुनः परमं निधानम् ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">तद्ब्रह्मणस्सकलमण्डलपुण्डरीकं</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">पायादनन्तवपुषः फणमण्डलं वः ॥ १ ॥</div>
    <div class="col-right">1</div>
  </div>

  <!-- Verse 2 -->
  <div class="row" style="margin-top: 1.5mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">मनवे वाचस्पतये शुक्राय पराशराय ससुताय ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">चाणक्याय च महते नमो ऽस्तु नृपशास्त्रकर्तृभ्यः ॥ २ ॥</div>
    <div class="col-right">SP 1</div>
  </div>

  <!-- Verse 3 -->
  <div class="row" style="margin-top: 1.5mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">सकलार्थशास्त्रसारं जगति समालोक्य विष्णुशर्मापि ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">तन्त्रैः पञ्चभिरेतैश्चकार सुमनोहरं शास्त्रम् ॥ ३ ॥</div>
    <div class="col-right">9</div>
  </div>

  <div class="section-title">तथानुश्रूयते ॥</div>

  <!-- Prose Lines (1:1 with original) -->
  <div class="row">
    <div class="col-left">A 1a</div>
    <div class="col-center prose-text">दाक्षिणात्ये जनपदे महिलारोप्यं नाम नगरम् । तत्र च सकलार्थिजनमनोरथकल्पद्रुमः प्रव-</div>
    <div class="col-right">Cf. SP 1. 7</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">रनरपतिमुकुटमणिमरीचिनिचयरञ्जितचरणयुगलः कलासु पारङ्गमसकलार्थशास्त्रविदमरश-</div>
    <div class="col-right">12</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">क्तिर्नाम राजा बभूव । तस्य च पुत्रास्त्रयः परमदुर्मेधसो वसुशक्तिरुग्रशक्तिरनेकशक्तिश्चेतिनामानो</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">बभूवुः । तानर्थशास्त्रं प्रति जडानालोक्य राजा सचिवानाहूय सम्प्रधारितवान् । ज्ञातमेव भव-</div>
    <div class="col-right"></div>
  </div>

  <div class="apparatus-container">
    <div class="apparatus-divider"></div>
    <img class="apparatus-img" style="max-height: 85mm;" src="file://{img_p1}" alt="Apparatus Page 1" />
  </div>
</div>

<!-- ==========================================
     PAGE 2: Book Page 4 (Kathāmukha Teil 2)
     ========================================== -->
<div class="page">
  <div class="page-header">
    <div class="header-left">4</div>
    <div class="header-center">KATHĀMUKHA.</div>
    <div class="header-right"></div>
  </div>

  <!-- Prose Block 1 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">द्भिः । यथा ममैते पुत्राः परमदुर्मेधसः । तदेषां बुद्धिप्रबोधनं केनोपायेनानुष्ठीयते । इति । तत्र</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">केचिदाहुः । देव । द्वादशभिर्वर्षैः । किल व्याकरणं ज्ञायत इति । तत्र केचिदाहुः । न वा ज्ञायते</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">च । ततो धर्मार्थकामशास्त्राणि ज्ञेयानि । तदेतदतिगहनं धीमतामपि । किं पुनर्मन्दबुद्धीनाम् ।</div>
    <div class="col-right">3</div>
  </div>
  <div class="row">
    <div class="col-left">A 1b</div>
    <div class="col-center prose-text">तदत्र वस्तुनि नीतिशास्त्रविद्विष्णुशर्मा नाम ब्राह्मणो ऽनेकशास्त्रविख्यातकीर्तिरस्ति । तमाहूय</div>
    <div class="col-right">Cf. SP. I. 26</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">तस्मै समर्प्यन्तां कुमाराः इति । एवमनुष्ठिते सचिवास्तं राजानं द्विजातिमार्गोचितेनाशीर्वादेना-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">भिनन्द्योपाविशत् । सुखोपविष्टं तमाह राजा । ब्रह्मन् । मदनुग्रहार्थमेतान्कुमारान्दुर्मेधसस्त्वमर्थशा-</div>
    <div class="col-right">6</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">स्त्रं प्रत्यनन्यसमान्कर्तुमर्हसि । अर्थमात्रया च त्वां सम्मानयिष्यामीति । एवमभिहितवति पार्थिवे</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">विष्णुशर्मापि तं राजानं विज्ञापितवान् ।</div>
    <div class="col-right"></div>
  </div>

  <!-- Verse 4 -->
  <div class="row" style="margin-top: 1.5mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">कार्यं यथा वदति यस्त तथा प्रकारो</div>
    <div class="col-right">9</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">युक्तं न युक्तमिदमित्यविचार्यमेतत् ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">उद्दिष्ट किं वदति को ऽनुशयो ऽस्य</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">को ऽयमेवार्थतत्त्वमिति तत्प्रमुखा विचार्यम् ॥ ४ ॥</div>
    <div class="col-right">12</div>
  </div>

  <!-- Prose Block 2 -->
  <div class="row" style="margin-top: 1.5mm;">
    <div class="col-left">A 2</div>
    <div class="col-center prose-text">तत्किं बहुना । श्रूयतामयं मम वचनसिंहनादः । नाहमर्थलिप्सुरित्येवं ब्रवीमि । न च ममाशी-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">तिवर्षस्य व्यावृत्तसर्वेन्द्रियस्य कश्चिदर्थोपभोगकालः । किन्तु लब्धितार्थं बुद्धिपूर्वोको ऽयमारम्भः ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">तस्मिन्नतामयतनो दिवसः । यद्यहं न षण्मासाभ्यन्तरात्तव पुत्रान्नीतिशास्त्रं प्रत्यनन्यसमान्करो-</div>
    <div class="col-right">15 SP. I. 27</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">मि । ततो ममार्हसि मार्गसन्दर्शनं हस्त्यशत्रुतमपकामयितुम् । इति ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">एतामसम्भाव्यां ब्राह्मणस्य प्रतिज्ञां श्रुत्वा ससचिवो राजा परं विस्मयमगमदाह च । यश्चाव-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">दर्थमेतं सम्पन्नमिति मां पुनर्विज्ञापयिष्यति । तस्याहं पुष्टमनुग्रहं करिष्यामि । इत्युक्त्वा ससम्मानं</div>
    <div class="col-right">18</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">तस्मै समर्पितवान्कुमारान् । तेनापि च सुपायमालोच्य शास्त्राणि लिखितानि पञ्च तन्त्राणि । न</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">सो ऽस्ति तिरश्चां मनुष्याणां वा । यं यथायोगं स्वार्थसिद्धये न निवेशितवान् ॥</div>
    <div class="col-right"></div>
  </div>

  <div class="colophon">॥ कथामुखमेतत्समाप्तम् ॥</div>

  <div class="apparatus-container">
    <div class="apparatus-divider"></div>
    <img class="apparatus-img" style="max-height: 80mm;" src="file://{img_p2_l}" alt="Apparatus Page 2 Left" />
  </div>
</div>

<!-- ==========================================
     PAGE 3: Book Page 5 (Tantra 1: Mitrabheda)
     ========================================== -->
<div class="page">
  <div class="page-header">
    <div class="header-left"></div>
    <div class="header-center">TANTRA I. MITRABHEDA.</div>
    <div class="header-right">5</div>
  </div>

  <!-- Opening -->
  <div class="row">
    <div class="col-left">A 3</div>
    <div class="col-center prose-text">अत इदमारभ्यते मित्रभेदं नाम प्रथमं तन्त्रम् । यस्यायमाद्यश्लोकः ।</div>
    <div class="col-right">SP I. 3</div>
  </div>

  <!-- Verse 1 -->
  <div class="row" style="margin-top: 1mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">वर्धमानो महान्स्नेहस्सिंहगोवृषयोर्वने ।</div>
    <div class="col-right">SP zu 1</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">पिशुनेनातिलुब्धेन जम्बुकेन विनाशितः ॥ १ ॥</div>
    <div class="col-right">3</div>
  </div>

  <div class="section-title">तथानुश्रूयते ॥</div>

  <!-- Prose Block 1 -->
  <div class="row">
    <div class="col-left">A 4</div>
    <div class="col-center prose-text">दाक्षिणात्ये जनपदे महिलारोप्यं नाम नगरम् । तत्र च धर्मोपार्जितवृत्तिर्वर्धमानको नाम</div>
    <div class="col-right">SP I. 3</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">श्रेष्ठिपुत्रो बभूव । तस्य कदाचिच्चित्तमुत्पन्नम् । प्रभूते ऽपि वित्ते ऽर्थवृद्धिः करणीयेति । उक्तं च ।</div>
    <div class="col-right">6</div>
  </div>

  <!-- Verse 2 -->
  <div class="row" style="margin-top: 1mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">अलभ्यमर्थं लिप्सेत लब्धं रक्षेच्चवेक्षया ।</div>
    <div class="col-right">SP I, 2</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">रक्षितं वर्धयेत्सम्यग्वृद्धं पात्रेषु निक्षिपेत् ॥ २ ॥</div>
    <div class="col-right"></div>
  </div>

  <!-- Prose Block 2 -->
  <div class="row" style="margin-top: 1mm;">
    <div class="col-left">A 5</div>
    <div class="col-center prose-text">अलब्धलाभार्था लब्धपरिरक्षणी रक्षितविवर्धिनी वर्धितस्य तीर्थप्रतिपादनी चेति लोकया-</div>
    <div class="col-right">9 SP I. 4</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">त्रा । अरक्ष्यमाणो ह्यर्थो बद्धपद्मवतया सद्यो विनश्यति । अवर्धमानो ऽप्यञ्जनादिचयदर्शनाच्छ-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">नैरप्युपयुज्यमानः क्षीयते । अनुपयुज्यमानः प्रयोजनोत्पत्तौ तुल्यो ऽप्राप्तेनेति । अतः प्राप्तस्य</div>
    <div class="col-right">12</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">रक्षाविवर्धनोपयोगाः कार्याः । उक्तं च ।</div>
    <div class="col-right">SP I, 3</div>
  </div>

  <!-- Verse 3 -->
  <div class="row" style="margin-top: 1mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">उपार्जितानामर्थानां त्याग एव हि रक्षणम् ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">तडाकोदरसंस्थानां परीवाह इवाम्भसाम् ॥ ३ ॥</div>
    <div class="col-right"></div>
  </div>

  <!-- Prose Block 3 -->
  <div class="row" style="margin-top: 1mm;">
    <div class="col-left">A 6</div>
    <div class="col-center prose-text">इति । एवं सम्प्रधार्य मधुरागामि भाण्डमुपसङ्गृह्य शुभे तिथौ गुरुजनानुज्ञातस्स्वस्मान्नगरा-</div>
    <div class="col-right">15 SP I. 4</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">द्विनिर्गतः । तस्य च द्वौ वृषभौ वोढारावयधुरायां नन्दकसञ्जीवकनामानावभूताम् । गच्छतस्तस्य</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">कस्मिंश्चिद्देशे दूरावच्छन्नगिरिनिर्झरस्खलितवारिजनितकर्दमैकचरणवैकल्याच्छकटस्य चातिभारा-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">दभिहतः कथमपि दैववशात्सञ्जीवको युगभङ्गं कृत्वा निपसाद । तं च दृष्ट्वा वर्धमानकस्सार्थवा-</div>
    <div class="col-right">18</div>
  </div>

  <div class="apparatus-container">
    <div class="apparatus-divider"></div>
    <img class="apparatus-img" style="max-height: 65mm;" src="file://{img_p2_r}" alt="Apparatus Page 2 Right" />
  </div>
</div>

</body>
</html>"""


def main():
    html_file = OUTPUT_DIR / "Kathamukha_clean_layout.html"
    pdf_file = PDF_DIR / "Kathamukha_clean_layout.pdf"

    print("1) Generating HTML with perfect 3-column alignment...")
    html_content = generate_html()
    html_file.write_text(html_content, encoding="utf-8")
    print(f"   -> Wrote HTML: {html_file}")

    print("2) Compiling with WeasyPrint...")
    cmd = ["/opt/homebrew/bin/weasyprint", str(html_file), str(pdf_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("WeasyPrint error:", res.stderr)
        raise SystemExit(res.returncode)
    print(f"   -> Successfully generated PDF: {pdf_file} ({pdf_file.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
