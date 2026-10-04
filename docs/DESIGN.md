# Design system

The look is inspired by a set of reference screens (a Behance project called Dafi): a warm blush canvas, white
rounded cards on nested panels, blurred colour-mesh gradients for identity, light tight type, black pill
buttons and a slim icon rail. Nothing was copied: the logo, gradients, layouts and copy are Padhotec's own.

## Tokens (`frontend/src/app/globals.css`)

| Role | Value |
|---|---|
| Canvas / panel / sunken | `#f5f1ef` / `#eee9e5` / `#e7e1da` |
| Surface (cards) | white, 28px radius, a hairline ring instead of a shadow |
| Ink / soft ink | `#111111` / `#5f5953` (the lighter `#8e8882` is for large headlines only) |
| Accents | yellow `#f3e04a`, sticky `#fbf2a6`, lilac `#ddccf3`, blush, sky, peach, mint |
| Status text | ok `#3f6b0e`, warn `#8a4b00`, bad `#b8281a` |

Type: Funnel Display (headlines, big numbers, wordmark), Funnel Sans (UI), Instrument Serif (titles on
gradient tiles). Headlines are light weight and tight. Where a headline has two parts, the subject is black
and the explanation is grey.

## Course colour

Each course gets one of eight mesh gradients (`.mesh-0` to `.mesh-7`), chosen from its id so it looks the same
everywhere. A grain overlay (`.mesh`) and a dark bottom scrim (`.scrim`) keep white text legible.

## Components (`frontend/src/components/ui.tsx`)

`Card`, `Panel`, `SectionTitle` (title plus a count), `PageHeader`, `Chip`, `Button` (black pill, outline pill),
`ProgressBar`, and `IntervalBar`, the signature mark: a soft yellow-to-lilac band for the likely range, a black
dot for the best estimate, and a yellow diamond for "you".

## Rules that keep it honest

- Colour never carries meaning alone. Every colour-coded value (score bars, risk effects, levels) also prints
  its number or a word.
- Uncertainty is shown wherever a model estimate appears. It is part of the design, not a footnote.
- Contrast: all text is at least 4.5:1 on its background (checked). The lighter grey (`#8e8882`, about 3.1 to 3.5:1)
  is used only at 24px and above, where WCAG asks for 3:1. Smaller text uses the darker grey.
- Motion is limited to a small hover lift. Nothing animates on load.
