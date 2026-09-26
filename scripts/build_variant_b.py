#!/usr/bin/env python3
"""
AlexandriaSandwich - Variant B Generator (Final Polish)
- Page 1: Re-typeset Latin IAST transliteration (two-column hemistichs, centered, clean accents).
- Pages 2-7: Devanagari pages transformed with larger font (13.2pt-16.2pt) and all blocks centered.
- Pages 8-11: Directly preserved from the original PDF (Oxford University Press vector pages).
- Assembly: Merged via qpdf on alex.local into a single 11-page master PDF.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "output"
PDF_DIR = OUTPUT_DIR / "pdf"
INPUT_PDF = ROOT / "data" / "input" / "RV_9.1.pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Pages 1 to 7 to be re-typeset
PAGES_DATA = [
    # Page 1: IAST Roman Transliteration
    {
        "page_num": 1,
        "type": "iast",
        "header_left": "",
        "header_center": "RIG VEDA - MAṆḌALA 9",
        "header_right": "",
        "footer_center": "-420-",
        "items": [
            {"type": "h2", "text": "9.1 (713). To Soma Pavamāna from Madhuchandas Vaiśvāmitra"},
            {"type": "subtitle", "text": "gāyatri"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "verse", "num": "1a.", "left": "svādiṣṭhayā mādiṣṭhayā", "right": "pāvasva soma dhārayā |"},
            {"type": "verse", "num": "1c.", "left": "indrāya pātave sutāḥ ||", "right": ""},
            {"type": "verse", "num": "2a.", "left": "rakṣoḥā viśvācarṣaṇir", "right": "abhi yōnim āyohatam |"},
            {"type": "verse", "num": "2c.", "left": "drūṇā sadhāstham āsadat ||", "right": ""},
            {"type": "verse", "num": "3a.", "left": "varivodhātamo bhava", "right": "māṃhiṣṭho vṛtrahāntamaḥ |"},
            {"type": "verse", "num": "3c.", "left": "pārṣi rādho maghōnām ||", "right": ""},
            {"type": "verse", "num": "4a.", "left": "abhi arṣa mahānām", "right": "devānām vītīm āndhasā |"},
            {"type": "verse", "num": "4c.", "left": "abhi vājam utā śrāvāḥ ||", "right": ""},
            {"type": "verse", "num": "5a.", "left": "tuvām āchā carāmasi", "right": "tād id ārtham divē-dive |"},
            {"type": "verse", "num": "5c.", "left": "indo tuvē na āśāsāḥ ||", "right": ""},
            {"type": "verse", "num": "6a.", "left": "punāti te parisrūtam", "right": "sōmam sūryasya duhitā |"},
            {"type": "verse", "num": "6c.", "left": "vāreṇa śāśvatā tānā ||", "right": ""},
            {"type": "verse", "num": "7a.", "left": "tām īm āṇvīḥ samaryā ā", "right": "gṛbhṇānti yōṣaṇo dāśa |"},
            {"type": "verse", "num": "7c.", "left": "svāsāraḥ pāriye divī ||", "right": ""},
            {"type": "verse", "num": "8a.", "left": "tām īm hinvanti agrūvo", "right": "dhāmanti bākurām dṛtim |"},
            {"type": "verse", "num": "8c.", "left": "tridhātu vāraṇām mādhu ||", "right": ""},
            {"type": "verse", "num": "9a.", "left": "abhīmām āghniyā utā", "right": "śrīnānti dhenāvāḥ śīsum |"},
            {"type": "verse", "num": "9c.", "left": "sōmam indrāya pātave ||", "right": ""},
            {"type": "verse", "num": "10a.", "left": "asyēd indro mādeṣu ā", "right": "viśvā vṛtrāṇi jighnate |"},
            {"type": "verse", "num": "10c.", "left": "śūro maghā ca maṃhate ||", "right": ""},
            {"type": "blank", "height": "3.5mm"},
            {"type": "h2", "text": "9.2 (714). To Soma Pavamāna from Medhātithi Kāṇva"},
            {"type": "subtitle", "text": "gāyatri"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "verse", "num": "1a.", "left": "pāvasva devavīr āti", "right": "pavitrām soma rāṃhiyā |"},
            {"type": "verse", "num": "1c.", "left": "indram indo vṛṣā viśa ||", "right": ""},
            {"type": "verse", "num": "2a.", "left": "ā vacyasva māhi psāro", "right": "vṛṣendo dyumnāvattamaḥ |"},
            {"type": "verse", "num": "2c.", "left": "ā yōnim dharnasiḥ sadaḥ ||", "right": ""},
            {"type": "verse", "num": "3a.", "left": "ādhukṣata priyām mādhu", "right": "dhārā sutāsya vedhāsāḥ |"},
            {"type": "verse", "num": "3c.", "left": "apō vasiṣṭa sukrātuh ||", "right": ""},
            {"type": "verse", "num": "4a.", "left": "mahāntam tvā mahir ānu", "right": "āpo arṣanti sindhavāḥ |"},
            {"type": "verse", "num": "4c.", "left": "yād gōbhir vāsayiṣyāse ||", "right": ""},
            {"type": "verse", "num": "5a.", "left": "samudrō apsu māṃṛje", "right": "viṣṭambhō dharūṇo divāḥ |"},
            {"type": "verse", "num": "5c.", "left": "sōmaḥ pavitre asmayūḥ ||", "right": ""},
            {"type": "verse", "num": "6a.", "left": "ācikradad vṛṣā hārīr", "right": "mahān mitrō nā darśatāḥ |"},
            {"type": "verse", "num": "6c.", "left": "sām sūriyeṇa rocate ||", "right": ""},
            {"type": "verse", "num": "7a.", "left": "gīras ta inda ōjasā", "right": "marmṛjyānte apasyūvāḥ |"},
            {"type": "verse", "num": "7c.", "left": "yābhir mādāya śumbhase ||", "right": ""},
        ]
    },
    # Page 2: Devanagari
    {
        "page_num": 2,
        "type": "deva",
        "header_left": "",
        "header_center": "ॐ",
        "header_right": "",
        "footer_left": "VOL. V.",
        "footer_right": "B",
        "items": [
            {"type": "center_title", "text": "॥ श्रीगणेशाय नमः ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "mangal", "text": "यस्य निःश्वसितं वेदा यो वेदेभ्योऽखिलं जगत् ।"},
            {"type": "mangal", "text": "निर्ममे तमहं वन्दे विद्यातीर्थमहेश्वरं ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "bhashya", "text": "अथ नवमं मंडलं । तत्र सप्तानुवाकाः । तत्र प्रथमेऽनुवाके चतुर्विंशति-"},
            {"type": "bhashya", "text": "संख्याकानि सूक्तानि । तत्र स्वादिष्टयेति दशर्चे प्रथमं सूक्तं । अत्रानुक्रम्यते ।"},
            {"type": "bhashya", "text": "स्वादिष्टया दश मधुच्छंदा इति । वैश्वामित्रो मधुच्छंदा ऋषिः । प्राग्वत्सप्री-"},
            {"type": "bhashya", "text": "यपरिभाषया गायत्री छंदः । नवमं मंडलं पावमानं सौम्यमिति वचनात् पव-"},
            {"type": "bhashya", "text": "मानगुणविशिष्टः सोमो देवता ॥ यावत्स्तोत्रेऽर्बुदसूक्तस्य प्रागुत्तमाया इदमादिकं"},
            {"type": "bhashya", "text": "सर्वं पावमानं विकल्पेनावपनीयं । सूचितं च । प्रेतं वदन्त्यर्बुदं प्रागुत्तमाया"},
            {"type": "bhashya", "text": "आ व ऋक्षसे प्र वो वाग्वाण इति सूक्तयोरंतरोपरिष्टात्पुरस्ताद्वा पावमानीरोप"},
            {"type": "bhashya", "text": "यथार्थमावापग्रहणात् । आ० ५.१२. इति ॥ उपाकर्मणि मंडलादिग्रहणे आद्यं ।"},
            {"type": "bhashya", "text": "सूक्तं पूर्वमेवोदाहृतं ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ तत्र प्रथमा ॥"},
            {"type": "samhita", "text": "स्वादिष्टया मदिष्टया पवस्व सोम धारया । इंद्राय पातवे सुतः ॥१॥"},
            {"type": "padapatha", "text": "स्वादिष्टया । मदिष्टया । पवस्व । सोम । धारया । इंद्राय । पातवे । सुतः ॥१॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे सोम इंद्राय पातवे पातुं सुतोऽभिषुतस्त्वं स्वादिष्टया स्वादुतमया मदिष्ट-"},
            {"type": "bhashya", "text": "यातिशयेन मादयित्र्या धारया पवस्व । क्षर ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ द्वितीया ॥"},
            {"type": "samhita", "text": "रक्षोहा विश्वचर्षणिरभि योनिमयोहृतं । दुर्गा सधस्थमासंदत् ॥२॥"},
            {"type": "padapatha", "text": "रक्षःऽहा । विश्वऽचर्षणिः । अभि । योनिं । अयःऽहृतं । दुर्गा । सधऽस्थं । आ । असदत् ॥२॥"},
        ]
    },
    # Page 3: Devanagari
    {
        "page_num": 3,
        "type": "deva",
        "header_left": "२",
        "header_center": "॥ ऋग्वेदः ॥",
        "header_right": "[अ० ६. अ० ७. व० १६.]",
        "footer_left": "",
        "footer_right": "",
        "items": [
            {"type": "bhashya", "text": "रक्षोहा रक्षसां हन्ता विश्वचर्षणिविश्वस्य द्रष्टा सोमोऽयोहतं हिरण्येन हतं ।"},
            {"type": "bhashya", "text": "तथा च ब्राह्मणं । हिरण्यपाणिरभिषुणोतीति । द्रुणा द्रोणकलशेनाधिषवणफल-"},
            {"type": "bhashya", "text": "काभ्यां वा सधस्थं सहस्थानं योनिमभिषवस्थानमभ्यासदत् । अभ्यासीदति ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ तृतीया ॥"},
            {"type": "samhita", "text": "वरिवोधातमो भव मंहिष्ठो वृत्रहंतमः । पर्षि राधो मघोनां ॥३॥"},
            {"type": "padapatha", "text": "वरिवःऽधातमः । भव । मंहिष्ठः । वृत्रहन्ऽतमः । पर्षि । राधः । मघोनां ॥३॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे सोम त्वं वरिवोधातमोऽतिशयेन धनानां दाता भव ॥ वेदो वरिव इति"},
            {"type": "bhashya", "text": "धननामसु पाठात् ॥ मंहिष्ठो दातृतमश्च भव । सर्वदातृतमोच्यत इत्यपुन-"},
            {"type": "bhashya", "text": "रुक्तिः । वृत्रहंतमोऽतिशयेन शत्रूणां हन्ता भव । किंच मघोनां धनवतां शत्रूणां"},
            {"type": "bhashya", "text": "राधो धनं च पर्षि । अस्मभ्यं प्रयच्छ ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ चतुर्थी ॥"},
            {"type": "samhita", "text": "अभ्यर्ष महानां देवानां वीतिमंधसा । अभि वाजमुत श्रवः ॥४॥"},
            {"type": "padapatha", "text": "अभि । अर्ष । महानां । देवानां । वीतिं । अंधसा । अभि । वाजं । उत । श्रवः ॥४॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे सोम त्वं महानां महतां देवानां वीतिं यज्ञमंधसा धानाद्यन्नेन सहाभ्यर्ष ।"},
            {"type": "bhashya", "text": "अभिगच्छ । उतापि चाभिगच्छस्त्वं वाजं बलं श्रवोऽन्नं चाभिगमयास्मानित्यर्थः ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ पंचमी ॥"},
            {"type": "samhita", "text": "त्वामच्छा चरामसि तदिदर्थं दिवेदिवे । इंदो त्वे न आशसः ॥५॥"},
            {"type": "padapatha", "text": "त्वां । अच्छ । चरामसि । तत् । इत् । अर्थं । दिवेऽदिवे । इंदो इति । त्वे इति । नः ।"},
            {"type": "padapatha", "text": "आऽशसः ॥५॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे इंदो यागेषु क्रियमाणं सोम त्वामच्छा त्वां प्रति चरामसि । वयं चरामः ।"},
            {"type": "bhashya", "text": "दिवेदिवे प्रतिदिनमस्माकं तदित् तदेव तत्परिचरणमेवार्थं कार्यं नान्यत्कार्य-"},
            {"type": "bhashya", "text": "मस्ति । नोऽस्माकमाशंस आशंसनान्यपि त्वय्येव नान्यत्र ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "center_title", "text": "॥ इति षष्ठस्य सप्तमे षोडशो वर्गः ॥"},
        ]
    },
    # Page 4: Devanagari
    {
        "page_num": 4,
        "type": "deva",
        "header_left": "म० ९. अ० १. सू० १.]",
        "header_center": "॥ षष्ठोऽष्टकः ॥",
        "header_right": "३",
        "footer_left": "",
        "footer_right": "",
        "items": [
            {"type": "h3", "text": "॥ अथ षष्ठी ॥"},
            {"type": "samhita", "text": "पुनाति ते परिस्रुतं सोमं सूर्यस्य दुहिता । वारेण शश्वता तना ॥६॥"},
            {"type": "padapatha", "text": "पुनाति । ते । परिऽस्रुतं । सोमं । सूर्यस्य । दुहिता । वारेण । शश्वता । तना ॥६॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे सोम ते तव परिस्रुतं क्षरन्तं सोमं सोमरसं सूर्यस्य दुहिता श्रद्धा देवी"},
            {"type": "bhashya", "text": "वारेण वालेन शश्वता शाश्वतेन तना विस्मृतेन पुनाति ॥ तथा च वाजसनेयिन"},
            {"type": "bhashya", "text": "आमनंति । श्रद्धा वै सूर्यस्य दुहिता श्रद्धा ह्येनं पुनातीति ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ सप्तमी ॥"},
            {"type": "samhita", "text": "तमीमृण्वीः समर्य आ गृभ्णंति योषणो दश । स्वसारः पार्ये दिवि ॥७॥"},
            {"type": "padapatha", "text": "तं । ईं । ऋज्वीः । समर्यॆ । आ । गृभ्णंति । योषणः । दश । स्वसारः । पार्ये । दिवि ॥७॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "समर्ये समनुष्ये यज्ञे पार्ये दिवि सौत्येऽहनि योषितः स्त्रियः स्वसारः स्वयं"},
            {"type": "bhashya", "text": "सरंत्यो दशसंख्याका अङ्गुलयः [ऋज्व्योऽङ्गुलयः । ऋज्व्योऽङ्गुल्य इत्यङ्गुलिनामसु पाठात् ।]"},
            {"type": "bhashya", "text": "तमीं तमेतं सोममागृभ्णंति । आगृह्णंति ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथाष्टमी ॥"},
            {"type": "samhita", "text": "तमीं हिन्वंत्यग्रुवो धमंति बाकुरं दृतिं । त्रिधातु वारणं मधु ॥८॥"},
            {"type": "padapatha", "text": "तं । ईं । हिन्वंति । अग्रुवः । धमंति । बाकुरं । दृतिं । त्रिऽधातु । वारणं । मधु ॥८॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "तमीमेनं सोममग्रुवोऽङ्गुलयो हिन्वंति । अभिषवदेशं प्रति प्रेरयंति । प्रेरयित्वा"},
            {"type": "bhashya", "text": "च बाकुरं भासमानं दृतिं दृतिसदृशामेनं सोमं धमंति । अभिषुन्वंति ।"},
            {"type": "bhashya", "text": "यद्यपि धमतिरभिषवकर्मा न भवति तथाप्यौचित्यादत्राभिषवपरो भविष्यति ।"},
            {"type": "bhashya", "text": "तदेतत्सोमात्मकं मधु वस्तु त्रिधातु त्रिस्थानं । द्रोणकलश आधवनीयः पूतभृ-"},
            {"type": "bhashya", "text": "दिति त्रिधातवः । वारणं शत्रूणां वारकं च भवति ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ नवमी ॥"},
            {"type": "samhita", "text": "अभीमं मध्वा उत श्रीणंति धेनवः शिशुं । सोममिंद्राय पातवे ॥९॥"},
            {"type": "padapatha", "text": "अभि । इमं । अध्वराः । उत । श्रीणंति । धेनवः । शिशुं । सोमं । इंद्राय । पातवे ॥९॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "उतापि चेममेनं शिशुं बालं सोममध्वरा अहंतव्या धेनवो गाव इंद्राय"},
            {"type": "bhashya", "text": "पातवे पातुमभिश्रीणंति । स्वकीयेन पयसा संस्कुर्वंतीत्यर्थः ॥"},
        ]
    },
    # Page 5: Devanagari
    {
        "page_num": 5,
        "type": "deva",
        "header_left": "४",
        "header_center": "॥ ऋग्वेदः ॥",
        "header_right": "[अ० ६. अ० ७. व० १८.]",
        "footer_left": "",
        "footer_right": "",
        "items": [
            {"type": "h3", "text": "॥ अथ दशमी ॥"},
            {"type": "samhita", "text": "अस्येदिंद्रो मदेष्वा विश्वा वृत्राणि जिघ्नते । शूरो मघा च मंहते ॥१०॥"},
            {"type": "padapatha", "text": "अस्य । इत् । इंद्रः । मदेषु । आ । विश्वा । वृत्राणि । जिघ्नते । शूरः । मघा । च । मंहते ॥१०॥"},
            {"type": "blank", "height": "1mm"},
            {"type": "bhashya", "text": "शूरो वीर इंद्रोऽस्येदस्य सोमस्यैव मदेषु विश्वा विश्वानि वृत्राणि शत्रून्"},
            {"type": "bhashya", "text": "आजिघ्नते । आहंति । मघा मघानि धनानि च मंहते । यजमानेभ्यः प्रयच्छति ॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "center_title", "text": "॥ इति षष्ठस्य सप्तमे सप्तदशो वर्गः ॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "पवस्वेति दशर्चं द्वितीयं सूक्तं काण्वस्य मेधातिथेरार्षं गायत्रं पवमानसोम-"},
            {"type": "bhashya", "text": "देवताकं । तथा चानुक्रांतं । पवस्व मेधातिथिरिति । उक्तो विनियोगः ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "h3", "text": "॥ तत्र प्रथमा ॥"},
            {"type": "samhita", "text": "पवस्व देववीरति पवित्रं सोम रंह्या । इंद्रमिंदो वृषा विश ॥१॥"},
            {"type": "padapatha", "text": "पवस्व । देवऽवीः । अति । पवित्रं । सोम । रंह्या । इंद्रं । इंदो इति । वृषा । आ । विश ॥१॥"},
            {"type": "blank", "height": "1mm"},
            {"type": "bhashya", "text": "हे सोम देववीरदेवकामस्त्वं रंह्या वेगेन पवित्रं यथा भवति तथाति पवस्व ।"},
            {"type": "bhashya", "text": "अतिक्षर । किंच हे इंदो वृषा सेचकस्त्वमिंद्रमाविश । प्रविश ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "h3", "text": "॥ अथ द्वितीया ॥"},
            {"type": "samhita", "text": "आ वच्यस्व महि प्सारो वृषेंदो द्युम्नवत्तमः । आ योनिं धर्णसिः सदः ॥२॥"},
            {"type": "padapatha", "text": "आ । वच्यस्व । महि । प्सारः । वृषा । इंदो इति । द्युम्नवत्ऽतमः । आ । योनिं ।"},
            {"type": "padapatha", "text": "धर्णसिः । सदः ॥२॥"},
            {"type": "blank", "height": "1mm"},
            {"type": "bhashya", "text": "हे इंदो सोम महि महान्वृषा कामानां वर्षको द्युम्नवत्तमो यशस्वितमो"},
            {"type": "bhashya", "text": "धर्णसिर्धर्ता त्वं प्सरः पानीयमन्नं आवच्यस्व । अस्मान्प्रत्यागमय । योनिं"},
            {"type": "bhashya", "text": "स्वकीयं स्थानमासदः । आसीद च ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "h3", "text": "॥ अथ तृतीया ॥"},
            {"type": "samhita", "text": "अधुक्षत प्रियं मधु धारा सुतस्य वेधसः । अपो वसिष्ट सुक्रतुः ॥३॥"},
            {"type": "padapatha", "text": "अधुक्षत । प्रियं । मधु । धारा । सुतस्य । वेधसः । अपः । वसिष्ट । सुऽक्रतुः ॥३॥"},
            {"type": "blank", "height": "1mm"},
            {"type": "bhashya", "text": "सुतस्याभिषुतस्य वेधसोऽभिलषितस्य विधातुर्यस्य सोमस्य धारा प्रियं"},
            {"type": "bhashya", "text": "प्रीतिकरं मधुमन्मधुधुक्षत दुग्धे स सुक्रतुः सुकर्मा सोमोऽपो वसतीवरीर्वसिष्ट ।"},
            {"type": "bhashya", "text": "आच्छादयति ॥"},
        ]
    },
    # Page 6: Devanagari
    {
        "page_num": 6,
        "type": "deva",
        "header_left": "म० ९. अ० १. सू० २.]",
        "header_center": "॥ षष्ठोऽष्टकः ॥",
        "header_right": "५",
        "footer_left": "VOL. V.",
        "footer_right": "C",
        "items": [
            {"type": "h3", "text": "॥ अथ चतुर्थी ॥"},
            {"type": "samhita", "text": "महांतं त्वा महीरन्वापो अर्षंति सिंधवः । यद्गोभिर्वासयिष्यसे ॥४॥"},
            {"type": "padapatha", "text": "महांतं । त्वा । महीः । अनु । आपः । अर्षंति । सिंधवः । यत् । गोभिः । वासयिष्यसे ॥४॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे सोम त्वं यद्यदा यज्ञे गोभिर्गोविकारैः पयोभिर्वासयिष्यस आच्छादयिष्यसे"},
            {"type": "bhashya", "text": "तत्तदा महांतं त्वामन्व प्रति सिंधवः स्यंदमाना महीर्महत्य आपोऽर्षंति ।"},
            {"type": "bhashya", "text": "गच्छंति ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ पंचमी ॥"},
            {"type": "samhita", "text": "समुद्रो अप्सु मामृजे विष्टंभो धरुणो दिवः । सोमः पवित्रे अस्मयुः ॥५॥"},
            {"type": "padapatha", "text": "समुद्रः । अप्सु । ममृजे । विष्टंभः । धरुणः । दिवः । सोमः । पवित्रे । अस्मऽयुः ॥५॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "समुद्रः समुद्रवंत्यस्माद्रसा इति समुद्रः । विष्टंभो दिवः स्वर्गस्य धरुणो"},
            {"type": "bhashya", "text": "धारकश्चास्मयुरस्मत्कामः सोमोऽप्सूदकेषु ममृजे । मृज्यते । पवित्रेऽभिषिच्यत"},
            {"type": "bhashya", "text": "इत्यर्थः ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "center_title", "text": "॥ इति षष्ठस्य सप्तमेऽष्टादशो वर्गः ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "h3", "text": "॥ अथ षष्ठी ॥"},
            {"type": "samhita", "text": "अचिक्रदद्वृषा हरिर्महान्मित्रो न दर्शतः । सं सूर्येण रोचते ॥६॥"},
            {"type": "padapatha", "text": "अचिक्रदत् । वृषा । हरिः । महान् । मित्रः । न । दर्शतः । सं । सूर्येण । रोचते ॥६॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "वृषा कामानां वर्षको हरिर्हरितवर्णो महान् सर्वोत्तमो मित्रो न यथा सखा"},
            {"type": "bhashya", "text": "तद्वद्दर्शतो दर्शनीयो योऽयं सोमोऽचिक्रदत् शब्दं करोति सोऽयं सोमः सूर्येण"},
            {"type": "bhashya", "text": "सह रोचते । दिवि प्रकाशते ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ सप्तमी ॥"},
            {"type": "samhita", "text": "गिरस्त इंद ओजसा मर्मृज्यंते अपस्युवः । याभिर्मदाय शुंभसे ॥७॥"},
            {"type": "padapatha", "text": "गिरः । ते । इंदो इति । ओजसा । मर्मृज्यंते । अपस्युवः । याभिः । मदाय । शुंभसे ॥७॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे इंदो ते तवौजसा बलेनापस्युवः कर्मेच्छासंबंधिन्यस्ता गिरः स्तुतयो"},
            {"type": "bhashya", "text": "मर्मृज्यंते शोध्यंते याभिर्गीर्भिस्त्वं मदाय क्षरञ्छुंभसेऽलंक्रियसे ॥"},
        ]
    },
    # Page 7: Devanagari
    {
        "page_num": 7,
        "type": "deva",
        "header_left": "६",
        "header_center": "॥ ऋग्वेदः ॥",
        "header_right": "[अ० ६. अ० ७. व० २०.]",
        "footer_left": "",
        "footer_right": "",
        "items": [
            {"type": "h3", "text": "॥ अथाष्टमी ॥"},
            {"type": "samhita", "text": "तं त्वा मदाय घृष्वय उ लोककृत्नुमीमहे । तव प्रशस्तयो महीः ॥८॥"},
            {"type": "padapatha", "text": "तं । त्वा । मदाय । घृष्वये । उं इति । लोकऽकृत्नुं । ईमहे । तव । प्रऽशस्तयः । महीः ॥८॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे सोम यस्य ते तव प्रशस्तयः प्रशंसा महीर्महत्यो घृष्वय उ त्वत्प्रसादाच्छ-"},
            {"type": "bhashya", "text": "त्रूणां घर्षणशीलाय यजमानायैव लोककृत्नुमुत्तमस्य लोकस्य कर्तारं तं त्वां"},
            {"type": "bhashya", "text": "सोमं मदायेमहे । वयं याचामहे ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ नवमी ॥"},
            {"type": "samhita", "text": "अस्मभ्यमिंदविंद्रयुर्मध्वः पवस्व धारया । पर्जन्यो वृष्टिमां इव ॥९॥"},
            {"type": "padapatha", "text": "अस्मभ्यं । इंदो इति । इंद्रऽयुः । मध्वः । पवस्व । धारया । पर्जन्यः । वृष्टिऽमान् इव ॥९॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे इंदो सोम इंद्रयुंरिंद्रकामस्त्वं मध्वो मदकरस्यामृतस्य धारया पर्जन्यो वृष्टि-"},
            {"type": "bhashya", "text": "मानिव यथा वर्षन्पर्जन्यो मेघस्तथास्मभ्यं मेधातिथिभ्यः पवस्व । क्षर ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ अथ दशमी ॥"},
            {"type": "samhita", "text": "गोषा इंदो नृषा अस्यश्वसा वाजसा उत । आत्मा यज्ञस्य पूर्व्यः ॥१०॥"},
            {"type": "padapatha", "text": "गोऽसाः । इंदो इति । नृऽसाः । असि । अश्वऽसाः । वाजऽसाः । उत । आत्मा ।"},
            {"type": "padapatha", "text": "यज्ञस्य । पूर्व्यः ॥१०॥"},
            {"type": "blank", "height": "1.5mm"},
            {"type": "bhashya", "text": "हे इंदो यज्ञस्य पूर्व्यः प्रत्न आत्मात्मभूतस्त्वं गोषा अस्मभ्यं गवां दातासि ।"},
            {"type": "bhashya", "text": "भवसि । नृषाः पुत्राणां दाता चासि । अश्वसा अश्वानां दाता चासि । उतापि"},
            {"type": "bhashya", "text": "च वाजसा अन्नानां दाता चासि ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "center_title", "text": "॥ इति षष्ठस्य सप्तम एकोनविंशो वर्गः ॥"},
            {"type": "blank", "height": "2mm"},
            {"type": "bhashya", "text": "एष देव इति दशर्चं तृतीयं सूक्तमाजिगर्तैः शुनःशेपस्यार्षं गायत्रं पवमान-"},
            {"type": "bhashya", "text": "सोमदेवतार्क । अनुक्रांतं च । एष शुनःशेप इति । उक्तो विनियोगः ॥"},
            {"type": "blank", "height": "2.5mm"},
            {"type": "h3", "text": "॥ तत्र प्रथमा ॥"},
            {"type": "samhita", "text": "एष देवो अमर्त्यः पर्णवीरिव दीयति । अभि द्रोणान्यासदं ॥१॥"},
            {"type": "padapatha", "text": "एषः । देवः । अमर्त्यः । पर्णवीःऽइव । दीयति । अभि । द्रोणानि । आऽसदत् ॥१॥"},
        ]
    }
]


def generate_html_part1() -> str:
    html = []
    html.append("""<!DOCTYPE html>
