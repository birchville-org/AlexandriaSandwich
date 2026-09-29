#!/usr/bin/env python3
"""
AlexandriaSandwich - Katha 6 (Lion and Hare) Sanskrit Typesetting Generator
Matches the classical scholarly edition layout (Hertel 1915, HOS 14, pp. 20-21):
- 3-column layout: Left Marginalia (A 42, A 43) | Sanskrit Core | Right Marginalia (Line numbers, Verse 62)
- Zero wrapping across original Sanskrit lines
- High-quality typography (Shobhika / Devanagari MT / EB Garamond)
- Includes original German philological translation and notes
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
PDF_DIR = OUTPUT_DIR / "pdf"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)


def generate_html() -> str:
    return """<!DOCTYPE html>
<html lang="sa">
<head>
<meta charset="utf-8">
<title>Tantrākhyāyikā — Kathā 6 (Siṃha-Śaśaka-Kathā)</title>
<style>
@page {
  size: 210mm 297mm; /* A4 */
  margin: 15mm 18mm 12mm 18mm;
  @bottom-center {
    content: none;
  }
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Shobhika', 'Devanagari MT', serif;
  color: #111;
  background: #fff;
  -webkit-font-smoothing: antialiased;
}

.page {
  page-break-after: always;
  break-after: page;
  page-break-inside: avoid;
  break-inside: avoid;
  min-height: 265mm;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  position: relative;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 11pt;
  font-weight: 600;
  color: #222;
  border-bottom: 0.6pt solid #888;
  padding-bottom: 1.5mm;
  margin-bottom: 2.5mm;
}
.header-left { width: 15mm; text-align: left; }
.header-center { flex-grow: 1; text-align: center; letter-spacing: 1.5px; }
.header-right { width: 15mm; text-align: right; }

.page-subheader {
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 8.5pt;
  font-style: italic;
  color: #444;
  text-align: center;
  margin-bottom: 3.5mm;
}

/* Section Titles */
.section-title {
  font-size: 13pt;
  font-weight: 700;
  text-align: center;
  margin: 2.5mm 0 2mm 0;
  color: #12284c;
}

/* 3-Column Layout Row */
.row {
  display: flex;
  align-items: baseline;
  width: 100%;
  margin-bottom: 1.1mm;
}

.col-left {
  width: 14mm;
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 9.5pt;
  color: #666;
  text-align: left;
  flex-shrink: 0;
}

.col-center {
  width: 146mm;
  flex-grow: 1;
  flex-shrink: 0;
}

.col-right {
  width: 14mm;
  font-family: 'EB Garamond', 'Times New Roman', serif;
  font-size: 9pt;
  color: #666;
  text-align: right;
  flex-shrink: 0;
  white-space: nowrap;
}

/* Verse Styling */
.verse-text {
  font-size: 11.8pt;
  font-weight: 600;
  color: #1a1a1a;
  text-align: center;
  letter-spacing: 0.3px;
  line-height: 1.4;
}

/* Prose Styling */
.prose-text {
  font-size: 10.8pt;
  line-height: 1.42;
  color: #111;
  text-align: left;
  letter-spacing: 0.2px;
  white-space: nowrap;
}

/* Editorial Apparatus / Notes */
.apparatus-divider {
  width: 45%;
  border-top: 0.6pt solid #666;
  margin: 4mm 0 2.5mm 0;
}

.apparatus-box {
  margin-top: auto;
  font-family: 'EB Garamond', 'Linux Libertine', serif;
  font-size: 8.5pt;
  line-height: 1.35;
  color: #444;
  padding-top: 2mm;
}

.apparatus-box p {
  margin-bottom: 1mm;
}

/* German translation section */
.trans-page {
  font-family: 'EB Garamond', 'Linux Libertine', Georgia, serif;
  color: #1a1a1a;
  line-height: 1.38;
}
.trans-title {
  font-size: 13pt;
  font-weight: 700;
  text-align: center;
  margin-bottom: 3mm;
  color: #12284c;
}
.trans-block {
  margin-bottom: 2.2mm;
  font-size: 9.1pt;
  text-align: justify;
}
.trans-ref {
  font-weight: 600;
  color: #333;
}
</style>
</head>
<body>

<!-- ==========================================
     PAGE 1: Book Page 20 (Hertel 1915)
     ========================================== -->
