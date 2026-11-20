"""Builds packs/ds_linked_lists.json — UOS1.2 from the thesis (singly-linked part), level descent."""
import json
import sys

PREAMBLE = '''class Node:
    def __init__(self, data, next=None):
        self.data = data
        self.next = next

def from_list(values):
    head = None
    for v in reversed(values):
        head = Node(v, head)
    return head

def to_list(head):
    out = []
    while head is not None:
        out.append(head.data)
        head = head.next
    return out
'''

def code(iid, prompt, starter, tests, solution, hint):
    return {"id": iid, "type": "code_python", "prompt": prompt, "preamble": PREAMBLE, "starter": starter,
            "tests": tests, "solution": solution, "hint": hint}

def mcq(iid, prompt, options, answer, hint="", expl=""):
    d = {"id": iid, "type": "mcq", "prompt": prompt, "options": options, "answer": answer}
    if hint: d["hint"] = hint
    if expl: d["explanation"] = expl
    return d

NOTE = "\n\nA `Node` class (`data`, `next`) and helpers `from_list([...])` / `to_list(head)` are already defined."

END_SOL = '''def insert_at_end(head, data):
    new = Node(data)
    if head is None:
        return new
    cur = head
    while cur.next is not None:
        cur = cur.next
    cur.next = new
    return head
'''
BEG_SOL = '''def insert_at_beginning(head, data):
    return Node(data, head)
'''
POS_SOL = '''def insert_at_position(head, data, pos):
    if pos == 1 or head is None:
        return Node(data, head)
    cur = head
    for _ in range(pos - 2):
        if cur.next is None:
            break
        cur = cur.next
    cur.next = Node(data, cur.next)
    return head
'''
end_tests = ["assert to_list(insert_at_end(from_list([1, 2, 3]), 4)) == [1, 2, 3, 4]",
             "assert to_list(insert_at_end(None, 7)) == [7]",
             "assert to_list(insert_at_end(from_list([5]), 9)) == [5, 9]"]
beg_tests = ["assert to_list(insert_at_beginning(None, 1)) == [1]",
             "assert to_list(insert_at_beginning(from_list([2, 3]), 1)) == [1, 2, 3]",
             "h = insert_at_beginning(None, 1); assert h.next is None"]
pos_tests = ["assert to_list(insert_at_position(from_list([1, 2, 3]), 4, 2)) == [1, 4, 2, 3]",
             "assert to_list(insert_at_position(from_list([1, 2, 3]), 0, 1)) == [0, 1, 2, 3]",
             "assert to_list(insert_at_position(from_list([1, 2]), 3, 3)) == [1, 2, 3]",
             "assert to_list(insert_at_position(None, 5, 1)) == [5]"]

sets = {}
U_LINKS = ["A1.2.U.1", "A1.2.U.2", "A1.2.U.3", "A1.2.U.4"]
R_LINKS = ["A1.2.R.1", "A1.2.R.2", "A1.2.R.3", "A1.2.R.4"]

