// AlexandriaSandwich - Universal Book Typesetting Template
// Pure Typst - No LaTeX dependency

#let book_fonts = ("Noto Serif Devanagari", "Linux Libertine O", "Libertinus Serif", "Baskerville", "Charter", "PT Serif", "Times New Roman", "Devanagari MT", "Kohinoor Devanagari", "Noto Sans Devanagari")

#let orig-page(p) = context {
  let is_even = calc.even(here().page())
  let dx_val = if is_even { -1.8cm } else { 1.8cm }
  let align_dir = if is_even { left } else { right }
  place(align_dir, dx: dx_val)[
    #text(size: 7.5pt, fill: rgb("#b45309"), weight: "bold", font: book_fonts)[\[p. #p\]]
  ]
}

#let get_text(it) = {
  if type(it) == str {
    it
  } else if it.has("text") {
    it.text
  } else if it.has("children") {
    it.children.map(get_text).join("")
  } else if it.has("body") {
    get_text(it.body)
  } else {
    ""
  }
}

#let page_content(body) = layout(size => context {
  let m = measure(block(width: size.width)[#body])
  if m.height > size.height {
    let factor = (size.height / m.height) * 98%
    place(top + left)[
      #scale(x: factor, y: factor, origin: top + left)[
        #block(width: size.width / (factor / 100%))[#body]
      ]
    ]
  } else {
    block(width: size.width)[#body]
  }
})

#let fit-page = page_content

#let page-footnotes(notes) = {
  if notes != none and notes.len() > 0 {
    v(1fr)
    line(length: 30%, stroke: 0.4pt + luma(100))
    v(2pt)
    set text(size: 7.2pt, fill: luma(60))
    set par(leading: 0.28em, first-line-indent: 0em)
    for n in notes [
      #n \
    ]
  }
}

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
  page_labels: (),
  front_matter_pages: 0,
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

  set block(spacing: if preserve_pages { 0.52em } else { 0.65em })

  // Headings
  show heading: it => {
    set text(font: book_fonts, weight: "bold")
    if preserve_pages {
      if it.level == 1 {
        align(center)[#v(1.2cm)#text(size: 16pt)[#it.body]#v(0.8cm)]
      } else if it.level == 2 {
        block(above: 0.8em, below: 0.4em)[#text(size: 11.5pt)[#it.body]]
      } else {
        block(above: 0.6em, below: 0.3em)[#text(size: 10pt, style: "italic")[#it.body]]
      }
    } else {
      if it.level == 1 {
        v(1.0cm)
        align(center)[
          #text(size: 15pt)[#it.body]
        ]
        v(0.6cm)
      } else if it.level == 2 {
        v(0.6cm)
        text(size: 12pt)[#it.body]
        v(0.35cm)
      } else {
        v(0.4cm)
        text(size: 10.5pt, style: "italic")[#it.body]
        v(0.25cm)
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
    page_args.insert("margin", (inside: 2.2cm, outside: 2.2cm, top: 2.2cm, bottom: 2.2cm))
  }

  set page(
    ..page_args,
    header: context {
      let page_num = here().page()
      let idx = page_num - 1
      let plabel = if preserve_pages and page_labels != none and page_labels.len() > idx {
        page_labels.at(idx)
      } else {
        str(page_num)
      }

      // Check whether this page has a level 1 heading (chapter opening page, TOC, preface)
      let h1_on_page = query(heading.where(level: 1)).filter(h => h.location().page() == page_num)
      let is_chapter_start = h1_on_page.len() > 0

      // Suppress headers on unnumbered front-matter pages (cover, card, title, imprint, dedication)
      // AND on any chapter opening page!
      let suppress = is_chapter_start or (if preserve_pages {
        idx < 6
      } else {
        page_num <= 2
      })

      if not suppress {
        let clean_title = title.split("(").at(0).trim()
        let headings = query(heading.where(level: 1).before(here()))
        let clean_ch_title = if headings.len() > 0 {
          let raw = get_text(headings.last().body)
          raw.replace(regex("^\d+\.\s*"), "").trim()
        } else {
          clean_title
        }

        // Determine parity based on printed page label (plabel) if numeric
        let is_even = if plabel.matches(regex("^\d+$")).len() > 0 {
          calc.even(int(plabel))
        } else {
          calc.even(page_num)
        }

        let is_back_matter = clean_ch_title in ("Bibliography", "Index of Sūtras", "Index of Terms")
        let verso_title = if is_back_matter { clean_ch_title } else { clean_title }

        set text(size: 8.5pt, font: book_fonts, fill: luma(60))
        if is_even {
          grid(
            columns: (1fr, auto, 1fr),
            align: (left, center, right),
            [#plabel],
            [#text(style: "italic")[#verso_title]],
            []
          )
        } else {
          grid(
            columns: (1fr, auto, 1fr),
            align: (left, center, right),
            [],
            [#text(style: "italic")[#clean_ch_title]],
            [#plabel]
          )
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