<div class="page">
  <div class="page-header">
    <div class="header-left">20</div>
    <div class="header-center">Book I. THE ESTRANGING OF FRIENDS;</div>
    <div class="header-right"></div>
  </div>
  <div class="page-subheader">Tale v: Heron, fishes, and crab. Tale iv: Crows and serpent. Frame-story. Tale vi: Lion and hare.</div>

  <!-- Lines 1-3 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">प्रायात् । तैश्चाभिहितः । भ्रातः । क्वासौ माम इति । अथासाव-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">ब्रवीत् । पञ्चत्वमुपगतः । तस्यैतद्दुरात्मनः शिरः । भक्षितास्तेनोप-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">धिना बहवः स्वयूथ्या वः । सो ऽपि मत्सकाशाद्विनष्ट इति ।</div>
    <div class="col-right">3</div>
  </div>

  <!-- Lines 4-6 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">अतो ऽहं ब्रवीमि । भक्षयित्वा बहून्मत्स्यानिति । अथ वायसो</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">जम्बुकमाह । आवयोः किं प्राप्तकालं मन्यसे । गोमायुः । सुवर्ण-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">सूत्रमादायात्रावासके स्थाप्यताम् । असंशयं तत्स्वामी तं कृष्णसर्पं</div>
    <div class="col-right">6</div>
  </div>

  <!-- Lines 7-9 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">घातयिष्यति । इत्युक्त्वा स सृगालो ऽपक्रान्तः ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">अथ वायसः सुवर्णसूत्रान्वेषी राजगृहं प्रायात् । दृष्टं च तेनान्तः-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">पुरैकदेशे धौतवस्त्रयुगलोपरि सुवर्णसूत्रमुत्तममणिविरचितं म-</div>
    <div class="col-right">9</div>
  </div>

  <!-- Lines 10-12 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">हार्हं प्रक्षाल्य चेटिकया स्थापितम् । तच्चावस्थाप्यान्यया सह कथां</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">कर्तुमारब्धा । वायसस्तु तद्गृहीत्वा वियता शनैरात्मानं दर्शयन्स्व-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">मालयं प्रति प्रायात् । अथारक्षिपुरुषैः प्रासमुद्गरतोमरपाणिभिर्म-</div>
    <div class="col-right">12</div>
  </div>

  <!-- Lines 13-15 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">हता जवेन गत्वा वृक्षो ऽवलोकितः । यावत्तेन तत्स्वनीडे स्था-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">पितम् । तत्रैकेनारोहता दृष्टम् । कृष्णभुजंगो वायसपोतान्भक्ष-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">यित्वा निद्रावशमगमत् । तेन चासौ सुप्त एव घातितः । तत्कृत्वा</div>
    <div class="col-right">15</div>
  </div>

  <!-- Line 16 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">सुवर्णसूत्रमादाय गत इति ।</div>
    <div class="col-right"></div>
  </div>

  <!-- Lines 17-20: Transition & Verse 62 -->
  <div class="row" style="margin-top: 2mm;">
    <div class="col-left">A 42</div>
    <div class="col-center prose-text">अतो ऽहं ब्रवीमि । उपायेन हि यच्छक्यमिति । समाप्ते चाख्याने पुनराह ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row" style="margin-top: 1mm;">
    <div class="col-left"></div>
    <div class="col-center verse-text">यस्य बुद्धिर्बलं तस्य अबुधस्य कुतो बलम् ।</div>
    <div class="col-right">18</div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center verse-text">पश्य जातिबलः सिंहः शशकेन निपातितः ॥ ६२ ॥</div>
    <div class="col-right"></div>
  </div>
  <div class="row" style="margin-top: 1.5mm;">
    <div class="col-left">A 43</div>
    <div class="col-center prose-text">करटकः । कथं चैतत् । दमनकः ।</div>
    <div class="col-right"></div>
  </div>

  <!-- Line 21: Title of Katha 6 -->
  <div class="section-title">२१ ॥ कथा ६ ॥</div>

  <!-- Lines 22-24 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">अस्ति । कस्मिंश्चिद्वनान्तरे महान्सिंहः प्रतिवसति स्म । सो ऽजस्रं</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">मृगोत्सादं कुरुते । अथ ते मृगाः सर्व एवाभिमुखाः प्रणतचित्ता</div>
    <div class="col-right">24</div>
  </div>

  <div class="apparatus-box">
    <div class="apparatus-divider"></div>
    <p><strong>Textkritischer Apparat (Hertel 1915):</strong></p>
    <p>Z. 4: <em>बहून्मत्स्यानिति</em>] Druck im Original बहन्मत्स्यानिति. || Z. 18: <em>यस्य बुद्धिर्बलं...</em>] Vers 62 = Tantrākhyāyikā I.62 (vgl. Pañcatantra I.134, Hitopadeśa II.123). || Z. 20: <em>दमनकः</em>] Druckfehler im Erstdruck teils दद्मनकः.</p>
  </div>