<html lang="sa">
<head>
<meta charset="utf-8">
<title>Rig Veda - Maṇḍala 9 (Pages 1-7 Typeset)</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Noto+Serif+Devanagari:wght@400;500;600;700&display=swap');

@page {
  size: A4 portrait;
  margin: 10mm 15mm 10mm 15mm;
  @bottom-center {
    content: counter(page);
    font-family: 'EB Garamond', serif;
    font-size: 10pt;
    color: #555;
  }
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'EB Garamond', 'Noto Serif Devanagari', 'Devanagari MT', serif;
  font-size: 11pt;
  line-height: 1.44;
  color: #1a1a1a;
  background-color: #faf9f6;
  -webkit-font-smoothing: antialiased;
}

.page {
  background: #ffffff;
  width: 210mm;
  min-height: 297mm;
  margin: 10mm auto;
  padding: 12mm 16mm 14mm 16mm;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  page-break-after: always;
  break-after: page;
  position: relative;
  display: flex;
  flex-direction: column;
}

@media print {
  body {
    background: transparent;
  }
  .page {
    margin: 0;
    padding: 0;
    width: 100%;
    min-height: auto;
    box-shadow: none;
    page-break-after: always;
    break-after: page;
  }
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 0.6pt solid #aaa;
  padding-bottom: 1.8mm;
  margin-bottom: 3.5mm;
  font-size: 10pt;
  color: #2b2b2b;
  letter-spacing: 0.4px;
}
.header-center {
  flex-grow: 1;
  text-align: center;
  font-weight: 600;
}
.header-left {
  text-align: left;
  min-width: 25mm;
}
.header-right {
  text-align: right;
  min-width: 25mm;
}

