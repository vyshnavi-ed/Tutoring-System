"""Builds packs/math_fractions.json with computed (verified) answers."""
import json
import sys
from fractions import Fraction as F
from math import gcd

def fs(x: F) -> str:
    return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)

def lcm(a, b): return a * b // gcd(a, b)

sets, acts = {}, {}

def add_set(sid, title, level, links, activity, items):
    for i, it in enumerate(items, 1):
        it.setdefault("id", f"{sid}.{i}")
    sets[sid] = {"title": title, "level": level, "activity": activity, "links": links, "items": items}

def frac_item(prompt, ans, hint, expl, form="simplest"):
    return {"type": "fraction", "prompt": prompt, "answer": fs(ans), "form": form, "hint": hint, "explanation": expl}

# ---------- lessons
acts["L_MEANING"] = {"title": "What a fraction means", "body":
"""A fraction describes **equal parts of a whole**.

In **3/4**, the bottom number (the **denominator**, 4) says the whole is cut into 4 equal parts. The top number (the **numerator**, 3) says we take 3 of them.

**Example:** A pizza is cut into 8 equal slices and you eat 3. You ate **3/8** of the pizza.

A fraction can be bigger than 1: **5/4** means five quarters — one whole and one more quarter."""}
acts["L_FACTORS"] = {"title": "Factors and the HCF", "body":
"""A **factor** of a number divides it exactly. Factors of 12: 1, 2, 3, 4, 6, 12.

The **Highest Common Factor (HCF)** of two numbers is the biggest number that is a factor of both.

**Example:** Factors of 12 → 1, 2, 3, 4, 6, 12. Factors of 18 → 1, 2, 3, 6, 9, 18. Common: 1, 2, 3, 6. **HCF = 6**."""}
acts["L_MULTIPLES"] = {"title": "Multiples and the LCM", "body":
"""A **multiple** of a number is in its times table. Multiples of 4: 4, 8, 12, 16, 20 …

The **Lowest Common Multiple (LCM)** is the smallest number in both times tables.

**Example:** Multiples of 4 → 4, 8, **12**, 16. Multiples of 6 → 6, **12**, 18. **LCM = 12**.

The LCM of two denominators is the best *common denominator*."""}
acts["L_EQUIV"] = {"title": "Equivalent fractions", "body":
"""Multiply (or divide) the top **and** the bottom by the same number and the fraction keeps its value.

**Example:** 2/3 = (2×4)/(3×4) = **8/12**.

To find the missing number in 3/5 = ?/20: the bottom went 5 → 20, that's ×4, so the top is 3×4 = **12**."""}
acts["L_SIMPLIFY"] = {"title": "Simplifying fractions", "body":
"""A fraction is in **simplest form** when the top and bottom have no common factor except 1.

**Method:** divide top and bottom by their **HCF**.

**Example:** 18/24. HCF of 18 and 24 is 6. 18÷6 = 3, 24÷6 = 4 → **3/4**."""}
acts["L_MIXED"] = {"title": "Mixed numbers and improper fractions", "body":
"""An **improper fraction** has top ≥ bottom, like 7/3. A **mixed number** writes it as wholes plus a fraction: **2 1/3**.

**Improper → mixed:** 7 ÷ 3 = 2 remainder 1 → 2 1/3.

**Mixed → improper:** 2 1/3 = (2×3 + 1)/3 = **7/3**."""}
acts["L_ADD_LIKE"] = {"title": "Adding & subtracting with the same denominator", "body":
"""When the denominators are the **same**, add (or subtract) the numerators and **keep the denominator**.

**Example:** 2/9 + 4/9 = (2+4)/9 = 6/9 → simplify → **2/3**.

⚠️ Never add the denominators: 2/9 + 4/9 is **not** 6/18."""}
acts["L_COMPARE"] = {"title": "Comparing fractions", "body":
"""To compare fractions, rewrite them with a **common denominator** (use the LCM), then compare the numerators.

**Example:** Which is bigger, 3/4 or 5/6? LCM(4, 6) = 12. 3/4 = 9/12 and 5/6 = 10/12. So **5/6 is bigger**.

Shortcut: with the same numerator, the smaller denominator wins (1/3 > 1/5)."""}
acts["L_ADD_UNLIKE"] = {"title": "Adding & subtracting with different denominators", "body":
"""1. Find a **common denominator** — the LCM of the denominators.
2. Rewrite each fraction as an **equivalent fraction** with that denominator.
3. Add or subtract the numerators.
4. **Simplify**.

**Example:** 1/4 + 1/6. LCM(4, 6) = 12. 1/4 = 3/12, 1/6 = 2/12. 3/12 + 2/12 = **5/12**."""}
acts["L_MULTIPLY"] = {"title": "Multiplying fractions", "body":
"""Multiply the tops, multiply the bottoms, then simplify.

**Example:** 2/3 × 3/4 = (2×3)/(3×4) = 6/12 = **1/2**.

A whole number is a fraction over 1: 3 × 2/5 = 3/1 × 2/5 = **6/5**."""}
acts["L_WORD"] = {"title": "Fraction word problems", "body":
"""1. Read carefully: what is the **whole**? What are the **parts**?
2. Decide the operation: *together / in total* → add; *left / how much more* → subtract; *of* → multiply.
3. Solve and **simplify**, then check the answer makes sense.

**Example:** Riya drank 1/3 of a bottle in the morning and 1/4 in the evening. How much did she drink? 1/3 + 1/4 = 4/12 + 3/12 = **7/12** of the bottle."""}

