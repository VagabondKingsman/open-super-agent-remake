---
name: unslop
description: Write and edit English that reads like a skilled native writer, with no AI tells. Upgraded drop-in for pstack's unslop (same rule ids 3, 5, 7-33), plus rules for English written by Vietnamese speakers (articles, plurals, tense, calques like "discuss about") and a full workflow that turns a brief written in Vietnamese into a publish-ready English blog post with an SEO pack and a Vietnamese summary so the author can check the meaning. Use this skill whenever the user wants English content written, edited, polished, proofread, "made natural", "less AI", "unslopped" or checked for AI tells, and especially whenever they describe a blog post, article, newsletter, landing page, LinkedIn post, case study or product page idea in Vietnamese and want it in English, even if they never say "unslop". Not for pure translation the user wants word for word, or for code.
---

# Unslop (upgraded)

This skill does two jobs. It cuts AI tells from English writing, and it writes English content for authors whose first language is Vietnamese, starting from a brief they write in Vietnamese.

It keeps the rule ids of pstack's `unslop` (3, 5, 7 to 33) so other skills that cite "unslop rule 14" still work. New rules use prefixes. `T` rules catch habits that carry over from Vietnamese into English. `B` rules cover blog craft.

The author often cannot judge English style on their own. So the bar is higher than "grammatical". The text should read as if a good native editor wrote it, and the author must be able to verify the meaning without reading the English closely. That is why every write-from-brief delivery ends with a Vietnamese summary.

## Talk to the user in their language

Write the content in English. Talk to the user (questions, notes, summaries, placeholders explained) in the language they wrote to you, usually Vietnamese.

## Pick the mode

1. **Write from brief.** The user describes a post, often in Vietnamese. This is the main use. Follow the brief-to-post workflow below.
2. **Edit.** The user gives an English draft. Return the edited text and a short change log.
3. **Audit.** The user asks whether a text sounds like AI, or asks to point out problems without rewriting. Return a findings table, not a rewrite.
4. **Write clean.** Any other English writing (email, bio, docs). Apply the rules while drafting. No change log.

## Brief-to-post workflow

**Step 1. Read the brief.** Pull out the topic, the reader, what the reader should know or do afterwards, the angle, the facts the user supplied, target keyword, length, call to action, and the site's voice. Read `references/blog-playbook.md` for the post type that fits.

If something is missing, choose a sensible default and state it in the Vietnamese notes. Ask one question before writing only when the brief is too thin to have a point, for example a bare topic with no angle and no reader. A question costs the user a round trip, and a stated assumption costs them one line to correct.

**Step 2. Take a fact inventory.** List every claim you plan to make and where it comes from: the brief, well-established general knowledge, or nothing. Claims from nothing do not go in the post. Never invent statistics, studies, quotes, customer stories, prices, dates, or personal experiences of the author. Put a placeholder in their place, such as `[source needed]`, `[add your number]`, or `[add a real example from your work]`. A blog post with a fake number damages the author's credibility, and the author may not catch it in English.

If you have a web search tool and the post needs a current fact, search and cite the source in the notes instead of leaving a placeholder.

**Step 3. Outline.** Write the post's point as one sentence. Then write headings that make claims, not labels (B2). Each section should carry one idea the reader did not have before.

**Step 4. Draft clean.** Apply every rule while writing. A cleanup pass after drafting misses patterns, so the first draft should already be clean.

**Step 5. Scan and fix.** If code execution is available, run the scanner on the draft:

```bash
python3 scripts/scan_en.py post.md
python3 scripts/scan_en.py --compare draft.md final.md
```

The scanner flags candidates by rule id. Judge each flag in context. Then read the draft as if aloud. Rewrite any sentence you stumble on.

**Step 6. Deliver** in the format under "Output".

## Register

Pick the register from the post type and the site. When the brief does not say, default to American English and a conversational, expert voice.

| Post type | Allow | Hold firm on |
|---|---|---|
| How-to, tutorial | Second person, imperatives in steps, code | 27, 29, 33, B3 |
| Opinion, thought leadership | First person, strong claims, some rhetoric | 5, 7, 9, 25, B5 |
| Product, landing, marketing | Enthusiasm that rests on specifics, a clear CTA | 7, 10, 25, 27, 32 |
| News, update, changelog | Short paragraphs, dates and versions | 5, 27, T7 |
| Case study | Narrative order, numbers | B5 (no invented results), 27 |
| LinkedIn, social | Short lines, first person, one emoji if it carries meaning | 20, 22, T1 |