.footer {
  margin-top: 3mm;
  display: flex;
  justify-content: space-between;
  border-top: 0.5pt solid #ddd;
  padding-top: 1.8mm;
  font-size: 9.5pt;
  color: #666;
}

.content {
  flex-grow: 1;
}

/* ========================================================
   Page 1: Latin IAST Transliteration (Centered Two-Column Hemistichs)
   ======================================================== */
.latin-page {
  font-family: 'EB Garamond', serif;
}

.latin-page .h2 {
  font-size: 13.5pt;
  font-weight: 700;
  text-align: center;
  margin: 2.5mm 0 1.2mm 0;
  color: #12284c;
}

.latin-page .subtitle {
  font-size: 11pt;
  font-style: italic;
  text-align: center;
  margin: 0 0 2mm 0;
  color: #444;
}

.verses-container {
  max-width: 155mm;
  margin: 0 auto;
}

.verse-row {
  display: flex;
  font-size: 10pt;
  line-height: 1.34;
  margin: 0;
}
.verse-num {
  width: 10mm;
  font-weight: 600;
  color: #555;
}
.verse-left {
  width: 68mm;
}
.verse-right {
  flex-grow: 1;
}

/* ========================================================
   Devanagari Pages 2 to 7: Traditional Sanskrit Layout
   - Larger font size (13.2pt - 16.2pt) to fill the page
   - ALL blocks centered (verses, padapatha, commentary)
   - Clean spacing to avoid overflow
   ======================================================== */
