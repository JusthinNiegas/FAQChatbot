"""
PUP Parañaque IT FAQ Chatbot  (Rule-Based AI, Taglish-ready)
-----------------------------------------------------------
Pipeline:  question -> preprocessing -> clean/normalize -> keyword & pattern
           matching -> rule-based decision engine -> answer or fallback

Run the GUI :  python chatbot.py
Run in text :  python chatbot.py --cli
Run tests   :  python chatbot.py --test
"""
import json
import os
import re
import sys
import csv
import difflib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "knowledge_base.json")
LOG_PATH = os.path.join(BASE_DIR, "chat_log.csv")


class FAQEngine:
    """Rule-based engine. All rules live in knowledge_base.json."""

    def __init__(self, kb_path=KB_PATH):
        self.kb_path = kb_path
        self.load()

    # ---------- knowledge base ----------
    def load(self):
        with open(self.kb_path, encoding="utf-8") as f:
            self.kb = json.load(f)
        self.stopwords = set(self.kb["stopwords"])
        self.entries = self.kb["entries"]
        self.phrases = {self._clean(k): v for k, v in self.kb["phrases"].items()}
        self.word_to_canon = {}
        for canon, words in self.kb["synonyms"].items():
            self.word_to_canon[canon] = canon
            for w in words:
                w = self._clean(w)
                if " " in w:                      # multi-word synonym -> phrase rule
                    self.phrases[w] = canon
                else:
                    self.word_to_canon[w] = canon
        # longest phrases first so "good morning" beats "good"
        self.phrase_list = sorted(self.phrases, key=len, reverse=True)
        self.vocab = list(self.word_to_canon)

    @staticmethod
    def _clean(text):
        text = text.lower().replace("-", " ").replace("_", " ")
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    # ---------- pipeline steps ----------
    def preprocess(self, question):
        """Step 1-2: lowercase, remove punctuation, normalize."""
        return self._clean(question)

    def tokenize(self, text):
        """Step 3: apply phrase rules, split, drop stopwords, map synonyms
        (Tagalog/English/Taglish -> canonical keyword), tolerate typos."""
        padded = f" {text} "
        for phrase in self.phrase_list:
            if f" {phrase} " in padded:
                padded = padded.replace(f" {phrase} ", f" {self.phrases[phrase]} ")
        tokens = set()
        for w in padded.split():
            if w in self.stopwords:
                continue
            if w in self.word_to_canon:
                tokens.add(self.word_to_canon[w])
            elif len(w) >= 4:                      # typo tolerance
                m = difflib.get_close_matches(w, self.vocab, n=1, cutoff=0.82)
                if m:
                    tokens.add(self.word_to_canon[m[0]])
        return tokens

    def match(self, tokens):
        """Step 4-5: pattern matching + decision rule.
        An entry matches when ALL keywords of one of its patterns are present.
        The most specific pattern (most keywords) wins."""
        best, best_score = None, 0
        for e in self.entries:
            for pat in e["patterns"]:
                if set(pat) <= tokens and len(pat) > best_score:
                    best, best_score = e, len(pat)
        return best

    def fallback(self, tokens):
        offices = self.kb["fallback_offices"]
        office = offices["default"]
        for key in ("enroll", "grade", "subject", "office"):
            if key in tokens:
                office = offices[key]
                break
        return self.kb["fallback"].format(office=office)

    def ask(self, question):
        """Returns (answer, matched_entry_id or None)."""
        if not question.strip():
            return "Pakisulat po ang inyong tanong. 🙂", None
        tokens = self.tokenize(self.preprocess(question))
        entry = self.match(tokens)
        if entry:
            return entry["answer"], entry["id"]
        return self.fallback(tokens), None

    # ---------- maintenance ----------
    def unverified(self):
        return [e["id"] for e in self.entries if not e.get("verified", False)]

    def categories(self):
        return sorted({e["category"] for e in self.entries if e["category"] != "General"})


def log_chat(question, answer, entry_id):
    new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "question", "matched_entry", "answer"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), question,
                    entry_id or "FALLBACK", answer.replace("\n", " | ")])


# ---------------------------------------------------------------- tests
TEST_CASES = [
    ("Paano mag-enroll?", "enroll_how"),
    ("how to enroll po", "enroll_how"),
    ("ano ang process ng enrollment", "enroll_how"),
    ("Kailan ang deadline ng enrollment?", "enroll_when"),
    ("kelan po ang enrollment", "enroll_when"),
    ("Ano ang requirements sa enrollment?", "enroll_req"),
    ("nahuli ako mag enroll, pwede pa ba?", "enroll_late"),
    ("Magkano ang tuition?", "tuition"),
    ("ano prerequisite ng programming 2", "prereq_prog"),
    ("prereq ng database?", "prereq_db"),
    ("what is the prerequisite of networking", "prereq_net"),
    ("ano po ang prerequisite", "prereq"),
    ("Saan makikita ang curriculum checklist?", "curriculum"),
    ("Ano ang passing grade?", "grade_pass"),
    ("pumasa ba ako kapag 3.00", "grade_pass"),
    ("paano i-compute ang GWA", "grade_compute"),
    ("ano ang grading system ng PUP", "grade_scale"),
    ("ano ang ibig sabihin ng INC?", "inc"),
    ("paano mag-drop ng subject", "drop"),
    ("anong oras bukas ang registrar", "office_registrar"),
    ("nasaan ang opisina ng dean", "office_dean"),
    ("office hours ng program chair", "office_chair"),
    ("kailan ang consultation ng prof?", "consult"),
    ("what time is the office open", "office_hours"),
    ("hello po", "greet"),
    ("Good morning!", "greet"),
    ("salamat po", "thanks"),
    ("what can you do", "help"),
    ("Magkano ang bayad sa parking?", "tuition"),  # known weakness
    ("ano ang pinakamagandang pizza", None),
    ("asdfgh qwerty", None),
    ("", None),
]