# ---------- skills
add_set("F_MEANING", "What a fraction means", "Understand", [], "L_MEANING", [
    frac_item("A cake is cut into 8 equal pieces. You eat 3 pieces. What fraction of the cake did you eat?", F(3, 8),
              "Bottom number = how many equal pieces in total.", "3 out of 8 equal pieces = 3/8."),
    frac_item("A chocolate bar has 10 equal squares. Ravi eats 7. What fraction is left?", F(3, 10),
              "First find how many squares are left.", "10 − 7 = 3 squares left out of 10 → 3/10."),
    {"type": "mcq", "prompt": "In the fraction 5/9, what does the 9 tell you?",
     "options": ["The whole is split into 9 equal parts", "We take 9 parts", "There are 9 wholes", "Nothing — it's just a label"],
     "answer": "The whole is split into 9 equal parts", "hint": "The denominator is the bottom number."},
    frac_item("A class has 12 students and 5 of them are girls. What fraction of the class are girls?", F(5, 12),
              "Part over whole.", "5 girls out of 12 students → 5/12."),
    {"type": "mcq", "prompt": "Which fraction is equal to one whole?",
     "options": ["4/4", "1/4", "4/1", "0/4"], "answer": "4/4", "hint": "Taking all the parts gives the whole."},
    frac_item("A rope is cut into 6 equal pieces. 2 pieces are used. What fraction of the rope is used? (simplest form)", F(1, 3),
              "Write 2/6, then simplify.", "2/6 = 1/3."),
])

hcf_pairs = [(12, 18), (8, 20), (15, 25), (14, 21), (16, 24), (9, 27)]
add_set("M_FACTORS", "Factors and HCF", "Remember", [], "L_FACTORS", [
    {"type": "numeric", "prompt": f"What is the HCF of {a} and {b}?", "answer": gcd(a, b),
     "hint": "List the factors of each number and find the biggest one they share.",
     "explanation": f"The biggest number dividing both {a} and {b} is {gcd(a, b)}."} for a, b in hcf_pairs])

lcm_pairs = [(4, 6), (3, 5), (6, 8), (2, 7), (4, 10), (6, 9)]
add_set("M_MULTIPLES", "Multiples and LCM", "Remember", [], "L_MULTIPLES", [
    {"type": "numeric", "prompt": f"What is the LCM of {a} and {b}?", "answer": lcm(a, b),
     "hint": f"Write out the {a} times table and the {b} times table and find the first number in both.",
     "explanation": f"The smallest number in both times tables is {lcm(a, b)}."} for a, b in lcm_pairs])

eq = [(2, 3, 12), (3, 5, 20), (1, 4, 12), (5, 6, 18), (3, 7, 21), (4, 9, 27)]
add_set("F_EQUIV", "Equivalent fractions", "Apply", ["F_MEANING"], "L_EQUIV", [
    {"type": "numeric", "prompt": f"Fill in the missing number: {a}/{b} = ?/{d}", "answer": a * d // b,
     "hint": f"What do you multiply {b} by to get {d}? Do the same to the top.",
     "explanation": f"{b} × {d // b} = {d}, so {a} × {d // b} = {a * d // b}."} for a, b, d in eq])