sets["A1.2.Ap.1"] = {"title": "Insert a node at the end of a singly-linked list", "level": "Apply",
    "activity": "IA1.2.Ap", "links": U_LINKS, "items": [
    code("Ap1.a", "Write `insert_at_end(head, data)` that adds a node with `data` at the end of the list and returns the head. "
         "Example: 1 → 2 → 3, insert 4 → 1 → 2 → 3 → 4." + NOTE,
         "def insert_at_end(head, data):\n    # your code here\n    pass\n", end_tests, END_SOL,
         "Walk to the node whose next is None, then attach the new node there. Don't forget the empty list."),
    code("Ap1.b", "Write `insert_at_end(head, data)` for a singly-linked list. If the list is empty, the new node becomes the head. "
         "Example: 5 → 9, insert 2 → 5 → 9 → 2." + NOTE,
         "def insert_at_end(head, data):\n    pass\n", end_tests, END_SOL,
         "Use a loop: while cur.next is not None: cur = cur.next"),
]}
sets["A1.2.Ap.2"] = {"title": "Insert a node at the beginning of a (new) singly-linked list", "level": "Apply",
    "activity": "IA1.2.Ap", "links": U_LINKS, "items": [
    code("Ap2.a", "Write `insert_at_beginning(head, data)` that inserts `data` at the front and returns the new head. "
         "Example: insert 1 into an empty list → 1." + NOTE,
         "def insert_at_beginning(head, data):\n    pass\n", beg_tests, BEG_SOL,
         "The new node's next should be the old head."),
    code("Ap2.b", "Write `insert_at_beginning(head, data)`. Example: 2 → 3, insert 1 → 1 → 2 → 3." + NOTE,
         "def insert_at_beginning(head, data):\n    pass\n", beg_tests, BEG_SOL,
         "Create Node(data) and point it at the current head; return the new node."),
]}
sets["A1.2.Ap.3"] = {"title": "Insert a node at a given position of a singly-linked list", "level": "Apply",
    "activity": "IA1.2.Ap", "links": U_LINKS, "items": [
    code("Ap3.a", "Write `insert_at_position(head, data, pos)` (positions start at 1) and return the head. "
         "Example: insert 4 at position 2 of 1 → 2 → 3 → 1 → 4 → 2 → 3." + NOTE,
         "def insert_at_position(head, data, pos):\n    pass\n", pos_tests, POS_SOL,
         "Stop at the node *before* the position, then link: new.next = cur.next; cur.next = new. Position 1 is a special case."),
    code("Ap3.b", "Write `insert_at_position(head, data, pos)`; position 1 means the new node becomes the head. "
         "Example: insert 0 at position 1 of 1 → 2 → 3 → 0 → 1 → 2 → 3." + NOTE,
         "def insert_at_position(head, data, pos):\n    pass\n", pos_tests, POS_SOL,
         "Move pos − 2 steps from the head to reach the node before the insertion point."),
]}

SLL = ["1 → 2 → 3 → 4", "4 → 1 → 2 → 3", "1 → 2 → 3", "1 → 2 → 4 → 3"]
sets["A1.2.U.1"] = {"title": "Result of inserting at the end", "level": "Understand", "activity": "IA1.2.U",
    "links": R_LINKS, "items": [
    mcq("U1.a", "What will the list 1 → 2 → 3 look like after inserting the node 4 at the end?", SLL, "1 → 2 → 3 → 4"),
    mcq("U1.b", "The list is 7 → 8. After inserting 9 at the end, the list is:", ["7 → 8 → 9", "9 → 7 → 8", "7 → 9 → 8", "7 → 8"], "7 → 8 → 9"),
]}
sets["A1.2.U.2"] = {"title": "What the new last node points to", "level": "Understand", "activity": "IA1.2.U",
    "links": R_LINKS, "items": [
    mcq("U2.a", "After inserting a node at the end of 1 → 2 → 3, what does the new node point to?",
        ["None (NULL)", "The head (node 1)", "Node 3", "Itself"], "None (NULL)"),
    mcq("U2.b", "After inserting at the end, which node's `next` changes from None to the new node?",
        ["The old last node", "The head", "The new node", "No node changes"], "The old last node"),
]}
sets["A1.2.U.3"] = {"title": "Inserting at a position (not the end)", "level": "Understand", "activity": "IA1.2.U",
    "links": R_LINKS, "items": [
    mcq("U3.a", "After inserting 4 at the 2nd position of 1 → 2 → 3, what does the new node point to?",
        ["Node 2", "Node 1", "None (NULL)", "Node 3"], "Node 2"),
    mcq("U3.b", "After inserting 4 at the 2nd position of 1 → 2 → 3, what does node 1 point to?",
        ["The new node (4)", "Node 2", "None (NULL)", "Node 3"], "The new node (4)"),
]}
sets["A1.2.U.4"] = {"title": "Inserting into an empty list", "level": "Understand", "activity": "IA1.2.U",
    "links": R_LINKS, "items": [
    mcq("U4.a", "After inserting a node containing 3 into an empty singly-linked list, what does the new node point to?",
        ["None (NULL)", "Itself", "The head", "Node 3"], "None (NULL)"),
    mcq("U4.b", "After inserting the first node into an empty list, what is the head?",
        ["The new node", "None (NULL)", "Undefined", "A dummy node"], "The new node"),
]}
sets["A1.2.R.1"] = {"title": "Number of links in a singly-linked node", "level": "Remember", "activity": "IA1.2.R",
    "links": [], "items": [
    mcq("R1.a", "How many links (pointers to other nodes) does each node of a singly-linked list have?", ["1", "2", "0", "3"], "1"),
    mcq("R1.b", "A singly-linked list node stores data and how many references to other nodes?", ["One", "Two", "None", "As many as needed"], "One"),
]}
sets["A1.2.R.2"] = {"title": "Prev link in a singly-linked list", "level": "Remember", "activity": "IA1.2.R",
    "links": [], "items": [
    mcq("R2.a", "Does a node of a singly-linked list have a `prev` link?", ["No", "Yes"], "No"),
    mcq("R2.b", "Which kind of linked list has a `prev` link in every node?", ["Doubly-linked", "Singly-linked", "Neither"], "Doubly-linked"),
]}
sets["A1.2.R.3"] = {"title": "Next link in a singly-linked list", "level": "Remember", "activity": "IA1.2.R",
    "links": [], "items": [
    mcq("R3.a", "Does a node of a singly-linked list have a `next` link?", ["Yes", "No"], "Yes"),
    mcq("R3.b", "In a singly-linked list, the `next` field of a node refers to:", ["The following node", "The previous node", "The head", "The data"], "The following node"),
]}
sets["A1.2.R.4"] = {"title": "The NULL / None link", "level": "Remember", "activity": "IA1.2.R",
    "links": [], "items": [
    mcq("R4.a", "In a singly-linked list, which node's `next` is None (NULL)?", ["The last node", "The head", "Every node", "No node"], "The last node"),
    mcq("R4.b", "Does a (non-circular) singly-linked list have a node that points to None (NULL)?", ["Yes", "No"], "Yes"),
]}