def run_tests(engine):
    ok = 0
    for q, expected in TEST_CASES:
        _, got = engine.ask(q)
        passed = got == expected
        ok += passed
        print(f"[{'PASS' if passed else 'FAIL'}] {q!r:55} expected={expected} got={got}")
    print(f"\nResponse accuracy: {ok}/{len(TEST_CASES)} = {ok/len(TEST_CASES)*100:.1f}%")


# ---------------------------------------------------------------- CLI
def run_cli(engine):
    print("PUP Parañaque IT FAQ Bot  (type 'exit' para umalis)\n")
    while True:
        try:
            q = input("Ikaw: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit", "bye"):
            print("Bot: Paalam po!")
            break
        a, eid = engine.ask(q)
        log_chat(q, a, eid)
        print(f"Bot: {a}\n")


# ---------------------------------------------------------------- GUI
def run_gui(engine):
    import tkinter as tk
    from tkinter import scrolledtext, messagebox

    NAVY, MAROON, LIGHT = "#0b2a5b", "#800000", "#f3f5fa"
    root = tk.Tk()
    root.title("PUP Parañaque IT FAQ Chatbot")
    root.geometry("620x700")
    root.configure(bg=LIGHT)

    header = tk.Label(root, text="PUP Parañaque IT FAQ Chatbot", bg=MAROON, fg="white",
                      font=("Segoe UI", 15, "bold"), pady=10)
    header.pack(fill="x")
    sub = tk.Label(root, text="Magtanong sa Tagalog, English, o Taglish!", bg=MAROON, fg="#f5d76e",
                   font=("Segoe UI", 9), pady=2)
    sub.pack(fill="x")

    chat = scrolledtext.ScrolledText(root, wrap="word", state="disabled", font=("Segoe UI", 10),
                                     bg="white", relief="flat", padx=10, pady=10)
    chat.pack(fill="both", expand=True, padx=10, pady=(10, 5))
    chat.tag_config("user", foreground=NAVY, font=("Segoe UI", 10, "bold"), spacing1=8)
    chat.tag_config("bot", foreground="#222222", spacing3=4)
    chat.tag_config("who_bot", foreground=MAROON, font=("Segoe UI", 10, "bold"), spacing1=8)

    def say(who, text):
        chat.config(state="normal")
        if who == "user":
            chat.insert("end", "Ikaw:\n", "user")
            chat.insert("end", text + "\n", "bot")
        else:
            chat.insert("end", "FAQ Bot:\n", "who_bot")
            chat.insert("end", text + "\n", "bot")
        chat.config(state="disabled")
        chat.see("end")

    def send(event=None, text=None):
        q = (text or entry.get()).strip()
        if not q:
            return
        entry.delete(0, "end")
        say("user", q)
        a, eid = engine.ask(q)
        log_chat(q, a, eid)
        say("bot", a)

    # quick topic buttons
    topics = tk.Frame(root, bg=LIGHT)
    topics.pack(fill="x", padx=10)
    samples = {"Enrollment": "Paano mag-enroll?", "Prerequisites": "Ano ang prerequisite?",
               "Grading": "Ano ang passing grade?", "Office hours": "Anong oras bukas ang office?",
               "Help": "help"}
    for label, q in samples.items():
        tk.Button(topics, text=label, command=lambda q=q: send(text=q), bg="white", fg=NAVY,
                  relief="groove", padx=6).pack(side="left", padx=2, pady=2)

    bottom = tk.Frame(root, bg=LIGHT)
    bottom.pack(fill="x", padx=10, pady=10)
    entry = tk.Entry(bottom, font=("Segoe UI", 11))
    entry.pack(side="left", fill="x", expand=True, ipady=6)
    entry.bind("<Return>", send)
    tk.Button(bottom, text="Send", command=send, bg=MAROON, fg="white", padx=14,
              font=("Segoe UI", 10, "bold")).pack(side="left", padx=(6, 0))

    def clear():
        chat.config(state="normal"); chat.delete("1.0", "end"); chat.config(state="disabled")
        say("bot", "Chat cleared. Ano pong maitutulong ko?")

    def reload_kb():
        try:
            engine.load()
            messagebox.showinfo("Knowledge Base", f"Na-reload po ang FAQ: {len(engine.entries)} entries.")
        except Exception as e:
            messagebox.showerror("Error", f"May mali sa knowledge_base.json:\n{e}")

    menu = tk.Menu(root)
    admin = tk.Menu(menu, tearoff=0)
    admin.add_command(label="Reload knowledge base", command=reload_kb)
    admin.add_command(label="Clear chat", command=clear)
    menu.add_cascade(label="Options", menu=admin)
    root.config(menu=menu)

    say("bot", "Hello po! 👋 Ako ang FAQ Bot ng IT Department ng PUP Parañaque. "
               "Magtanong po tungkol sa enrollment, prerequisites, grading, o office schedules.")
    entry.focus()
    root.mainloop()


if __name__ == "__main__":
    eng = FAQEngine()
    if "--test" in sys.argv:
        run_tests(eng)
    elif "--cli" in sys.argv:
        run_cli(eng)
    else:
        try:
            run_gui(eng)
        except Exception as ex:      # no display / no tkinter
            print("GUI unavailable (", ex, ") - starting text mode.")
            run_cli(eng)