.deva-page {
  font-family: 'Noto Serif Devanagari', 'Devanagari MT', serif;
}

.deva-page .header {
  font-size: 12.5pt;
  font-weight: 600;
  border-bottom: 0.8pt solid #777;
  padding-bottom: 1.5mm;
  margin-bottom: 3mm;
  color: #1a1a1a;
}

.deva-page .footer {
  font-size: 11pt;
  font-weight: 600;
  color: #444;
  margin-top: 2mm;
}

/* Centered section headings: ॥ तत्र प्रथमा ॥ */
.deva-page .h3 {
  font-size: 14.8pt;
  font-weight: 700;
  text-align: center;
  margin: 1.8mm auto 0.8mm auto;
  color: #12284c;
  letter-spacing: 0.5px;
}

/* Centered Mangalashloka / titles: ॥ श्रीगणेशाय नमः ॥ etc. */
.deva-page .center-title {
  font-size: 15.5pt;
  font-weight: 700;
  text-align: center;
  margin: 1.8mm auto 1mm auto;
  color: #0b1a30;
}

.deva-page .mangal {
  font-size: 14.8pt;
  font-weight: 600;
  text-align: center;
  margin: 0.8mm auto;
  color: #1a1a1a;
  line-height: 1.4;
}

/* Samhita Verses: Centered, Bold, Large Font (16.2pt) */
.deva-page .samhita {
  font-size: 16.2pt;
  font-weight: 700;
  text-align: center;
  color: #08162b;
  margin: 1.8mm auto 0.8mm auto;
  line-height: 1.38;
  letter-spacing: 0.3px;
  display: block;
}

