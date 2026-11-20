"""Convert packs/math_fractions.json to the inquiry pedagogy: episodes, hint ladders, misconception probes."""
import json
import re
import sys
from fractions import Fraction as F
from math import gcd

path = sys.argv[1]
pack = json.load(open(path))
S = pack["item_sets"]
pack["pedagogy"] = "inquiry"
pack["description"] = ("Inquiry-based: predict, investigate with fraction strips, explain in your own words — "
                       "then practise. Wrong answers get a thinking question first, not the answer.")
pack["config"].update({"max_hints": 2, "ai_followups": True})

def fs(x):
    x = F(x)
    return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)

def lcm(a, b): return a * b // gcd(a, b)

STRIPS = [2, 3, 4, 6, 8, 12]

# ------------------------------------------------------------------ episodes
EP = {
 "F_MEANING": {
  "elicit": [{"prompt": "Have you ever shared a roti, a chocolate or a fruit with someone? How did you make sure the shares were fair?",
              "followup": "What would make a share *unfair*?"}],
  "predict": {"prompt": "A roti is torn into 4 pieces of different sizes. You get 1 piece. Do you have one quarter (1/4) of the roti?",
              "options": ["Yes, it is 1 out of 4 pieces", "No", "It depends"]},
  "explore": {"tool": "real_materials", "prompt": "Investigate with paper.",
              "materials": ["a sheet of paper (or a roti/chapati)", "a pencil"],
              "steps": ["Fold the paper in half, then in half again. Open it out.",
                        "How many parts are there? Are they all the same size?",
                        "Shade or colour 3 of the parts.",
                        "Now fold another sheet into 4 parts that are NOT equal (fold any way you like)."],
              "record": "What did you notice? How is the first sheet different from the second?"},
  "probe": [{"kind": "observe", "prompt": "On your first sheet, what part of the paper did you shade? Describe it in words."},
            {"kind": "why", "prompt": "Why can't we call one piece of the second (unequal) sheet a quarter?",
             "followup": "What has to be true about the pieces?"},
            {"kind": "summarise", "prompt": "In your own words: what do the top and bottom numbers of a fraction like 3/4 tell us?"}],
  "explain": {"activity": "L_MEANING",
              "revisit": "You predicted {prediction}. A quarter means one of **4 equal** parts — if the pieces aren't equal, one piece isn't a quarter."},
  "connect": ["Cutting a watermelon for the family: everyone gets a fair share only if the slices are equal.",
              "A cricket over has 6 balls — after 2 balls, 2/6 of the over is done.",
              "If 1 of the 4 weeks of the month is holidays, that's 1/4 of the month."],
  "key_learning": "A fraction tells how many equal parts the whole is cut into (bottom) and how many of those parts we take (top).",
 },
 "M_FACTORS": {
  "predict": {"prompt": "You have 12 laddoos to pack into boxes. Every box must have the same number and none can be left over. How many different box sizes do you think are possible?",
              "options": ["1 or 2", "3 or 4", "5 or 6", "More than 6"]},
  "explore": {"tool": "problem", "prompt": "Investigate.",
              "problem": "Try box sizes 1, 2, 3, 4 … up to 12. For each one, can you pack all **12 laddoos** with none left over?\n\nThen do the same for **18 laddoos**.",
              "record": "Which box sizes work for 12? Which work for 18? Which work for both?"},
  "probe": [{"kind": "observe", "prompt": "Which box sizes worked for both 12 and 18? Which is the biggest?"},
            {"kind": "why", "prompt": "Why does a box size of 5 not work for 12 laddoos?"},
            {"kind": "summarise", "prompt": "In your own words, what is the biggest number that works for both called, and how do you find it?"}],
  "explain": {"activity": "L_FACTORS", "revisit": "You predicted {prediction}. For 12 there are 6 box sizes: 1, 2, 3, 4, 6, 12 — these are the **factors** of 12."},
  "connect": ["Arranging 24 chairs in equal rows for an assembly: the number of rows must be a factor of 24.",
              "Sharing 30 marbles equally among friends works for 2, 3, 5, 6, 10 or 15 friends."],
  "key_learning": "A factor divides a number with nothing left over; the HCF is the biggest factor two numbers share.",
 },
 "M_MULTIPLES": {
  "predict": {"prompt": "Bus A leaves the stand every 4 minutes. Bus B leaves every 6 minutes. Both leave together right now. When do you think they will next leave together?",
              "options": ["After 10 minutes", "After 12 minutes", "After 24 minutes", "Not sure"]},
  "explore": {"tool": "problem", "prompt": "Investigate.",
              "problem": "Write down the times Bus A leaves: 4, 8, 12, …\n\nWrite down the times Bus B leaves: 6, 12, …\n\nKeep going up to 30 minutes.",
              "record": "At which times do both buses leave together? Which is the first one?"},
  "probe": [{"kind": "observe", "prompt": "What is the first time both buses leave together? Is there a pattern in the later times?"},
            {"kind": "why", "prompt": "Why isn't 24 minutes the answer, even though 4 × 6 = 24?"},
            {"kind": "summarise", "prompt": "In your own words, how would you find the first time two buses meet again?"}],
  "explain": {"activity": "L_MULTIPLES", "revisit": "You predicted {prediction}. The lists meet first at **12** — the lowest common multiple of 4 and 6."},
  "connect": ["Two friends water plants: one every 2 days, one every 3 days — they meet at the garden every 6 days.",
              "Buying cups in packs of 6 and plates in packs of 8: the smallest equal number you can buy is 24 of each."],
  "key_learning": "The LCM is the first number that appears in both times tables.",
 },
 "F_EQUIV": {
  "predict": {"prompt": "Is 2/3 of a roti the same amount as 4/6 of the same roti?", "options": ["Yes, the same", "No, 4/6 is more", "No, 2/3 is more"]},
  "explore": {"tool": "fraction_strips", "strips": STRIPS, "preset": [{"parts": 3, "shaded": 2}],
              "prompt": "A strip with **2/3** shaded is ready. Add strips cut into 6 and 12 parts. Shade pieces until each strip covers exactly the same length as 2/3.",
              "record": "How many sixths matched 2/3? How many twelfths? What pattern do you see?"},
  "probe": [{"kind": "observe", "prompt": "What happened to the number of pieces and their size when you went from thirds to sixths?"},
            {"kind": "why", "prompt": "Why does 2/3 cover the same length as 4/6, even though the numbers are different?",
             "followup": "What happened to each piece when you cut thirds into sixths?"},
            {"kind": "where_else", "prompt": "Where else might two different-looking amounts be the same? (Think of money, time or measuring.)"},
            {"kind": "summarise", "prompt": "In your own words: how can you make a fraction that is equal to 3/5?"}],
  "explain": {"activity": "L_EQUIV", "revisit": "You predicted {prediction}. On the strips, 2/3 and 4/6 end at exactly the same place — they're **equivalent**."},
  "connect": ["Half an hour and 30 minutes out of 60 are the same amount of time.",
              "50 paise is half a rupee — and so is 2 coins of 25 paise out of 4."],
  "key_learning": "Cutting every piece into the same number of smaller pieces changes the numbers but not the amount.",
 },
 "F_SIMPLIFY": {
  "predict": {"prompt": "Is 18/24 the same as 3/4?", "options": ["Yes", "No", "Not sure"]},
  "explore": {"tool": "fraction_strips", "strips": [2, 3, 4, 6, 8, 12],
              "prompt": "Build a strip of 12 parts and shade **9** (that's 9/12). Now find a strip with *fewer, bigger* pieces that covers exactly the same length.",
              "record": "Which strip matched 9/12 with the fewest pieces? What did you divide by?"},
  "probe": [{"kind": "observe", "prompt": "When you used bigger pieces, what happened to both numbers?"},
            {"kind": "why", "prompt": "Why must you divide the top and the bottom by the *same* number?"},
            {"kind": "summarise", "prompt": "In your own words: how do you know when a fraction can't be simplified any more?"}],
  "explain": {"activity": "L_SIMPLIFY", "revisit": "You predicted {prediction}. 18/24 and 3/4 are equal — dividing both by 6 (their HCF) gives the simplest form."},
  "connect": ["Saying 'half the class' is simpler than '20 out of 40 students'.",
              "Recipes for 8 people can be simplified to recipes for 2 by dividing every amount by 4."],
  "key_learning": "Simplifying means using the biggest possible pieces: divide top and bottom by their HCF.",
 },
 "F_MIXED": {
  "predict": {"prompt": "Seven children each get 1/3 of a roti. Is that more than 2 whole rotis?", "options": ["More than 2", "Exactly 2", "Less than 2"]},
  "explore": {"tool": "fraction_strips", "strips": [2, 3, 4], "max_rows": 4,
              "prompt": "Shade **7 thirds** using strips cut into 3 parts. You'll need more than one strip!",
              "record": "How many whole strips did you fill? How many thirds were left over?"},
  "probe": [{"kind": "observe", "prompt": "How did you write 7/3 as wholes and a part?"},
            {"kind": "why", "prompt": "Why is 7/3 bigger than 1, but 2/3 is smaller than 1?"},
            {"kind": "summarise", "prompt": "In your own words, how do you turn an improper fraction into a mixed number?"}],
  "explain": {"activity": "L_MIXED", "revisit": "You predicted {prediction}. 7 thirds fill 2 whole strips with 1 third left: **2 1/3**."},
  "connect": ["'Two and a half cups of rice' is a mixed number — 5 half-cups.",
              "A 1 1/2 hour film is 3 half-hours long."],
  "key_learning": "An improper fraction can be split into whole ones and a leftover part — that's a mixed number.",
 },
 "F_ADD_LIKE": {
  "elicit": [{"prompt": "You ate 2 slices of a pizza cut into 8, then 1 more slice. How would you describe how much you ate?"}],
  "predict": {"prompt": "Amma cuts a cake into 8 equal pieces. You eat 3 and your brother eats 2. What fraction of the cake did you eat together?",
              "options": ["5/8", "5/16", "6/8", "Not sure"]},
  "explore": {"tool": "fraction_strips", "strips": [4, 8, 12],
              "prompt": "Make a strip of **8** parts. Shade 3 pieces for you, then 2 more for your brother.",
              "record": "How much of the strip is shaded altogether? Did the size of the pieces change?"},
  "probe": [{"kind": "observe", "prompt": "When you shaded more pieces, did the size of each piece change?"},
            {"kind": "why", "prompt": "So why does the bottom number stay 8 when you add 3/8 and 2/8?",
             "followup": "What does the bottom number describe — the number of pieces you have, or the size of each piece?"},
            {"kind": "where_else", "prompt": "Where else do you add parts that are the same size?"},
            {"kind": "summarise", "prompt": "In your own words: how do you add two fractions with the same denominator?"}],
  "explain": {"activity": "L_ADD_LIKE", "revisit": "You predicted {prediction}. The strip shows **5 of the 8** pieces shaded — 5/8. Adding pieces doesn't change their size, so the 8 stays."},
  "connect": ["Filling a water tank: 2/10 in the morning and 3/10 in the evening makes 5/10 — half the tank.",
              "Walking 1/4 km to the shop and 1/4 km back is 2/4 km — half a kilometre."],
  "key_learning": "When the pieces are the same size, add how many pieces you have; the denominator (size of each piece) stays the same.",
 },
 "F_COMPARE": {
  "predict": {"prompt": "Which is bigger: 3/4 of a roti or 5/6 of the same roti?", "options": ["3/4", "5/6", "They are the same"]},
  "explore": {"tool": "fraction_strips", "strips": [3, 4, 6, 12],
              "prompt": "Build **3/4** on one strip and **5/6** on another. Compare where the shading ends. Then try a strip of 12 parts for each.",
              "record": "Which was longer? How did the 12-part strips help you be sure?"},
  "probe": [{"kind": "observe", "prompt": "Which shading went further along the strip?"},
            {"kind": "why", "prompt": "5/6 has a bigger bottom number. Why can it still be bigger than 3/4?",
             "followup": "Is a sixth of a roti a bigger or smaller piece than a quarter?"},
            {"kind": "summarise", "prompt": "In your own words: how can you compare any two fractions fairly?"}],
  "explain": {"activity": "L_COMPARE", "revisit": "You predicted {prediction}. With twelfths: 3/4 = 9/12 and 5/6 = 10/12, so **5/6 is bigger** — by just one twelfth."},
  "connect": ["Is 3/5 of the class or 2/3 of the class more students? Same idea.",
              "Comparing two shops' discounts like '1/4 off' and '1/3 off'."],
  "key_learning": "To compare fractions fairly, cut both into pieces of the same size (a common denominator), then compare the counts.",
 },
 "F_ADD_UNLIKE": {
  "predict": {"prompt": "Is 1/2 + 1/3 more than 1 whole, less than 1, or exactly 1?", "options": ["More than 1", "Exactly 1", "Less than 1"]},
  "explore": {"tool": "fraction_strips", "strips": STRIPS,
              "prompt": "Build **1/4** and **1/6** on two strips. Can you add them yet? Look for another strip whose pieces fit exactly into *both* a quarter and a sixth.",
              "record": "Which strip helped? What is 1/4 + 1/6 in those pieces?"},
  "probe": [{"kind": "observe", "prompt": "How many twelfths did 1/4 cover? How many did 1/6 cover?"},
            {"kind": "why", "prompt": "Why can't we just add 1/4 + 1/6 as 2/10?",
             "followup": "Is 2/10 bigger or smaller than 1/4, which you started with?"},
            {"kind": "where_else", "prompt": "Where else do you have to change things into the same unit before adding them?"},
            {"kind": "summarise", "prompt": "In your own words: what are the steps to add fractions with different denominators?"}],
  "explain": {"activity": "L_ADD_UNLIKE", "revisit": "You predicted {prediction}. 1/2 + 1/3 = 3/6 + 2/6 = 5/6 — **less than 1**."},
  "connect": ["Adding 1 rupee and 50 paise: change to paise first (100 + 50).",
              "Adding 1/2 kg of tomatoes and 1/4 kg of onions: 2/4 + 1/4 = 3/4 kg in the bag."],
  "key_learning": "Before adding, make the pieces the same size by finding a common denominator.",
 },
 "F_MULTIPLY": {
  "predict": {"prompt": "A bottle is 3/4 full. You drink half of the water in it. Will the amount you drank be more or less than 3/4 of a bottle?",
              "options": ["More than 3/4", "Less than 3/4", "Exactly 3/4"]},
  "explore": {"tool": "fraction_strips", "strips": [2, 4, 8],
              "prompt": "Build **3/4** on a strip. Now find *half of that shaded part*. Try a strip of 8 parts to see it exactly.",
              "record": "What is half of 3/4? How did you work it out?"},
  "probe": [{"kind": "observe", "prompt": "Was half of 3/4 more or less than 3/4?"},
            {"kind": "why", "prompt": "Why does multiplying by 1/2 give a *smaller* answer, when multiplying whole numbers usually gives a bigger one?"},
            {"kind": "summarise", "prompt": "In your own words: what does '1/2 × 3/4' mean, and how do you work it out?"}],
  "explain": {"activity": "L_MULTIPLY", "revisit": "You predicted {prediction}. Half of 3/4 is 3/8 — **less** than 3/4. 'Of' means multiply: 1/2 × 3/4 = 3/8."},
  "connect": ["'Half of the 3/4 kg of sugar' is used in the payasam: 3/8 kg.",
              "If 2/3 of students take the bus and half of those sit upstairs, 1/3 of all students sit upstairs."],
  "key_learning": "Multiplying by a fraction takes a part *of* an amount: multiply the tops and multiply the bottoms.",
 },
 "F_WORD": {
  "elicit": [{"prompt": "Think of a time at home or in the market when you used halves or quarters. What were you working out?"}],
  "explore": {"tool": "problem", "prompt": "Try this before any help.",
              "problem": "Meena's family buys **3/4 kg** of rice. They cook **1/3 kg** for lunch and **1/4 kg** for dinner. Is there any rice left? If yes, how much?",
              "record": "Show how you solved it. What did you do first?"},
  "probe": [{"kind": "observe", "prompt": "What was the 'whole' in Meena's problem? What were the parts?"},
            {"kind": "why", "prompt": "How did you decide whether to add, subtract or multiply?"},
            {"kind": "summarise", "prompt": "In your own words: what steps help you solve a fraction word problem?"}],
  "explain": {"activity": "L_WORD"},
  "connect": ["Sharing travel costs, splitting a field among crops, reading a recipe — all fraction problems."],
  "key_learning": "Find the whole, find the parts, then choose the operation from what the story asks.",
 },
}
for sid, ep in EP.items():
    S[sid]["episode"] = ep

