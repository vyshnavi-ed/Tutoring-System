"""Convert packs/english_vocab.json to inquiry: infer meaning from context before seeing it."""
import json
import sys

path = sys.argv[1]
pack = json.load(open(path))
pack["pedagogy"] = "inquiry"
pack["description"] = ("Inquiry-based: guess each word's meaning from sentences before seeing it, then use it about "
                       "your own life. Spaced repetition brings words back until you know them.")
pack["config"].update({"max_hints": 1, "ai_followups": True})

THIRD = {  # a third context sentence per word (the example + cloze give the other two)
    "abundant": "There was so much rice in the granary that the farmers called it an abundant harvest.",
    "fragile": "The baby bird's wing was so fragile that we held it with both hands.",
    "reluctant": "Ravi was reluctant to tell his mother about the broken cup, so he waited until evening.",
    "curious": "Curious about the strange noise, the boys crept closer to the old well.",
    "generous": "The shopkeeper was generous and added two extra bananas without charging us.",
    "ancient": "Our grandfather showed us an ancient map, its paper yellow and cracked with age.",
    "brief": "The rain was brief — it stopped after just five minutes.",
    "enormous": "The enormous wave was taller than the fishing boat.",
    "rapid": "With rapid steps she reached the bus stop just in time.",
    "vivid": "The peacock spread its vivid blue and green feathers.",
    "humble": "Although he was the village's best singer, he was humble and never boasted.",
    "gloomy": "The house felt gloomy with all the lights off and the curtains closed.",
}

acts = pack["activities"]
for sid, s in pack["item_sets"].items():
    w = s["title"]
    card = acts[s["activity"]]["body"]
    example = card.split("**Example:** ")[1].split("\n")[0]
    meaning = card.split("**Meaning:** ")[1].split("\n")[0]
    cloze = s["items"][1]["prompt"].replace("Choose the word that fits: ", "").replace("___", w)
    s["episode"] = {
        "explore": {"tool": "context_sentences", "word": w, "sentences": [example, cloze, THIRD[w]],
                    "prompt": f"Read these three sentences. Each one uses the word **{w}**.",
                    "record": f"What do you think **{w}** means? Make your best guess."},
        "probe": [{"kind": "why", "prompt": f"Which words in the sentences gave you a clue about **{w}**?",
                   "followup": "Look at the words just before and after it. What do they tell you?"}],
        "reprobe": f"Read the sentences again. What clue tells you what **{w}** means?",
        "explain": {"activity": s["activity"],
                    "revisit": "Your guess was {prediction}. How close were you? Here's the meaning:"},
        "connect": [f"Think of something in your own life that is **{w}** — you'll get to use the word in a sentence soon."],
        "key_learning": f"{w}: {meaning}",
    }
    hints = {
        "recognise": "Think back to the three sentences. Which meaning fits all of them?",
        "cloze": "Read the sentence aloud with each word in the gap. Which one makes sense?",
        "produce": f"It starts with “{w[0]}” and has {len(w)} letters.",
        "use": "Try a sentence about your home, school or village, e.g. “The … was …”.",
    }
    for it in s["items"]:
        it["hints"] = [hints[it["id"].split(".")[-1]]]

json.dump(pack, open(path, "w"), indent=2, ensure_ascii=False)
print("words with episodes:", len(pack["item_sets"]))