</div>

<!-- ==========================================
     PAGE 2: Book Page 21 (Hertel 1915)
     ========================================== -->
<div class="page">
  <div class="page-header">
    <div class="header-left">21</div>
    <div class="header-center">OR, THE LION AND THE BULL. Book I.</div>
    <div class="header-right"></div>
  </div>
  <div class="page-subheader">Tale vi: Lion and hare.</div>

  <!-- Lines 1-3 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">हरिततृणाङ्कुरवक्त्रधारिणो ऽवनितलासक्तजानवस्तं मृगराजं वि-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">ज्ञापयामासुः । भो मृगराज । किमनेन परलोकविरुद्धेन स्वामिनो</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">नृशंसेन निष्कारणं सर्वमृगोत्सादनकर्मणा कृतेन । वयं तावद्वि-</div>
    <div class="col-right">3</div>
  </div>

  <!-- Lines 4-6 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">नष्टा एव । तवाप्याहारस्याभावः । तदुभयोपद्रवः । तत्प्रसीद । वयं</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">तु स्वामिन एकैकं वनचरं वारेण स्वजातिसमुत्थं प्रेषयामः । तथा</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">कृते कालपर्यायाच्छशकस्य वारो ऽभ्यागतः । स तु सर्वमृगाज्ञा-</div>
    <div class="col-right">6</div>
  </div>

  <!-- Lines 7-9 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">पितो रुषितमनाश्चिन्तयामास । अन्तकरो ऽयं मृत्युमुखप्रवेशः ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">किमधुना प्राप्तकालं ममेति । अथवा बुद्धिमतां किमशक्यम् ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">अहमेवोपायेन व्यापादयामि सिंहम् । इति तस्याहारवेलां क्षप-</div>
    <div class="col-right">9</div>
  </div>

  <!-- Lines 10-12 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">यित्वा गतः । असावपि क्षुत्क्षामकण्ठः क्रोधसंरक्तनयनः स्फुरद्व-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">दनदशनसंघर्षदंष्ट्राकरालो लाङ्गूलास्फालनाकारभयकृत्तमाह । सु-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">कुण्डैरपि किं क्रियते ऽन्यत्र प्राणवियोगात् । स त्वमद्य गतासुरेव ।</div>
    <div class="col-right">12</div>
  </div>

  <!-- Lines 13-15 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">को ऽयं तव वेलात्ययः । शशकः । न ममात्मवशस्यातिक्रान्ता ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">स्वामिन् । आहारवेला । सिंहः । केन विधृतो ऽसि । शशः । सिं-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">हेनेति । तच्छ्रुत्वा परमोद्विग्नहृदयः सिंहो ऽब्रवीत् । कथमन्यो ऽत्र</div>
    <div class="col-right">15</div>
  </div>

  <!-- Lines 16-18 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">मद्भुजपरिरक्षिते वने सिंह इति । शशो बाढमित्याह ।</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">अथ सिंहो व्यचिन्तयत् । किमनेन हतेन कारणं मम । तं सपत्नं</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">संदर्शयिष्यतीति । तं च व्यापाद्यैनं भक्षयिष्यामि । इति तमाह ।</div>
    <div class="col-right">18</div>
  </div>

  <!-- Lines 19-21 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">मम तं दुरात्मानं दर्शयस्वेति । असावपि शशो ऽन्तर्लीनमवहस्य</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">बृहस्पत्युशनसोर्नीतिशास्त्रं प्रमाणीकृत्य स्वार्थसिद्धये विमलज-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">लसंपन्नं द्विपुरुषप्राप्योदकमिष्टकाचितं महान्तं कूपमदर्शयत् ।</div>
    <div class="col-right">21</div>
  </div>

  <!-- Lines 22-24 -->
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">असावप्यात्मकायप्रतिबिम्बानभिज्ञतया कुमार्गापन्नचित्तो ऽयम-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">सौ सपत्न इति मत्वा सहसैव तस्योपरि संनिपतितो मौर्ख्यात्प-</div>
    <div class="col-right"></div>
  </div>
  <div class="row">
    <div class="col-left"></div>
    <div class="col-center prose-text">ञ्चत्वमगमत् ।</div>
    <div class="col-right">24</div>
  </div>

  <div class="apparatus-box">
    <div class="apparatus-divider"></div>
    <p><strong>Textkritischer Apparat (Hertel 1915):</strong></p>
    <p>Z. 1: <em>हरिततृणाङ्कुरवक्त्रधारिणो</em>] Druck im Original हरिततृणाङ्करवक्तधारिणो. || Z. 2: <em>भो मृगराज</em>] Druck im Original mit Apostroph hinter भो मृगराज’. || Z. 6: <em>कालपर्यायाच्छशकस्य</em>] Druck im Original कालपर्याच्छशकस्य. || Z. 11: <em>लाङ्गूलास्फालनाकार-</em>] Druck im Original लाङ्गलास्फालनाकार-. || Z. 20: <em>बृहस्पत्युशनसोर्नीतिशास्त्रं</em>] Bṛhaspati und Uśanas (Śukra) gelten als die mythischen Begründer der Artha- und Nīti-Wissenschaften.</p>
  </div>