/* Padapatha: Centered, Medium Weight (13.6pt) */
.deva-page .padapatha {
  font-size: 13.6pt;
  font-weight: 500;
  text-align: center;
  color: #2c3440;
  margin: 0.6mm auto 1.6mm auto;
  line-height: 1.36;
  letter-spacing: 0.35px;
  display: block;
}

/* Bhashya (Sāyaṇa Commentary) and other text blocks:
   Centered text, 13.2pt font, perfectly filling the page */
.deva-page .bhashya {
  font-size: 13.2pt;
  line-height: 1.42;
  color: #1a1a1a;
  text-align: center;
  margin: 0.5mm auto;
  padding: 0;
  max-width: 98%;
}
</style>
</head>
<body>
""")

    for p in PAGES_DATA:
        is_deva = p["type"] == "deva"
        page_cls = "page deva-page" if is_deva else "page latin-page"
        html.append(f'<div class="{page_cls}" id="page-{p["page_num"]}">')
        html.append('  <div class="header">')
        html.append(f'    <div class="header-left">{p.get("header_left") or ""}</div>')
        html.append(f'    <div class="header-center">{p.get("header_center") or ""}</div>')
        html.append(f'    <div class="header-right">{p.get("header_right") or ""}</div>')
        html.append('  </div>')
        
        html.append('  <div class="content">')
        if not is_deva:
            html.append('    <div class="verses-container">')

        for item in p["items"]:
            itype = item["type"]
            if itype == "blank":
                h = item.get("height", "2mm")
                html.append(f'    <div style="height: {h};"></div>')
            elif itype == "h2":
                html.append(f'    <div class="h2">{item["text"]}</div>')
            elif itype == "h3":
                html.append(f'    <div class="h3">{item["text"]}</div>')
            elif itype == "subtitle":
                html.append(f'    <div class="subtitle">{item["text"]}</div>')
            elif itype == "center_title":
                html.append(f'    <div class="center-title">{item["text"]}</div>')
            elif itype == "mangal":
                html.append(f'    <div class="mangal">{item["text"]}</div>')
            elif itype == "samhita":
                html.append(f'    <div class="samhita">{item["text"]}</div>')
            elif itype == "padapatha":
                html.append(f'    <div class="padapatha">{item["text"]}</div>')
            elif itype == "bhashya":
                html.append(f'    <div class="bhashya">{item["text"]}</div>')
            elif itype == "verse":
                left = item.get("left", "")
                right = item.get("right", "")
                num = item.get("num", "")
                html.append(f'    <div class="verse-row"><span class="verse-num">{num}</span><span class="verse-left">{left}</span><span class="verse-right">{right}</span></div>')

        if not is_deva:
            html.append('    </div>')
        html.append('  </div>')
        
        # footer
        f_left = p.get("footer_left") or ""
        f_center = p.get("footer_center") or ""
        f_right = p.get("footer_right") or ""
        if f_left or f_center or f_right:
            html.append('  <div class="footer">')
            html.append(f'    <div>{f_left}</div>')
            html.append(f'    <div>{f_center}</div>')
            html.append(f'    <div>{f_right}</div>')
            html.append('  </div>')
        
        html.append('</div>')

    html.append("""</body>