simp = [(18, 24), (10, 15), (12, 16), (14, 35), (20, 28), (9, 12)]
add_set("F_SIMPLIFY", "Simplifying fractions", "Apply", ["F_EQUIV", "M_FACTORS"], "L_SIMPLIFY", [
    frac_item(f"Write {a}/{b} in simplest form.", F(a, b), "Divide top and bottom by their HCF.",
              f"HCF({a}, {b}) = {gcd(a, b)}. {a}÷{gcd(a, b)} = {a // gcd(a, b)}, {b}÷{gcd(a, b)} = {b // gcd(a, b)} → {fs(F(a, b))}.")
    for a, b in simp])

mixed_items = []
for n, d in [(7, 3), (11, 4), (9, 2)]:
    w, r = divmod(n, d)
    mixed_items.append({"type": "text", "prompt": f"Write {n}/{d} as a mixed number (e.g. 2 1/3).",
                        "answer": f"{w} {r}/{d}", "accepted": [f"{w} {r}/{d}"],
                        "hint": f"How many times does {d} go into {n}, and what is left over?",
                        "explanation": f"{n} ÷ {d} = {w} remainder {r} → {w} {r}/{d}."})
for w, r, d in [(2, 3, 5), (1, 5, 6), (3, 1, 4)]:
    mixed_items.append(frac_item(f"Write {w} {r}/{d} as an improper fraction.", F(w * d + r, d),
                                 "Multiply the whole number by the denominator, then add the numerator.",
                                 f"({w}×{d} + {r})/{d} = {w * d + r}/{d}.", form="improper"))
add_set("F_MIXED", "Mixed numbers and improper fractions", "Apply", ["F_MEANING"], "L_MIXED", mixed_items)

like = [((2, 9), (4, 9), "+"), ((3, 8), (1, 8), "+"), ((7, 10), (3, 10), "-"), ((5, 12), (1, 12), "+"),
        ((9, 14), (2, 14), "-"), ((1, 6), (3, 6), "+")]
items = []
for (a, b), (c, d), op in like:
    ans = F(a, b) + F(c, d) if op == "+" else F(a, b) - F(c, d)
    raw = a + c if op == "+" else a - c
    items.append(frac_item(f"{a}/{b} {op} {c}/{d} = ?  (simplest form)", ans,
                           "Same denominator: work with the numerators only and keep the denominator.",
                           f"{a} {op} {c} = {raw}, so {raw}/{b}" + (f" = {fs(ans)}." if F(raw, b).denominator != b else ".")))
add_set("F_ADD_LIKE", "Add & subtract: same denominator", "Apply", ["F_MEANING", "F_SIMPLIFY"], "L_ADD_LIKE", items)

cmp = [((3, 4), (5, 6)), ((2, 3), (3, 5)), ((5, 8), (7, 12)), ((4, 9), (1, 2)), ((3, 10), (2, 7))]
items = []
for (a, b), (c, d) in cmp:
    x, y = F(a, b), F(c, d)
    big = f"{a}/{b}" if x > y else f"{c}/{d}"
    L = lcm(b, d)
    items.append({"type": "mcq", "prompt": f"Which is bigger: {a}/{b} or {c}/{d}?",
                  "options": [f"{a}/{b}", f"{c}/{d}", "They are equal"], "answer": big,
                  "hint": "Rewrite both with a common denominator (the LCM of the bottoms).",
                  "explanation": f"LCM({b}, {d}) = {L}: {a}/{b} = {a * L // b}/{L}, {c}/{d} = {c * L // d}/{L}. So {big} is bigger."})
items.append({"type": "free_text", "prompt": "Explain how you would decide which is bigger: 2/3 or 3/4.",
              "rubric": "Full marks if the student converts to a common denominator (e.g. 8/12 vs 9/12) or uses decimals/cross-multiplication correctly and concludes 3/4 is bigger. Partial if method right but conclusion missing.",
              "keywords": ["denominator", "12", "common", "bigger", "larger", "3/4"], "min_words": 8,
              "hint": "Talk about a common denominator."})
add_set("F_COMPARE", "Comparing fractions", "Analyze", ["F_EQUIV", "M_MULTIPLES"], "L_COMPARE", items)

