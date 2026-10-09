#set page(
  paper: "iso-b5",
  columns: 2,
  margin: (top: 2.2cm, bottom: 2.2cm, inside: 2.5cm, outside: 2cm),
  header: context {
    let p = counter(page).get().first()
    let headings = query(selector(heading).before(here()))
    let current_h = if headings.len() > 0 { headings.last().body } else { [Dhātu-Pāṭha] }
    if calc.even(p) [
      #text(8.5pt, weight: "bold")[#p]
      #h(1fr)
      #text(8pt, font: ("Linux Libertine O", "Noto Serif Devanagari"), style: "italic")[Dhātu-Pāṭha — Kritische Neuausgabe]
    ] else [
      #text(8pt, font: ("Noto Serif Devanagari", "Linux Libertine O"), style: "italic")[#current_h]
      #h(1fr)
      #text(8.5pt, weight: "bold")[#p]
    ]
  }
)

#set columns(gutter: 20pt)
#set text(
  font: ("Noto Serif Devanagari", "Linux Libertine O"),
  size: 9.5pt,
  lang: "sa"
)
#set par(justify: true, leading: 0.55em)

#let entry(root, meaning, page_ref: none) = [
  #block(width: 100%, breakable: false, inset: (y: 1.5pt))[
    #text(weight: "bold")[#root]
    #h(0.4em)
    #meaning
    #if page_ref != none [
      #h(1fr)
      #text(size: 7pt, fill: luma(120))[[S. #page_ref]]
    ]
  ]
]

#heading(level: 1)[अदादिगणः]
#v(0.3em)
#text(8.5pt, style: "italic")[अथ चत्वारः परस्मैभाषाः—]
#v(0.2em)

#entry("विद", "ज्ञाने ।", page_ref: "73")
#entry("अस", "भुवि ।", page_ref: "73")
#entry("मृजूष", "शुद्धौ ।", page_ref: "73")
#entry("रुदिर", "अश्रुविमोचने ।", page_ref: "73")

#v(0.3em)
#text(8.5pt, style: "italic")[अथैकः आत्मनेभाषः—]
#v(0.2em)
#entry("जिष्णु", "शये ।", page_ref: "73")

#v(0.3em)
#text(8.5pt, style: "italic")[अथ सप्त परस्मैभाषाः—]
#v(0.2em)
#entry("श्वस", "प्राणने ।", page_ref: "73")
#entry("अन", "च ।", page_ref: "73")
#entry("जक्ष", "भक्षहसनयोः ।", page_ref: "73")
#entry("जागृ", "निद्राक्षये ।", page_ref: "73")
#entry("दरिद्रा", "दुर्गतौ ।", page_ref: "73")
#entry("चकासु", "दीप्तौ ।", page_ref: "73")
#entry("शासु", "अनुशिष्टौ ।", page_ref: "73")

#v(0.3em)
#text(8.5pt, style: "italic")[अथ द्वावात्मनेभाषौ—]
#v(0.2em)
#entry("दीधीङ्", "दीप्तिदेवनयोः ।", page_ref: "73")
#entry("वेवीङ्", "वेतिना तुल्ये ।", page_ref: "73")

#v(0.3em)
#text(8.5pt, style: "italic")[अथ त्रयः परस्मैभाषाः—]
#v(0.2em)
#entry("षस, सस्ति", "स्वप्ने ।", page_ref: "73")
#entry("वश", "कान्तौ ।", page_ref: "73")
#entry("हुङ्", "अपनयने ।", page_ref: "73")

#v(0.8em)
#heading(level: 1)[भ्वादिगणः (Auswahl S. 27)]
#v(0.3em)
#entry("ह्लादी", "सुखे च ।", page_ref: "27")
#entry("स्वाद", "आस्वादने ।", page_ref: "27")
#entry("पर्द", "कुत्सिते शब्दे ।", page_ref: "27")
#entry("यती", "प्रयत्ने ।", page_ref: "27")
#entry("युत्, जुत्", "भासने ।", page_ref: "27")
#entry("विध्, वेध्", "याचने ।", page_ref: "27")
#entry("श्रथि", "शैथिल्ये ।", page_ref: "27")
#entry("प्रथि", "कौटिल्ये ।", page_ref: "27")
#entry("कथ", "श्लाघायाम् ।", page_ref: "27")

#v(0.3em)
#text(8.5pt, style: "italic")[अथातादयः परस्मैभाषाः—]
#v(0.2em)
#entry("अत", "सातत्यगमने ।", page_ref: "27")
#entry("चिती", "सञ्ज्ञाने ।", page_ref: "27")
#entry("च्युतिर्", "आसेचने ।", page_ref: "27")
#entry("श्च्युतिर्", "क्षरणे ।", page_ref: "27")
#entry("मन्थ", "विलोडने ।", page_ref: "27")
#entry("कुथि, पुथि", "हिंसासंक्लेशनयोः ।", page_ref: "27")
#entry("लुथि, मथि", "गत्याम् ।", page_ref: "27")
#entry("षिधु", "शास्त्रे माङ्गल्ये च ।", page_ref: "27")
#entry("खाद", "भक्षणे ।", page_ref: "27")
#entry("खद", "स्थैर्यं हिंसायां च ।", page_ref: "27")
#entry("बद", "स्थैर्यम् ।", page_ref: "27")
#entry("गद", "व्यक्तायां वाचि ।", page_ref: "27")
#entry("रद", "विलेखने ।", page_ref: "27")
#entry("णद", "अव्यक्ते शब्दे ।", page_ref: "27")
#entry("अर्द", "गतौ याचने च ।", page_ref: "27")
#entry("नर्द, गर्द", "शब्दे ।", page_ref: "27")
#entry("तर्द", "हिंसायाम् ।", page_ref: "27")
#entry("कर्द", "कुत्सिते शब्दे ।", page_ref: "27")
#entry("खर्द", "दन्दशूके ।", page_ref: "27")
#entry("अति, अदि", "बन्धने ।", page_ref: "27")
#entry("इदि", "परमैश्वर्ये ।", page_ref: "27")
#entry("बिदि, भिदि", "अवयवे ।", page_ref: "27")
#entry("गडि", "वदनैकदेशे ।", page_ref: "27")
#entry("णिदि", "कुत्सायाम् ।", page_ref: "27")
#entry("चदि", "समृद्धौ ।", page_ref: "27")
#entry("त्रदि", "चेष्टायाम् ।", page_ref: "27")
#entry("शुन्ध", "शुद्धौ ।", page_ref: "27")
