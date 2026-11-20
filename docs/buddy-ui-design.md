# Science Buddy: interface design brief

Paste this into a new chat to continue the design. It describes what has been decided so far and what is still open.

## Principles

- **Phone first.** Designed at about 375 to 420px wide. Wide screens get a sidebar, but the phone layout comes first.
- **Calm and minimal.** One main action per screen. Few colours, generous space, no gradients or heavy shadows.
- **Whimsy in small doses.** Gentle motion, a friendly face, and small surprises. Motion always stops for people who have reduce-motion turned on.
- **The child does the thinking.** Screens ask one question at a time and make the child's own words the centre of attention.
- **Gender-neutral Buddy.** Buddy has a face, not a person. It has no gender, hair or body.

## Type

- **Font:** Nunito (Google Fonts), with fallbacks "Avenir Next" and system-ui.
- **Weights:** 400 for body, 500 for headings and labels. No 600 or 700.
- **Scale:** headings 18 to 26px, body 15 to 16px, labels and captions 13 to 14px.
- **Case:** sentence case everywhere, including labels and buttons.

## Colour tokens (light mode)

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | #F6F5F0 | Page background |
| `--card` | #FFFFFF | Cards, inputs, Buddy's bubbles on white |
| `--ink` | #2F3B35 | Main text |
| `--ink-soft` | #6B7A72 | Secondary text, hints |
| `--leaf` | #8DB8A0 | Primary buttons, current step, mic |
| `--leaf-soft` | #E4EFE8 | Buddy's speech bubbles, quiet buttons |
| `--sand` | #F2E9DC | Notes and banners |
| `--line` | #E3E2DA | Hairline borders (0.5px) |
| `--face` | #CFE5D8 | Buddy's face |

Rainbow halo colours (used only for the rainbow and session end): #C9D9EE, #E3D5EC, #F3D2C2, `--face`, `--leaf`. The discovery star is gold, #E9C46A.

**Dark mode** (set by the phone, or by `data-theme`): bg #1F2723, card #27312C, ink #E6EDE8, ink-soft #9DAAA2, leaf #7FAE95, leaf-soft #2F3D36, sand #33302A, line #3A4540, face #3E5A4C.

## Shapes and spacing

- Cards: 12 to 14px corner radius, 0.5px border.
- Buttons and chips: fully rounded pills. The primary button is solid `--leaf` with white text.
- Chat bubbles: 18px radius, with a small square corner on the side the speaker is on.
- Page gutter: at least 16px, using safe-area insets.

## Motion

- Buddy's face bobs gently and blinks about every 5 seconds.
- Buddy's sprout sways.
- Three small sparkles float around the face.
- The mic has a slow ripple ring.
- The rainbow halo draws in band by band on load, then the gold star pops in.
- Tapping Buddy wiggles it and changes the speech bubble.
- All motion is off under reduce-motion.

## The inquiry journey

Six steps, named for a child. Shown as a strip on phones and a sidebar on wide screens. Finished steps are solid green, the current step is a white circle with a pulsing green ring, and future steps are outlined. Tapping or hovering a circle opens a card with that step's description and bullet points.

1. **Observe:** I look closely
2. **Wonder:** I get curious
3. **Guess:** I think about what might happen
4. **Plan a test:** I plan how to find out
5. **Test it:** I investigate
6. **My Discovery:** I make sense of what I found. This name is still under review; "What I found out" is the leading alternative.

Skill levels are not shown to the child for now.

## Screens designed so far

- **Home:** https://claude.ai/artifact/9qoHYuN3ac44TLAooaMMMz
  Buddy's face in a rainbow halo, a greeting, one question, a mic and a typed box, four starter chips, and "My discoveries".
- **Chat:** https://claude.ai/artifact/1JLK2ypyjvyduvBdopBWfT
  The journey sidebar, the chat thread (tulsi plant example), and a "My test plan" card.
- **Remaining screens:** https://claude.ai/artifact/3Mt4Jb4iks9RAErUT6oTdS
  My discoveries, photo describe-first prompt, photo not kept, parent consent, wellbeing reply, session end, offline and thinking, voice listening, settings.

These links are private. The owner must share them to give others access.

## Rules for the content

- Buddy asks one question per turn and keeps replies short.
- Buddy never describes or identifies what is in a photo. The child describes first.
- Photos of people are refused and never stored. The message is kind and offers another photo.
- After a worrying disclosure, Buddy's reply points the child to a trusted adult and the chat stops there.
- No secrets: Buddy never asks the child to keep anything from parents or teachers.
- Buddy never claims to be a person.

## Still to design or decide

- Whether the journey card opens on the current step when the chat loads. Decided: no, it opens only when the child taps or hovers.
- The final journey step name ("My Discovery" or "What I found out").
- Kannada and other language support (not designed).
- Real parental consent (the current screen is a prototype, not verified consent).
- The discoveries list with photos, once real photos exist.
- Empty states for a brand-new child with no notes yet.
- The teacher or parent view.