unlike = [((1, 4), (1, 6), "+"), ((2, 3), (1, 5), "+"), ((3, 4), (1, 6), "-"), ((5, 6), (1, 4), "-"),
          ((1, 2), (2, 7), "+"), ((7, 8), (1, 3), "-")]
items = []
for (a, b), (c, d), op in unlike:
    L = lcm(b, d)
    ans = F(a, b) + F(c, d) if op == "+" else F(a, b) - F(c, d)
    items.append(frac_item(f"{a}/{b} {op} {c}/{d} = ?  (simplest form)", ans,
                           f"Find the LCM of {b} and {d} first, and rewrite both fractions.",
                           f"LCM({b}, {d}) = {L}. {a}/{b} = {a * L // b}/{L}, {c}/{d} = {c * L // d}/{L}. "
                           f"{a * L // b} {op} {c * L // d} = {a * L // b + c * L // d if op == '+' else a * L // b - c * L // d} → {fs(ans)}."))
add_set("F_ADD_UNLIKE", "Add & subtract: different denominators", "Apply",
        ["F_ADD_LIKE", "F_EQUIV", "M_MULTIPLES"], "L_ADD_UNLIKE", items)

mul = [((2, 3), (3, 4)), ((1, 2), (4, 5)), ((3, 5), (5, 6)), ((4, 7), (1, 2)), ((3, 1), (2, 9)), ((5, 8), (2, 5))]
items = []
for (a, b), (c, d) in mul:
    left = f"{a}" if b == 1 else f"{a}/{b}"
    ans = F(a, b) * F(c, d)
    items.append(frac_item(f"{left} × {c}/{d} = ?  (simplest form)", ans,
                           "Multiply top × top and bottom × bottom, then simplify.",
                           f"({a}×{c})/({b}×{d}) = {a * c}/{b * d} → {fs(ans)}."))
add_set("F_MULTIPLY", "Multiplying fractions", "Apply", ["F_SIMPLIFY"], "L_MULTIPLY", items)

word = [
    ("Riya drank 1/3 of a bottle of water in the morning and 1/4 in the evening. What fraction of the bottle did she drink altogether?", F(1, 3) + F(1, 4), "'Altogether' means add."),
    ("A ribbon is 3/4 m long. Asha cuts off 1/3 m. How long is the ribbon now (in m)?", F(3, 4) - F(1, 3), "'Cuts off' means subtract."),
    ("2/5 of the 30 students in a class walk to school. How many students walk? (whole number)", F(2, 5) * 30, "'of' means multiply."),
    ("A farmer plants rice on 1/2 of his field and wheat on 1/3. What fraction of the field is left for vegetables?", 1 - F(1, 2) - F(1, 3), "The whole field is 1. Subtract both parts."),
    ("Each glass holds 2/3 of a cup of milk. How many cups are needed to fill 6 glasses?", F(2, 3) * 6, "Multiply the amount per glass by the number of glasses."),
]
items = [frac_item(p, a, h, f"Answer: {fs(a)}.") for p, a, h in word]
items.append({"type": "free_text", "prompt": "Make up your own short word problem where you would ADD two fractions with different denominators, and solve it.",
              "rubric": "Full marks if the problem genuinely requires adding two fractions with different denominators and the solution (with common denominator) is correct.",
              "keywords": ["/"], "min_words": 15, "hint": "Think of sharing food or pouring water."})
add_set("F_WORD", "Fraction word problems", "Apply", ["F_ADD_UNLIKE", "F_MULTIPLY"], "L_WORD", items)

pack = {
    "id": "math_fractions",
    "title": "Fractions",
    "subject": "Mathematics (Class 5–6)",
    "strategy": "prereq_graph",
    "status": "approved",
    "description": "Diagnoses gaps by probing prerequisite skills (equivalent fractions, LCM, HCF…) whenever a student gets something wrong.",
    "config": {"mastery_threshold": 0.95, "p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2,
               "alert_after_failures": 3, "reveal_answer_on_fail": True},
    "activities": acts,
    "item_sets": sets,
    "units": [{"id": "fractions", "title": "Working with fractions",
               "sets": ["F_ADD_LIKE", "F_COMPARE", "F_ADD_UNLIKE", "F_MULTIPLY", "F_MIXED", "F_WORD"]}],
}
json.dump(pack, open(sys.argv[1], "w"), indent=2, ensure_ascii=False)
print("sets", len(sets), "items", sum(len(s["items"]) for s in sets.values()))
