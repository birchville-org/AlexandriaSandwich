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
    let ratio_val = (size.height / m.height) * 0.98
    let f = calc.max(0.82, ratio_val)
    place(top + left)[
      #scale(x: f * 100%, y: f * 100%, origin: top + left)[
        #block(width: size.width / f, height: size.height / f)[#body]
      ]
    ]
  } else {
    block(width: size.width, height: size.height)[#body]
  }
})

#let fit-page = page_content

#let book-half-title(title: "", subtitle: none) = {
  align(center)[
    #v(4.2cm)
    #text(size: 24pt, weight: "bold", font: book_fonts)[#title]
    #if subtitle != none and subtitle != "" [
      #v(1.2cm)
      #text(size: 13pt, font: book_fonts, tracking: 0.12em)[#upper(subtitle)]
    ]
    #v(1fr)
  ]
}

#let book-title-page(
  title: "",
  subtitle: none,
  author: none,
  publisher: none,
) = {
  align(center)[
    #v(2.6cm)
    #if title != "" [
      #text(size: 28pt, weight: "bold", font: book_fonts)[#title]
    ]
    #if author != none and author != "" [
      #v(3.0cm)
      #text(size: 13.5pt, weight: "medium", font: book_fonts, tracking: 0.18em)[#upper(author)]
    ]
    #if subtitle != none and subtitle != "" [
      #v(2.8cm)
      #text(size: 11.5pt, font: book_fonts, tracking: 0.14em)[#upper(subtitle)]
    ]
    #v(1fr)
    #if publisher != none and publisher != "" [
      #text(size: 9.5pt, font: book_fonts, tracking: 0.08em)[
        #set par(leading: 0.55em)
        #publisher
      ]
    ]
    #v(1.8cm)
  ]
}

#let book-imprint-page(
  editions: (),
  copyright: "",
  isbn: "",
  publisher_name: "",
  available_at: none,
  addresses: (),
  sales_restriction: none,
  colophon: ()
) = {
  let ed_arr = if type(editions) == array { editions } else if editions != none and editions != "" { (editions,) } else { () }
  let addr_arr = if type(addresses) == array { addresses } else if addresses != none and addresses != "" { (addresses,) } else { () }
  let col_arr = if type(colophon) == array { colophon } else if colophon != none and colophon != "" { (colophon,) } else { () }

  align(center)[
    #set text(size: 8.5pt, font: book_fonts)
    #set par(leading: 0.45em, justify: false)
    
    #v(1.6cm)
    
    // 1. Edition History
    #if ed_arr.len() > 0 [
      #for ed in ed_arr [
        #ed
        #v(0.12em)
      ]
    ]
    
    #v(0.6cm)
    
    // 2. Copyright & Rights
    #if copyright != "" [
      #text(weight: "medium")[#copyright]
    ]
    
    #if isbn != "" [
      #v(0.45cm)
      #text(weight: "bold")[#isbn]
    ]
    
    #v(0.6cm)
    
    // 3. Publisher & Branch Addresses
    #if available_at != none and available_at != "" [
      #text(style: "italic")[#available_at] \
      #v(0.15cm)
    ]
    #if publisher_name != "" [
      #text(size: 10pt, weight: "bold", tracking: 0.1em)[#upper(publisher_name)]
      #v(0.35cm)
    ]
    #if addr_arr.len() > 0 [
      #for addr in addr_arr [
        #text(size: 7.5pt)[#addr]
        #v(0.12em)
      ]
    ]
    
    #v(1fr)
    
    // 4. Sales Restriction / Territory notice
    #if sales_restriction != none and sales_restriction != "" [
      #text(size: 7.5pt, style: "italic", tracking: 0.06em)[#sales_restriction]
      #v(1.0cm)
    ]
    
    // 5. Printer Colophon at bottom
    #if col_arr.len() > 0 [
      #for line in col_arr [
        #text(size: 7.2pt, tracking: 0.04em)[#line]
        #v(0.1em)
      ]
    ]
    #v(1.2cm)
  ]
}

#let book-toc-page(
  is_first: false,
  roman_label: "",
  body
) = {
  set text(font: book_fonts)
  if is_first [
    #v(0.2cm)
    #align(center)[= CONTENTS]
    #v(0.45cm)
  ]
  body
}