</div>

<!-- ==========================================
     PAGE 3: Deutsche philologische Übersetzung
     ========================================== -->
<div class="page trans-page">
  <div class="page-header">
    <div class="header-left">Übersetzung</div>
    <div class="header-center">TANTRĀKHYĀYIKĀ — KATHĀ 6 (LÖWE UND HÄSLEIN)</div>
    <div class="header-right">S. 20–21</div>
  </div>

  <div class="trans-title">Deutsche Arbeitsübersetzung mit philologischer Kommentierung</div>

  <div class="trans-block">
    <span class="trans-ref">[S. 20, Z. 1–4: Abschluss der Erzählung von Reiher, Fischen und Krabbe]</span><br>
    Er [die Krabbe] ging davon und wurde von ihnen [den Fischen] gefragt: »Bruder, wo ist unser Onkel [der Reiher]?« Da sprach jener: »Er ist zur Fünfheit eingegangen [gestorben]. Hier ist der Kopf dieses Bösewichts! Durch seine Hinterlist wurden gar viele von eurer Schar gefressen. Doch auch er hat durch mein Zutun sein Leben eingebüßt.« Daher sage ich: »Nachdem er viele Fische gefressen hatte ...«
  </div>

  <div class="trans-block">
    <span class="trans-ref">[S. 20, Z. 4–7: Krähe und Schakal]</span><br>
    Darauf sprach die Krähe zum Schakal: »Was hältst du für das Gebot der Stunde für uns beide?« Der Schakal [namens Gomāyu] erwiderte: »Bring eine Goldschnur [ein kostbares Halsband] herbei und lege sie in seiner Behausung nieder. Ohne Zweifel wird ihr Besitzer diese schwarze Kobra erschlagen.« Nach diesen Worten entfernte sich der Schakal.
  </div>

  <div class="trans-block">
    <span class="trans-ref">[S. 20, Z. 8–16: Die Krähe stiehlt das Halsband]</span><br>
    Nun flog die Krähe, nach einer Goldschnur spähend, zum Palast des Königs. Und es wurde von ihr gesehen, wie im Frauenpalast eine kostbare, mit erlesenen Edelsteinen besetzte Goldschnur von einer Dienerin nach dem Waschen auf ein Paar frisch gereinigter Gewänder gelegt worden war. Kaum hatte jene sie hingelegt, begann sie mit einer anderen [Dienerin] ein Gespräch. Die Krähe aber ergriff das Halsband und flog, indem sie sich in den Lüften langsam zeigte, zu ihrer Behausung zurück. Da eilten Palastwächter mit Lanzen, Keulen und Wurfspießen in Händen in größter Eile herbei und erblickten den Baum, gerade als die Krähe den Schmuck in ihr Nest legte. Dort sah einer, der hinaufkletterte: Die schwarze Kobra war, nachdem sie die Krähenbrut gefressen hatte, fest eingeschlafen. Und eben schlafend wurde sie von jenem erschlagen. Nachdem die Wächter dies getan hatten, nahmen sie die Goldschnur an sich und gingen von dannen.
  </div>

  <div class="trans-block">
    <span class="trans-ref">[S. 20, Z. 17–20: Rahmenerzählung und Leitvers 62]</span><br>
    Daher sage ich: »Was durch eine List bewirkt werden kann ...« Und als die Erzählung zu Ende war, sprach er abermals:
    <blockquote style="margin: 1.5mm 0 1.5mm 6mm; font-style: italic;">
      »Wer Klugheit besitzt, der hat auch Macht; woher aber nähme ein Unverständiger Macht?<br>
      Sieh nur: Der an Gattungsart gewaltige Löwe ward von einem kleinen Hasen zu Fall gebracht!« (Vers 62)
    </blockquote>
    Karaṭaka fragte: »Wie trug sich denn dies zu?« Damanaka sprach:
  </div>

  <div class="trans-block">
    <span class="trans-ref">[S. 20, Z. 21 – S. 21, Z. 5: Erzählung 6 — Klage und Pakt der Waldtiere]</span><br>
    Es war einmal: In einem gewissen Waldgebiet hauste ein gewaltiger Löwe. Der richtete unablässig ein Gemetzel unter dem Wild an. Da traten all jene Waldtiere vor ihn hin, mit demütigem Gemüt, grüne Grassprossen im Maule tragend [als Zeichen bedingungsloser Unterwerfung] und auf die Knie gesunken. Sie trugen dem König der Tiere ehrfurchtsvoll vor: »O Herrscher der Tiere! Was nützt es dem Gebieter, dieses dem Jenseits zuwiderlaufende, grausame Werk der Ausrottung allen Wildes ohne Grund zu vollbringen? Wir für unser Teil gehen ohnehin zugrunde; doch auch dir wird dadurch die Nahrung ausgehen. Das wäre ein Verderben für beide Teile! Sei daher gnädig: Wir wollen unserem Herrn je ein Waldtier nach der Reihe, aus eigener Art hervorgegangen, als Beute senden.«
  </div>

  <div class="trans-block">
    <span class="trans-ref">[S. 21, Z. 5–12: Die Reihe trifft den klugen Hasen]</span><br>
    Als dies so abgemacht war, kam im Laufe der Zeit die Reihe an einen kleinen Hasen. Dieser aber, dem die Weisung von allen Tieren erteilt worden war, dachte mit erbittertem Herzen bei sich: »Todbringend ist dieser Gang in den Rachen des Todes! Was ist nun für mich das Gebot der Stunde? Oder vielmehr: Was wäre für Kluge unmöglich? Eben durch eine List will ich diesen Löwen umbringen!« Indem er so seine Mittagsmahlzeit absichtlich verstreichen ließ, ging er schließlich hin. Jener [der Löwe] aber – die Kehle vor Hunger ausgedörrt, die Augen vor Wut blutunterlaufen, furchterregend durch das Knirschen seiner zuckenden Zähne und mit peitschendem Schweif Furcht einflößend – sprach zu ihm: »Was vermögen die aufs Äußerste Erzürnten anderes zu tun, als das Leben zu nehmen? Eben du bist heute des Todes! Was bedeutet diese deine Verspätung?«
  </div>

  <div class="trans-block">
    <span class="trans-ref">[S. 21, Z. 13–24: Die List mit dem Brunnen und Sturz des Löwen]</span><br>
    Der Hase sprach: »O Gebieter, nicht durch mein eigenes Verschulden ist die Mahlzeit verstrichen!« Der Löwe fragte: »Von wem wurdest du aufgehalten?« Der Hase sprach: »Von einem anderen Löwen!« Als er das hörte, sprach der Löwe mit aufs Höchste beunruhigtem Herzen: »Wie sollte hier in dem von meinen Pranken beschützten Wald ein anderer Löwe sein?« Der Hase erwiderte: »Gewiss, so ist es!« Da überlegte der Löwe bei sich: »Welchen Grund habe ich, diesen Kleinen jetzt schon zu töten? Er soll mir jenen Nebenbuhler zeigen! Und nachdem ich jenen umgebracht habe, werde ich diesen hier fressen.« So befahl er ihm: »Zeige mir diesen Schurken!«<br>
    Jener Hase lachte insgeheim in sich hinein, nahm sich die Staatsklugheitslehren des Bṛhaspati und Uśanas zur Richtschnur und führte ihn, um seinen eigenen Zweck zu erreichen, zu einem großen Brunnen, der mit klarem Wasser gefüllt, zwei Mannstiefen tief und aus Backsteinen gemauert war. Jener [der Löwe] aber erkannte in seiner Einfalt sein eigenes Spiegelbild nicht, verlor vor Verblendung jeden klaren Verstand, dachte: »Das ist jener Nebenbuhler!«, stürzte sich sogleich kopfüber auf ihn hinab und ging aus Torheit zur Fünfheit ein [ertrank im Brunnen].
  </div>
</div>

</body>
</html>"""


def main():
    html_file = OUTPUT_DIR / "Katha_06_clean_layout.html"
    pdf_file = PDF_DIR / "Katha_06_clean_layout.pdf"

    print("1) Generating HTML with 3-column layout...")
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