acts = {
    "IA1.2.Ap": {"title": "IA1.2.Ap — Inserting nodes into a singly-linked list (Apply)", "body":
"""Each node has `data` and `next`. The list is reached through `head`.

**At the beginning:** `new = Node(data, head)` → the new node *is* the new head.

**At the end:** walk until `cur.next is None`, then `cur.next = Node(data)`. If the list is empty, the new node is the head.

**At position p (1-based):** walk to the node *before* p (p − 2 steps from head), then
```
new = Node(data, cur.next)
cur.next = new
```
Position 1 is the same as inserting at the beginning."""},
    "IA1.2.U": {"title": "IA1.2.U — What changes when you insert (Understand)", "body":
"""Compare the three insertions on 1 → 2 → 3:

- **End (insert 4):** 1 → 2 → 3 → 4. Node 3's `next` changes from None to 4; node 4's `next` is None.
- **Beginning (insert 0):** 0 → 1 → 2 → 3. Node 0's `next` is the old head (1); `head` now refers to 0.
- **Position 2 (insert 4):** 1 → 4 → 2 → 3. Node 1's `next` becomes 4; node 4's `next` is 2.
- **Empty list (insert 3):** head → 3, and node 3's `next` is None."""},
    "IA1.2.R": {"title": "IA1.2.R — Structure of a singly-linked node (Remember)", "body":
"""Memorise these facts:

- A singly-linked node has **data** and **one link: `next`**.
- It has **no `prev` link** (that's a doubly-linked list).
- `next` refers to the **following node**.
- The **last node's `next` is None (NULL)**. That's how you know the list has ended."""},
}

pack = {
    "id": "ds_linked_lists",
    "title": "Linked Lists — UOS1.2 (from the thesis)",
    "subject": "Data Structures (B.Tech)",
    "strategy": "level_descent",
    "status": "approved",
    "description": "The original tutoring rules from Ramesh (2014): fail an Apply item → Understand items pre-selected for it → Remember items → back up with a different item.",
    "config": {"alert_after_failures": 3, "reveal_answer_on_fail": False},
    "activities": acts, "item_sets": sets,
    "units": [{"id": "UOS1.2", "title": "Construct and traverse singly-linked lists", "activity": "IA1.2.Ap",
               "sets": ["A1.2.Ap.1", "A1.2.Ap.2", "A1.2.Ap.3"]}],
}
json.dump(pack, open(sys.argv[1], "w"), indent=2, ensure_ascii=False)
print("sets", len(sets))
