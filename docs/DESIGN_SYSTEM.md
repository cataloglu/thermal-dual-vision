# Design System (v2)

## Theme
- Dark-only UI
- High contrast text
- Neutral accents (no neon)
- Minimal shadows, subtle borders

## Color Tokens
- Background: near-black
- Surface: dark graphite
- Border: dark slate
- Text primary: near-white
- Text muted: gray
- Status: green (ok), amber (warn), red (error)

## Typography
- Sans-serif
- Clear hierarchy: page title > section title > label > body
- Use uppercase sparingly for table headers

## Layout
- Single column pages with cards
- Cards for logical grouping
- 16–24px spacing between sections
- Tables for lists, details in side panel where needed

## Components
- Cards: title + content
- Table: header row, clickable rows
- Form fields: label + input, masked for secrets
- Buttons: primary for Save, secondary for Test/Cancel

## Rules
- No placeholders or fake data
- Do not render sensitive values in clear text
- If backend value is missing, log it and leave field empty
- Avoid wizards; all settings visible as standard forms
