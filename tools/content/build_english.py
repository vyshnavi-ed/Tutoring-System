"""Builds packs/english_vocab.json (spaced repetition)."""
import json
import random
import sys

W = [  # word, part of speech, meaning, example, cloze sentence (___), Hindi gloss
    ("abundant", "adjective", "existing in large amounts; more than enough",
     "Mangoes are abundant in summer.", "After the rains, water was ___ in the village well.", "प्रचुर, भरपूर"),
    ("fragile", "adjective", "easily broken or damaged",
     "Handle the glass bangles carefully — they are fragile.", "The old clay pot was so ___ that it cracked when touched.", "नाज़ुक"),
    ("reluctant", "adjective", "unwilling and slow to do something",
     "Meena was reluctant to jump into the cold river.", "He was ___ to lend his new bicycle to anyone.", "अनिच्छुक"),
    ("curious", "adjective", "wanting to know or learn about something",
     "The curious child asked how rainbows form.", "The ___ cat kept sniffing the new box.", "जिज्ञासु"),
    ("generous", "adjective", "happy to give more money, time or help than expected",
     "Our generous neighbour shared sweets with the whole street.", "It was ___ of her to give her lunch to the new student.", "उदार"),
    ("ancient", "adjective", "very old; from a long time ago",
     "Hampi has many ancient temples.", "The museum displayed ___ coins from the Mauryan period.", "प्राचीन"),
    ("brief", "adjective", "lasting only a short time; short",
     "The principal gave a brief speech.", "We had a ___ stop for tea before continuing the journey.", "संक्षिप्त"),
    ("enormous", "adjective", "extremely large",
     "An elephant is an enormous animal.", "The banyan tree had an ___ trunk that five children could not circle.", "विशाल"),
    ("rapid", "adjective", "happening very quickly; fast",
     "The town saw rapid growth after the new railway line.", "The river's ___ current swept the leaves away.", "तीव्र, तेज़"),
    ("vivid", "adjective", "very bright, clear or detailed",
     "She described her dream in vivid detail.", "The rangoli was made with ___ colours.", "सजीव, चटकीला"),
    ("humble", "adjective", "not proud; not thinking you are better than others",
     "Despite winning, the champion stayed humble.", "The famous scientist was ___ and thanked her whole team.", "विनम्र"),
    ("gloomy", "adjective", "dark or sad; without hope",
     "The sky was gloomy before the storm.", "He felt ___ after losing the match.", "उदास, अंधकारमय"),
]

rng = random.Random(7)
sets, acts, order = {}, {}, []
for i, (w, pos, meaning, ex, cloze, hi) in enumerate(W):
    sid = f"W_{w.upper()}"
    order.append(sid)
    others = [x for x in W if x[0] != w]
    wrong_meanings = [x[2] for x in rng.sample(others, 3)]
    m_opts = wrong_meanings + [meaning]
    rng.shuffle(m_opts)
    wrong_words = [x[0] for x in rng.sample(others, 3)]
    w_opts = wrong_words + [w]
    rng.shuffle(w_opts)
    acts[f"CARD_{w.upper()}"] = {"title": w, "body":
        f"**{w}** *({pos})*\n\n**Meaning:** {meaning}\n\n**Example:** {ex}\n\n**हिंदी:** {hi}"}
    sets[sid] = {
        "title": w, "level": "vocabulary", "activity": f"CARD_{w.upper()}", "links": [],
        "items": [
            {"id": f"{sid}.recognise", "type": "mcq", "prompt": f"What does **{w}** mean?",
             "options": m_opts, "answer": meaning},
            {"id": f"{sid}.cloze", "type": "mcq", "prompt": f"Choose the word that fits: {cloze}",
             "options": w_opts, "answer": w},
            {"id": f"{sid}.produce", "type": "text", "prompt": f"Type the word that means: *{meaning}* (starts with “{w[0]}”)",
             "answer": w, "accepted": [w]},
            {"id": f"{sid}.use", "type": "free_text", "prompt": f"Write your own sentence using the word **{w}**.",
             "rubric": f"The sentence must use '{w}' (or a form of it) correctly, with the meaning '{meaning}', and be grammatical. "
                       "Minor spelling slips elsewhere are fine.",
             "keywords": [w[:max(4, len(w) - 2)]], "min_words": 5},
        ],
    }

pack = {
    "id": "english_vocab",
    "title": "English Vocabulary — Set 1",
    "subject": "English (Class 6–7)",
    "strategy": "spaced_repetition",
    "status": "approved",
    "description": "Each word climbs boxes: recognise the meaning → pick it in a sentence → type it → use it yourself. Missed words come back soon; known words come back days later.",
    "config": {"box_intervals_days": [0, 1, 3, 7, 14, 30], "new_per_session": 5, "relearn_gap": 3,
               "alert_after_failures": 3, "reveal_answer_on_fail": True},
    "activities": acts, "item_sets": sets,
    "units": [{"id": "set1", "title": "Word set 1", "sets": order}],
}
json.dump(pack, open(sys.argv[1], "w"), indent=2, ensure_ascii=False)
print("words", len(sets))