# ------------------------------------------------------------------ hint ladders + misconceptions
op_re = re.compile(r"^(\d+)(?:/(\d+))? ([+\-×]) (\d+)/(\d+)")
for sid, s in S.items():
    for it in s["items"]:
        old = it.pop("hint", None)
        hints = []
        m = op_re.match(it["prompt"])
        if sid == "F_ADD_LIKE" and m:
            a, b, op, c, d = int(m[1]), int(m[2]), m[3], int(m[4]), int(m[5])
            verb = "add" if op == "+" else "take away"
            hints = [f"Picture a strip cut into {b} pieces. How many pieces do you have after you {verb}?",
                     f"Same-size pieces: {verb} the numerators only — the denominator {b} stays. Then simplify."]
            if op == "+":
                big = max(F(a, b), F(c, d))
                it["misconceptions"] = [{"id": "add_denominators", "label": "Adds the denominators",
                    "values": [fs(F(a + c, b + d))],
                    "probe": f"You wrote {{response}}. Compare it with {fs(big)}, one of the fractions you started with. Is your answer bigger or smaller? Can adding more leave you with less?"}]
            else:
                it["misconceptions"] = [{"id": "subtract_denominators", "label": "Subtracts the denominators",
                    "responses": [f"{a - c}/0"], "probe": "A denominator of 0 would mean the whole is cut into 0 pieces! What does the denominator tell you — and does taking pieces away change it?"}]
        elif sid == "F_ADD_UNLIKE" and m:
            a, b, op, c, d = int(m[1]), int(m[2]), m[3], int(m[4]), int(m[5])
            L = lcm(b, d)
            hints = [f"Are {b}ths and {d}ths the same size of piece? What size of piece could both be cut into exactly?",
                     f"Use {L}ths: {a}/{b} = ?/{L} and {c}/{d} = ?/{L}. Then {'add' if op == '+' else 'subtract'}."]
            mcs = []
            if op == "+":
                mcs.append({"id": "add_tops_and_bottoms", "label": "Adds numerators and denominators",
                            "values": [fs(F(a + c, b + d))],
                            "probe": f"You wrote {{response}}. Is that bigger than {fs(max(F(a, b), F(c, d)))}, one of the fractions you started with? Adding should give you more. What's wrong with adding pieces of different sizes?"})
            elif b != d and b - d > 0:
                mcs.append({"id": "subtract_tops_and_bottoms", "label": "Subtracts numerators and denominators",
                            "responses": [f"{a - c}/{b - d}"],
                            "probe": f"You subtracted the bottoms too. Are {b}ths and {d}ths the same size of piece? What could you do first?"})
            kept = {fs(F(a + c if op == '+' else a - c, b)), fs(F(a + c if op == '+' else a - c, d))} if (a - c) != 0 else set()
            kept.discard(fs(F(a, b) + F(c, d) if op == '+' else F(a, b) - F(c, d)))
            if kept:
                mcs.append({"id": "keeps_one_denominator", "label": "Keeps one denominator without converting",
                            "values": sorted(kept),
                            "probe": f"You added the tops but kept one bottom number. But {c}/{d} is in {d}ths, not {b}ths — can you count them together before they are the same size?"})
            it["misconceptions"] = mcs
        elif sid == "F_MULTIPLY" and m:
            a, b, op, c, d = int(m[1]), int(m[2] or 1), m[3], int(m[4]), int(m[5])
            hints = [f"Should the answer be bigger or smaller than {fs(F(a, b))}? Why?",
                     "Multiply the tops together and the bottoms together, then simplify."]
            if F(a * d, b * c) != F(a, b) * F(c, d):
                it["misconceptions"] = [{"id": "cross_multiplies", "label": "Cross-multiplies (mixes up with dividing)",
                    "values": [fs(F(a * d, b * c))],
                    "probe": "It looks like you multiplied diagonally. Think of 'half of 3/4' on a strip — which numbers get multiplied together?"}]
        elif sid == "F_EQUIV":
            a, b, d = map(int, re.match(r".*?(\d+)/(\d+) = \?/(\d+)", it["prompt"]).groups())
            hints = [f"How many times bigger is {d} than {b}? What should happen to each piece — and to the number of pieces?",
                     f"{b} × {d // b} = {d}, so multiply the top by {d // b} too."]
            it["misconceptions"] = [{"id": "additive_thinking", "label": "Adds instead of multiplies",
                "values": [str(a + d - b)],
                "probe": f"You added {d - b} to the top because {b} + {d - b} = {d}. Try a simple check: is 1/2 the same amount as 2/3 (1 added to both)? What happens on the fraction strips?"}]
        elif sid == "F_COMPARE" and it["type"] == "mcq":
            x, y = [F(o) for o in it["options"][:2]]
            wrong = it["options"][0] if x < y else it["options"][1]
            wn, wd = map(int, wrong.split("/")); rn, rd = map(int, it["answer"].split("/"))
            hints = ["Imagine both fractions on fraction strips. Which shading would reach further?",
                     "Rewrite both with the same denominator (try the LCM of the bottoms), then compare the tops."]
            mcs = [{"id": "equal_when_close", "label": "Thinks the fractions are equal", "responses": ["They are equal"],
                    "probe": "Line them up on strips. Do they end at exactly the same place? How could you check precisely?"}]
            if wn > rn:
                mcs.append({"id": "compares_numerators_only", "label": "Compares numerators only",
                            "responses": [wrong], "probe": f"{wrong} has the bigger top number — but are its pieces the same size as the pieces of {it['answer']}? Which pieces are bigger?"})
            elif wd > rd:
                mcs.append({"id": "bigger_denominator_bigger", "label": "Thinks a bigger denominator means a bigger fraction",
                            "responses": [wrong], "probe": "A bigger denominator means the whole is cut into *more* pieces. Is each piece bigger or smaller then?"})
            else:
                mcs.append({"id": "smaller_denominator_always_bigger", "label": "Thinks fewer, bigger pieces always means a bigger fraction",
                            "responses": [wrong], "probe": f"It's true that {wd}ths are bigger pieces than {rd}ths. But {wrong} has {wn} of them and {it['answer']} has {rn}. Which covers more of the strip?"})
            it["misconceptions"] = mcs
        elif sid == "F_MIXED":
            mm = re.match(r"Write (\d+)/(\d+) as a mixed", it["prompt"])
            mi = re.match(r"Write (\d+) (\d+)/(\d+) as an improper", it["prompt"])
            if mm:
                n, d = int(mm[1]), int(mm[2]); w, r = divmod(n, d)
                hints = [f"How many whole strips of {d} pieces can you fill with {n} pieces?", f"{n} ÷ {d} = {w} remainder {r}."]
                it["misconceptions"] = [{"id": "swaps_whole_and_remainder", "label": "Swaps whole number and remainder",
                    "responses": [f"{r} {w}/{d}"], "probe": f"Check: {r} whole ones would be {r * d}/{d}. Is that close to {n}/{d}? Which number counts the full strips?"}]
            elif mi:
                w, r, d = int(mi[1]), int(mi[2]), int(mi[3])
                hints = [f"How many {d}ths are in one whole? In {w} wholes?", f"{w} wholes = {w * d}/{d}. Now add the {r}/{d}."]
                it["misconceptions"] = [{"id": "adds_whole_to_numerator", "label": "Adds the whole number to the numerator",
                    "values": [fs(F(w + r, d))], "probe": f"One whole is {d}/{d}, not 1/{d}. How many {d}ths make {w} whole ones?"},
                                        {"id": "forgets_part", "label": "Forgets the fraction part",
                    "values": [fs(F(w * d, d))] if w * d != d else [], "responses": [f"{w * d}/{d}"],
                    "probe": f"That's just the {w} wholes. Where did the {r}/{d} go?"}]
        elif sid == "M_FACTORS":
            a, b = map(int, re.findall(r"\d+", it["prompt"])[:2])
            hints = [f"Which numbers divide {a} with nothing left over? Which of those also divide {b}?", old]
            it["misconceptions"] = [{"id": "gives_lcm", "label": "Gives a common multiple instead of a factor",
                "values": [str(lcm(a, b)), str(a * b)],
                "probe": f"{{response}} is a number that both {a} and {b} go *into*. The HCF must go into {a} and {b}. Can a factor be bigger than {a}?"}]
        elif sid == "M_MULTIPLES":
            a, b = map(int, re.findall(r"\d+", it["prompt"])[:2])
            hints = [f"Count up in {a}s and in {b}s. Where do the lists first meet?", old]
            if a * b != lcm(a, b):
                it["misconceptions"] = [{"id": "multiplies_instead", "label": "Multiplies the numbers (not always the lowest)",
                    "values": [str(a * b)], "probe": f"{a * b} is in both times tables — but is it the *first* one? Check the {a} times table below {a * b}."}]
            it["misconceptions"] = it.get("misconceptions", []) + [{"id": "gives_hcf", "label": "Gives a factor instead of a multiple",
                "values": [str(gcd(a, b))] if gcd(a, b) > 1 else [], "responses": [],
                "probe": f"{{response}} goes *into* {a} and {b}. We need a number that both {a} and {b} go into."}]
        elif sid == "F_MEANING" and it["type"] == "fraction":
            ans = F(it["answer"])
            hints = ["What is the whole here, and how many equal parts is it cut into?", old]
            mcs = [{"id": "flips_fraction", "label": "Writes the fraction upside down",
                    "values": [fs(F(ans.denominator, ans.numerator))] if ans.numerator else [],
                    "probe": "Which number tells how many equal pieces the whole is cut into? Should it go on top or at the bottom?"}]
            if "left" in it["prompt"]:
                mcs.append({"id": "answers_eaten_not_left", "label": "Gives the part used instead of the part left",
                            "values": [fs(1 - ans)], "probe": "That's the part that was eaten or used. Read again: what does the question ask for?"})
            it["misconceptions"] = mcs
        else:
            hints = ["What is the question really asking? What is the whole, and what are the parts?"] + ([old] if old else [])
        it["hints"] = [h for h in hints if h]
        for mc in it.get("misconceptions", []):
            mc.setdefault("values", [])
        it["misconceptions"] = [mc for mc in it.get("misconceptions", []) if mc.get("values") or mc.get("responses")]
        if not it["misconceptions"]:
            it.pop("misconceptions")

json.dump(pack, open(path, "w"), indent=2, ensure_ascii=False)
print("episodes", sum(1 for s in S.values() if "episode" in s), "/", len(S),
      "| items with misconceptions", sum(1 for s in S.values() for i in s["items"] if i.get("misconceptions")))
