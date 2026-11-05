// AlexandriaSandwich — templates/interlinear_edition.typ
// Standard-Layout für zeilengetreue, interlineare und bilinguale wissenschaftliche Editionen
// (Birchville Scholarly Synthesis Standard)

/// Zeilenweises Sprach- oder Umschrift-Paar mit kontrollierter vertikaler Abstandshierarchie.
/// Stellt sicher, dass der Intra-Paarabstand (oberer zu unterem Text) kleiner ist als der Inter-Paarabstand.
#let interlinear_pair(
  top_text,
  bottom_text,
  top_font: "STIX Two Text",
  bottom_font: "STIX Two Text",
  top_size: 9.6pt,
  bottom_size: 8.0pt,
  top_weight: "medium",
  bottom_style: "italic",
  top_fill: luma(20),
  bottom_fill: rgb("#374151"),
  intra_spacing: 2.6pt,
  inter_spacing: 7.2pt,
) = block(
  spacing: inter_spacing,
  breakable: false
)[
  #stack(spacing: intra_spacing)[
    #text(font: top_font, size: top_size, weight: top_weight, fill: top_fill)[#top_text]
  ][
    #text(font: bottom_font, size: bottom_size, style: bottom_style, fill: bottom_fill)[#bottom_text]
  ]
]

/// Zeilenweises Fußnoten-Paar für textkritische Apparate mit feiner Schriftabstufung.
#let interlinear_footnote(
  top_text,
  bottom_text,
  top_font: "STIX Two Text",
  bottom_font: "STIX Two Text",
  top_size: 7.5pt,
  bottom_size: 6.8pt,
  top_weight: "medium",
  bottom_style: "italic",
  top_fill: luma(30),
  bottom_fill: rgb("#4b5563"),
  intra_spacing: 2.2pt,
  inter_spacing: 6.2pt,
) = block(
  spacing: inter_spacing,
  breakable: false
)[
  #stack(spacing: intra_spacing)[
    #text(font: top_font, size: top_size, weight: top_weight, fill: top_fill)[#top_text]
  ][
    #text(font: bottom_font, size: bottom_size, style: bottom_style, fill: bottom_fill)[#bottom_text]
  ]
]

/// Fußnotenblock-Separator mit Verankerung am Seitenfuß (#v(1fr, weak: true)).
#let footnote_separator(rule_length: 30%, rule_stroke: 0.5pt + luma(100), top_spacing: 2pt, bottom_spacing: 2.5pt) = [
  #v(1fr, weak: true)
  #v(top_spacing)
  #line(length: rule_length, stroke: rule_stroke)
  #v(bottom_spacing)
]

/// Birchville Standard-Titelblatt für wissenschaftliche Textausgaben
#let birchville_title_page(
  series_ind: "kaśmīra-saṃskṛta-granthāvalī — granthāṅkaḥ 17",
  series_lat: "Kashmir Series of Texts and Studies · No. XVII",
  author_ind: "śrīmadabhinavaguptācāryaviracitaḥ",
  author_lat: "Von Śrīmad Abhinavagupta",
  title_main: "TANTRASĀRAḤ",
  subtitle_ind: "tṛtīyam āhnikam · atha śāmbhavopāyaḥ",
  subtitle_lat: "Drittes Kapitel: Das Mittel Śivas (Śāmbhavopāya)",
  edition_badge: "IAST-NEUSATZ MIT ZEILENWEISER DEUTSCHER ÜBERSETZUNG",
  edition_desc: "Zeilen- und seitentreue wissenschaftliche Studienausgabe",
  editor_label: "saṃśodhakaḥ",
  editor_name: "Mahāmahopādhyāya Paṇḍita Mukundarāma Śāstrī",
  imprint_original: "mūlamudraṇam : Nirṇaya Sāgara Press, Bombay, 1918",
  imprint_standard: "Birchville Scholarly Synthesis Standard",
  font: "STIX Two Text"
) = {
  set page(paper: "a5", margin: (inside: 1.8cm, outside: 1.8cm, top: 2.0cm, bottom: 1.6cm), header: none)

  align(center)[
    #stack(spacing: 4pt)[
      #text(font: font, size: 10.5pt, weight: "medium", tracking: 0.04em)[#series_ind]
    ][
      #text(font: font, size: 8.5pt, fill: rgb("#6b7280"))[#series_lat]
    ]

    #v(1.4cm)

    #stack(spacing: 3pt)[
      #text(font: font, size: 13pt, style: "italic", fill: rgb("#374151"))[#author_ind]
    ][
      #text(font: font, size: 10pt, fill: rgb("#6b7280"))[#author_lat]
    ]

    #v(0.5cm)

    #text(font: font, size: 27pt, weight: "bold", tracking: 0.03em)[#title_main]

    #v(0.5cm)

    #stack(spacing: 3pt)[
      #text(font: font, size: 15pt, weight: "bold", fill: rgb("#374151"))[#subtitle_ind]
    ][
      #text(font: font, size: 12pt, style: "italic", fill: rgb("#4b5563"))[#subtitle_lat]
    ]

    #v(0.8cm)

    #block(stroke: 0.5pt + rgb("#9ca3af"), inset: (x: 14pt, y: 6pt), radius: 3pt)[
      #stack(spacing: 2.5pt)[
        #text(font: font, size: 8.8pt, weight: "bold", tracking: 0.05em, fill: rgb("#1f2937"))[#edition_badge]
      ][
        #text(font: font, size: 7.8pt, style: "italic", fill: rgb("#6b7280"))[#edition_desc]
      ]
    ]

    #v(1.0cm)

    #line(length: 22%, stroke: 0.5pt + rgb("#cbd5e1"))
    #v(0.35cm)

    #stack(spacing: 2.5pt)[
      #text(font: font, size: 9pt, style: "italic", fill: rgb("#6b7280"))[#editor_label]
    ][
      #text(font: font, size: 11pt, weight: "bold", fill: rgb("#1f2937"))[#editor_name]
    ]

    #v(1fr)

    #stack(spacing: 3pt)[
      #text(font: font, size: 8.5pt, fill: rgb("#6b7280"))[#imprint_original]
    ][
      #text(font: font, size: 8.5pt, fill: rgb("#9ca3af"))[#imprint_standard]
    ]
  ]

  pagebreak()
}
