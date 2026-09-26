// AlexandriaSandwich - Universal Book Typesetting Template
// Pure Typst - No LaTeX dependency

#let book(
  title: "Untitled Book",
  author: "Alexandria Archive",
  date: none,
  paper: "a5",
  lang: "de",
  body
) = {
  // Document metadata
  set document(title: title, author: author)

  // Typography rules
  set text(
    font: ("Linux Libertine", "DejaVu Serif", "Noto Serif", "Times New Roman"),
    size: 10pt,
    lang: lang,
    hyphenate: true
  )

  set par(
    justify: true,
    leading: 0.72em,
    first-line-indent: 1.4em
  )

  // Headings
  show heading: it => {
    set text(font: ("Linux Libertine", "DejaVu Serif", "Noto Serif", "Times New Roman"), weight: "bold")
    if it.level == 1 {
      pagebreak(weak: true)
      v(2cm)
      align(center)[
        #text(size: 16pt)[#it.body]
      ]
      v(1.5cm)
    } else if it.level == 2 {
      v(1.2cm)
      text(size: 12.5pt)[#it.body]
      v(0.6cm)
    } else {
      v(0.8cm)
      text(size: 11pt, style: "italic")[#it.body]
      v(0.4cm)
    }
  }

  // Page setup: Standard scholarly / readable book layout
  set page(
    paper: paper,
    margin: (inside: 2.2cm, outside: 1.8cm, top: 2.2cm, bottom: 2.2cm),
    header: context {
      let page_num = here().page()
      if page_num > 2 {
        let headings = query(heading.where(level: 1).before(here()))
        let chapter_title = if headings.len() > 0 {
          headings.last().body
        } else {
          title
        }

        set text(size: 8.5pt, font: ("Linux Libertine", "DejaVu Serif", "Noto Serif", "Times New Roman"), fill: luma(80))
        if calc.even(page_num) {
          align(left)[#smallcaps(title)]
        } else {
          align(right)[#smallcaps(chapter_title)]
        }
      }
    },
    footer: context {
      let page_num = here().page()
      if page_num > 1 {
        set text(size: 9pt, font: ("Linux Libertine", "DejaVu Serif", "Noto Serif", "Times New Roman"))
        align(center)[#page_num]
      }
    }
  )

  // --- Half-Title / Title Page ---
  align(center + horizon)[
    #v(-4cm)
    #text(size: 22pt, weight: "bold")[#title]
    
    #v(1.5cm)
    #text(size: 13pt, style: "italic")[#author]
    
    #v(4cm)
    #text(size: 8.5pt, fill: luma(120))[
      Digital Vector Edition • AlexandriaSandwich\
      #if date != none [ #date ]
    ]
  ]

  pagebreak()

  // Reset page counter for content
  counter(page).update(1)

  // Body content
  body
}