Contractions (it's, you'll, don't) are normal in blog English and make text sound less stiff. Use them unless the register is formal.

## Rules

### Content

3. **Superficial -ing tails.** "…, highlighting…", "…, ensuring…", "…, reflecting…", "…, showcasing…", "…, fostering…". Delete, or state the consequence as its own sentence with evidence.
5. **Vague attributions.** "Experts believe", "Studies show", "Industry reports suggest", "Many people say". Name the source or delete. Never invent one; use `[source needed]`.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore, vibrant. The extended list with replacements is in `references/vocabulary.md`. Replace with plain words or with the specific fact.
8. **Fancy ways to say "is".** "Serves as", "stands as", "boasts", "features", "represents". Say "is" or "has".
9. **"Not just X, but Y."** Also "It's not X, it's Y" and "X isn't about Y. It's about Z." State the point directly.
10. **Rule of three.** Don't force ideas into groups of three. Use the natural number.
11. **Synonym cycling.** Customer, client, user, buyer for the same person in one section. Pick one and repeat it.
12. **False ranges.** "From startups to enterprises, from coffee to code." List the real cases or name the real reader.

### Style

13. **Em dash overuse.** Avoid em dashes. Use a period or a comma. No en dashes or hyphens as substitutes. Number ranges like 2020-2024 are fine.
14. **Colon overuse.** Colons are fine before a list or an example, not as mid-sentence connectors.
15. **Boldface overuse.** Bold at most one phrase per section, and only when the reader must see it first.
16. **Inline-header lists.** "**Performance:** Performance improved…" Convert to prose. A bold lead-in that ends in a period and is followed by new detail is fine.
17. **Title case headings.** Use sentence case for headings. The post title may use title case if the site does.
18. **Decorative emojis.** Remove from headings and bullets.
19. **Curly quotes.** Use straight quotes in Markdown and code. In content for a CMS, follow the site; never mix the two.

### Communication artifacts

20. **Chatbot phrases.** "I hope this helps!", "Let me know if…", "Of course!", "Certainly!", "Let's dive in", "Let's explore", "Buckle up". Remove.
22. **Sycophantic tone.** "Great question!", "You're absolutely right!" Respond directly.

### Filler

23. **Filler phrases.** "In order to" becomes "to". "Due to the fact that" becomes "because". Delete "It is important to note that", "It's worth mentioning that", "When it comes to".
24. **Excessive hedging.** One hedge per claim at most. "Could potentially possibly" becomes "may".
25. **Generic conclusions.** "The future looks bright.", "In conclusion,", "In today's fast-paced world,", "At the end of the day". State a specific next step or stop.

### Jargon

26. **Abstract metaphor nouns.** Substrate, wedge, vector, locus, nexus, primitive (noun), harness (metaphor), surface (API surface), bedrock, scaffolding (metaphor), modality, paradigm, north star, flywheel, game-changer, journey (abstract), ecosystem (abstract), realm, unlock (metaphor). Pick the concrete word.

### Plain speech

27. **Say what it does, not how it feels.** "A seamless experience" names a feeling. "The page loads in under a second on 4G" names a fact. If a sentence could appear unchanged on a competitor's blog, it says nothing about this one. Cut it.
28. **Shorten or split dense sentences.** One idea per sentence. Break any sentence the reader has to reread.
29. **Active voice.** Name the actor. Passive is fine when the actor is unknown or doesn't matter.
30. **Cut adverbs, or use a stronger verb.** "Significantly improves" becomes the measured change. "Really", "truly", "incredibly", "extremely" usually go.
31. **Prefer the plain word.** Utilize becomes use, leverage becomes use, facilitate becomes help, numerous becomes many, commence becomes start.
32. **Mannered prose.** Aphorisms, rhetorical fragments, personified code, figurative verbs. "A dial worth turning" becomes "a parameter worth changing". Say what you mean.
33. **Over-compression.** Dropped articles, verbless fragments, arrows. Write whole sentences.

### Transfer from Vietnamese

These come from Vietnamese grammar and style showing through English. Native readers notice them at once. Full examples and the Vietnamese source of each pattern are in `references/vietnamese-transfer.md`. Read it before editing text a Vietnamese speaker wrote, and before writing from a Vietnamese brief, because translating the brief's phrasing produces these errors.

T1. **Calqued openers and slogans.** "In the era of 4.0", "In the digital age", "Nowadays,", "As we all know", "In the context of globalization". Start with the point.
T2. **Empty intensifiers.** "Very important", "very good", "so many", "extremely necessary". Use a precise word or a number.
T3. **Calqued nominalization.** "The use of", "the development of", "carry out the implementation of", "make a decision on the selection". Turn the noun back into a verb.
T4. **Calqued passive.** "The report was done by our team" becomes "Our team wrote the report".
T5. **Articles.** Vietnamese has no articles, so a, an, the and the zero article go wrong more than anything else. Check every noun phrase. First mention of a countable singular usually takes a/an; a known or unique thing takes the; general plurals and uncountables take none.
T6. **Plural and countability.** Informations, advices, feedbacks, equipments, researches, softwares, knowledges, homeworks are wrong. Watch subject-verb agreement too.
T7. **Tense drift.** Vietnamese marks time with words, not verb forms. Pick a tense per section and hold it. Use present tense for how things work, past for what happened, present perfect for results that still matter.
T8. **Word-level calques.** "Discuss about", "mention about", "help you to", "make you can", "return back", "until now" for "so far", "despite of", "according to me", "the price is cheap" for "the price is low", "open the app to see", "it has many people". The full table is in the reference.
T9. **Comma splices and run-ons.** Vietnamese chains clauses with commas. English needs a period, a semicolon, or a conjunction.
T10. **Topic-comment and dropped subjects.** "This product, it is very good." "Is very useful for beginners." Give each clause one subject.
T11. **Too formal for a blog.** Vietnamese formal register often turns into stiff English: "We would like to inform you", "Dear readers", "hereby". Write the way the reader talks.
T12. **Formats.** 1.000.000 VND becomes 1,000,000 VND or about US$40 if the brief gives a rate. 3,5% becomes 3.5%. Dates: October 29, 2026 (US) or 29 October 2026 (UK), never 29/10/2026 in body text. Space between number and unit (5 km), none before %.

### Blog craft

B1. **Lead with the point.** The first two sentences tell the reader what they'll get or why it matters to them. No throat-clearing, no definition of the topic.
B2. **Headings say something.** "Cache the API response, not the page" beats "Caching". Never "Introduction" or "Conclusion".
B3. **One concrete example per section.** A number, a case, a command, a before and after. If the brief has none, add a placeholder for the author to fill.
B4. **Rhythm.** Paragraphs of one to four sentences. Mix short and long sentences. A page of same-length sentences reads as machine-made even when each sentence is clean.
B5. **No fabricated experience.** Don't write "When I started my agency…" or "One of our clients…" unless the brief says so. Use `[add your story]`.
B6. **End with a next step.** A specific action, link, or question for the reader to act on. No summary of what they just read.
B7. **Lists only for parallel items.** Steps, options, or checklist items. Reasoning goes in paragraphs.
B8. **SEO without stuffing.** Put the primary keyword in the title, the first 100 words, one H2, and the meta description. Use it naturally after that. Never repeat the exact phrase in back-to-back sentences. If the keyword is ungrammatical as typed ("book homestay Hoi An direct"), use the closest natural phrasing ("book your Hoi An homestay direct") and say so under "Giả định". Search engines match close variants; readers notice broken English.

## Over-correction guard

Fixing slop badly produces a different kind of slop. Check the result against each point.

- **Don't chop everything into short sentences.** Keep connectors that carry logic (because, so, but, if, although).
- **Don't add facts while editing.** Rules 27 and 30 want numbers. If the source has none, write the claim more specifically with what you have, or add a placeholder.
- **Don't change numbers, names, quotes, product terms, or legal wording.**
- **Keep the author's position**, even when you'd argue the other side. You fix how it's said, not what's said.
- **Watch length.** Edits usually come out 10-35% shorter. Heavy slop can lose half. An edit longer than the original means you're adding.
- **Don't swap one cliché for another.** "Plays a pivotal role" to "is a key driver" changes nothing.
- **Don't overcorrect articles.** Not every noun needs "the". Generic plurals and abstract uncountables take no article.

## Output

**Write from brief.** Deliver in this order.
1. The post in English, Markdown, with an H1 title.
2. An SEO pack: title (60 characters or fewer), meta description (155 or fewer), URL slug, primary keyword, and two or three secondary keywords if the brief gave a keyword. Skip for non-blog content.
3. **Tóm tắt ý (Vietnamese).** One line per section saying what it argues, so the author can check the meaning. Keep it short.
4. **Cần bạn bổ sung (Vietnamese).** Every placeholder, what to put there, and why.
5. **Giả định (Vietnamese).** Defaults you chose (reader, length, tone, US or UK spelling). One line each. Skip if none.

If the user asked for a file or a doc, put the post there and keep items 2 to 5 in the reply.

**Edit.** The edited text first. Then a change log grouped by rule id, at most six lines, written in the user's language. If the author is a Vietnamese speaker, add up to three short "lỗi hay gặp" notes (pattern, wrong, right) so they learn from the edit. Skip both for one or two sentences.

**Audit.** One line with the level (clean, light, heavy) and density per 1,000 words if you ran the scanner. Then a table: rule id, short excerpt, fix. Order by impact, content first, formatting last. End with the three fixes that matter most.

Don't use any banned pattern in your own reply or notes.

## Bundled files

- `references/vocabulary.md`: extended AI vocabulary and phrase list with replacements, by rule id. Read it when scanning by hand.
- `references/vietnamese-transfer.md`: T1-T12 with the Vietnamese source pattern, the wrong English, and the fix. Read it before writing from a Vietnamese brief or editing a Vietnamese speaker's draft.
- `references/blog-playbook.md`: post-type templates, a Vietnamese brief template the user can fill in, SEO pack rules, and headline patterns. Read it at Step 1.
- `references/examples.md`: before and after edits, and one complete brief-to-post example. Read it to calibrate.
- `scripts/scan_en.py`: rule-id scanner. Skips code blocks, inline code and blockquotes. Supports `--json`, `--compare`, `--max-per-rule`.

Based on `unslop` from pstack (MIT, github.com/backnotprop/pstack). Rule ids 3, 5 and 7-33 keep the original meanings.
