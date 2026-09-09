---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 25px; padding: 46px 58px; }
  section.lead { text-align: center; }
  section.lead h1 { font-size: 54px; color: #E95420; }
  section.lead p { font-size: 28px; }
  h1 { color: #772953; font-size: 40px; }
  h2 { color: #E95420; font-size: 30px; }
  strong { color: #C7162B; }
  pre { font-size: 0.60em; line-height: 1.28; }
  table { font-size: 0.74em; }
  blockquote { font-size: 0.9em; border-left: 4px solid #E95420; }
  footer { color: #999; }
---

<!-- _class: lead -->

# Title of the Video

**One-line subtitle**

What this covers, in a phrase

<!--
Narration for the title slide. One HTML comment per slide, always the last thing in the slide. Speakable prose, one hundred to one hundred sixty words. This text becomes both the PPTX speaker notes and the TTS voiceover, so avoid reading paths or code aloud and prefer pronunciation-friendly wording.
-->

---

# A content slide

- Point one
- Point two

```go
// Verbatim code excerpt from the real repo — max ~16 lines at this font size
func example() {}
```

<!--
Narration for this slide. Describe what the code shows and why it matters rather than reading it. Directive comments like the class directive on the title slide are ignored by the video build script; every other comment is narration.
-->
