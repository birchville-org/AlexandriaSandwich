// AlexandriaSandwich - Universal Book Typesetting Template
// Pure Typst - No LaTeX dependency

#let book_fonts = ("Linux Libertine", "Libertinus Serif", "Noto Serif", "Noto Serif Devanagari", "PT Serif", "Charter", "Times New Roman", "DejaVu Serif")

#let book(
  title: "Untitled Book",
  author: "Alexandria Archive",
  date: none,
  paper: "a5",
  width: none,
  height: none,
  margin: none,
  preserve_pages: false,
  title_page: none,
  lang: "de",
  body
) = {
  // Document metadata
  set document(title: title, author: author)

  // Determine whether to emit upfront title page
  let show_title_page = if title_page != none { title_page } else { not preserve_pages }

  // Typography rules
  set text(
    font: book_fonts,
    size: if preserve_pages { 9.5pt } else { 10pt },
    lang: lang,
    hyphenate: true
  )

  set par(
    justify: true,
    leading: if preserve_pages { 0.55em } else { 0.72em },
    first-line-indent: if preserve_pages { 0em } else { 1.4em }
  )

  if preserve_pages {
    set block(spacing: 0.52em)
  }

  // Headings
  show heading: it => {
    set text(font: book_fonts, weight: "bold")
    if preserve_pages {
      let sz = if it.level == 1 { 11.5pt } else if it.level == 2 { 10.2pt } else { 9.6pt }
      block(above: 0.65em, below: 0.35em)[#text(size: sz)[#it.body]]
    } else {
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
  }

  // Page setup: Standard scholarly / readable book layout
  let page_args = (:)
  if width != none and height != none {
    page_args.insert("width", width)
    page_args.insert("height", height)
  } else {
    page_args.insert("paper", paper)
  }

  if margin != none {
    page_args.insert("margin", margin)
  } else if preserve_pages {
    page_args.insert("margin", (x: 28pt, top: 28pt, bottom: 28pt))
  } else {
    page_args.insert("margin", (inside: 2.2cm, outside: 1.8cm, top: 2.2cm, bottom: 2.2cm))
  }

  set page(
    ..page_args,
    header: context {
      let page_num = here().page()
      if preserve_pages or page_num > 2 {
        let headings = query(heading.where(level: 1).before(here()))
        let chapter_title = if headings.len() > 0 {
          headings.last().body
        } else {
          title
        }

        set text(size: 8pt, font: book_fonts, fill: luma(90))
        if calc.even(page_num) {
          [ #smallcaps(title) #h(1fr) #page_num ]
        } else {
          [ #page_num #h(1fr) #smallcaps(chapter_title) ]
        }
      }
    },
    footer: none
  )

  if show_title_page {
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
  }

  // Body content
  body
}