#let book-lesson-page(
  number: "",
  title: "",
  syllabus: (),
  num_dx: -168pt,
) = {
  set text(font: book_fonts)
  v(1.6cm)
  if number != "" and number != none [
    #place(left, dx: num_dx)[
      #text(size: 88pt, weight: "bold", fill: rgb("#03192e"), font: book_fonts)[#number]
    ]
  ]
  [= #upper(title)]
  v(1.4em)
  if syllabus.len() > 0 [
    #grid(
      columns: (84pt, 1fr),
      row-gutter: 1.85em,
      ..syllabus.map(cat => (
        text(weight: "bold", size: 10.5pt)[#cat.at(0)],
        stack(
          spacing: 0.65em,
          ..cat.at(1).map(item => text(size: 10.5pt)[#item])
        )
      )).flatten()
    )
  ]
}

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

#let sidehead(body, dx: -160pt, width: 92pt) = place(
  left,
  dx: dx,
  block(width: width)[
    #set text(size: 9.0pt, weight: "bold", font: book_fonts, hyphenate: false)
    #set par(leading: 0.35em, justify: false)
    #body
  ]
)

#let book(
  title: "Untitled Book",
  book_title: none,
  author: "Alexandria Archive",
  date: none,
  paper: "a5",
  width: none,
  height: none,
  margin: none,
  font_size: none,
  leading: none,
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

  let base_font_size = if font_size != none {
    font_size
  } else if preserve_pages {
    11.5pt
  } else {
    11pt
  }

  let base_leading = if leading != none {
    leading
  } else if preserve_pages {
    0.72em
  } else {
    0.72em
  }

  // Typography rules
  set text(
    font: book_fonts,
    size: base_font_size,
    lang: lang,
    hyphenate: true
  )

  set par(
    justify: true,
    leading: base_leading,
    first-line-indent: (amount: 1.5em, all: true)
  )

  set block(spacing: if preserve_pages { 0.55em } else { 0.65em })

  // Headings
  show heading: it => {
    set text(font: book_fonts, weight: "bold")
    if preserve_pages {
      if it.level == 1 {
        align(center)[
          #block(above: 0.8em, below: 0.6em)[
            #text(size: 14pt, weight: "bold", tracking: 0.08em)[#it.body]
          ]
        ]
      } else if it.level == 2 {
        align(center)[
          #block(above: 0.6em, below: 0.3em)[#text(size: 11.5pt)[#it.body]]
        ]
      } else {
        block(above: 0.45em, below: 0.25em)[#text(size: 10pt, style: "italic")[#it.body]]
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
        align(center)[
          #text(size: 12pt)[#it.body]
        ]
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

      // Suppress headers on unnumbered pages, front matter pages, or chapter opening pages
      let suppress = is_chapter_start or plabel == "" or plabel == none or idx < front_matter_pages or (if show_title_page { page_num <= 2 } else { false })

      if not suppress {
        let clean_title = title.split("(").at(0).trim()
        let headings = query(heading.where(level: 1).before(here()))
        let clean_ch_title = if headings.len() > 0 {
          let raw = get_text(headings.last().body)
          raw.replace(regex("^\d+\.\s*"), "").trim()
        } else {
          clean_title
        }

        let devanagari_digits = ("०": 0, "१": 1, "२": 2, "३": 3, "४": 4, "५": 5, "६": 6, "७": 7, "८": 8, "९": 9)
        let parse_dev_int(s) = {
          let acc = 0
          for ch in s {
            if ch in devanagari_digits {
              acc = acc * 10 + devanagari_digits.at(ch)
            }
          }
          acc
        }
        let is_dev_num = plabel.clusters().all(c => c in devanagari_digits) and plabel.len() > 0

        // Determine parity based on printed page label (plabel) supporting Devanagari, Arabic and Roman numerals
        let roman_map = (
          i: 1, ii: 2, iii: 3, iv: 4, v: 5, vi: 6, vii: 7, viii: 8, ix: 9, x: 10,
          xi: 11, xii: 12, xiii: 13, xiv: 14, xv: 15, xvi: 16, xvii: 17, xviii: 18, xix: 19, xx: 20,
          xxi: 21, xxii: 22, xxiii: 23, xxiv: 24, xxv: 25, xxvi: 26, xxvii: 27, xxviii: 28, xxix: 29, xxx: 30,
          xxxi: 31, xxxii: 32, xxxiii: 33, xxxiv: 34, xxxv: 35
        )
        let is_even = if is_dev_num {
          calc.even(parse_dev_int(plabel))
        } else if plabel.matches(regex("^\d+$")).len() > 0 {
          calc.even(int(plabel))
        } else if lower(plabel) in roman_map {
          calc.even(roman_map.at(lower(plabel)))
        } else {
          calc.even(page_num)
        }

        let v_title = if book_title != none and book_title != "" { book_title } else { clean_title }
        let r_title = clean_ch_title

        set text(size: 10.5pt, font: book_fonts, fill: luma(20))
        if is_even {
          grid(
            columns: (1fr, auto, 1fr),
            align: (left + horizon, center + horizon, right + horizon),
            [#plabel],
            [#text(tracking: 0.04em)[#v_title]],
            []
          )
        } else {
          grid(
            columns: (1fr, auto, 1fr),
            align: (left + horizon, center + horizon, right + horizon),
            [],
            [#text(tracking: 0.04em)[#r_title]],
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