</html>""")
    return "\n".join(html)


def main():
    part1_html = OUTPUT_DIR / "RV_9.1_part1_pages1_7.html"
    part1_pdf = PDF_DIR / "RV_9.1_part1_pages1_7.pdf"
    final_pdf = PDF_DIR / "RV_9.1_clean_layout.pdf"

    print("1) Generating HTML for Pages 1-7...")
    html_content = generate_html_part1()
    part1_html.write_text(html_content, encoding="utf-8")
    print(f"   -> Wrote: {part1_html}")

    print("2) Compiling Pages 1-7 via WeasyPrint...")
    cmd_weasy = ["/opt/homebrew/bin/weasyprint", str(part1_html), str(part1_pdf)]
    res = subprocess.run(cmd_weasy, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Weasyprint error:\n{res.stderr}")
        raise SystemExit(res.returncode)
    print(f"   -> Wrote Pages 1-7 PDF: {part1_pdf}")

    # Transfer part1 PDF to alex.local and merge with original pages 8-11 using qpdf
    print("3) Syncing to alex.local and merging with original pages 8-11...")
    scp_cmd = f"scp {part1_pdf} marco@alex.local:/data/output/pdf/RV_9.1_part1_pages1_7.pdf"
    subprocess.run(scp_cmd, shell=True, check=True)

    remote_merge = (
        'ssh marco@alex.local "'
        'docker exec alexandria_worker qpdf --warning-exit-0 --empty '
        '--pages /data/output/pdf/RV_9.1_part1_pages1_7.pdf 1-7 /data/input/RV_9.1.pdf 8-11 '
        '-- /data/output/pdf/RV_9.1_clean_layout.pdf && '
        'docker exec alexandria_worker pdfinfo /data/output/pdf/RV_9.1_clean_layout.pdf"'
    )
    res_merge = subprocess.run(remote_merge, shell=True, capture_output=True, text=True)
    print(res_merge.stdout)
    if res_merge.returncode != 0:
        print(f"Merge error: {res_merge.stderr}")
        raise SystemExit(res_merge.returncode)

    # Fetch merged PDF back to local
    fetch_cmd = f"scp marco@alex.local:/data/output/pdf/RV_9.1_clean_layout.pdf {final_pdf}"
    subprocess.run(fetch_cmd, shell=True, check=True)
    print(f"   -> Final merged PDF ready at: {final_pdf} ({final_pdf.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
