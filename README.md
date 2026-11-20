# TypoPilot

> **An Intelligent Desktop-Based NLP Assistant for Real-Time Word and Sentence Correction on Windows.**

TypoPilot is a lightweight, background-running Windows desktop assistant designed to intelligently correct typos and grammatical errors across ordinary applications (Microsoft Word, Notepad, Google Chrome, WhatsApp Desktop, etc.).

Unlike traditional aggressive autocorrect systems, TypoPilot **never replaces text automatically** while you type. Correction is triggered strictly on your explicit command via global keyboard shortcuts, allowing you to cycle through alternative candidates forward and backward or restore the original text with a single key.

---

## Key Features

* **Cursor-Aware Word Correction (`F2`):**
  * Automatically identifies the word immediately before or at the cursor, even if you typed an entire paragraph and moved the cursor backwards.
  * Preserves punctuation, capitalization (Title Case, UPPERCASE, lowercase), and surrounding spacing.
* **Two-Way Prediction Cycling:**
  * **Next Candidate (`F2`):** Cycles forward to the next ranked NLP candidate.
  * **Previous Candidate (`Shift+F2`):** Cycles backward so you never lose a candidate if you cycle past it.
  * **Restore Original (`Esc`):** Instantly cancels cycling and restores your original misspelled word.
* **Sentence & Paragraph Grammar Correction (`Ctrl+F2`):**
  * Highlight any sentence or paragraph and press `Ctrl+F2`.
  * Fixes subject-verb agreement (`He go` &rarr; `He goes`, `They was` &rarr; `They were`, `I has` &rarr; `I have`, `She don't` &rarr; `She doesn't`), spelling mistakes, coordination, and sentence boundary casing.
* **Dual-Mode NLP Engine (CPU & GPU Ready):**
  * **Local Offline Engine:** Runs with zero latency on any typical laptop with < 35 MB RAM.
  * **Neural Transformer Adapter:** Ready for GPU workstations to run Seq2Seq models (e.g. `google/flan-t5-base` or T5-Grammar).
* **Safe, Non-Destructive Operation:**
  * Uses Windows UI Automation `TextPattern` directly for zero clipboard footprint.
  * Clipboard fallback always takes a complete backup and immediately restores your original clipboard within 40 milliseconds.
  * Automatically detects and skips password/secure input fields to protect your privacy.
* **Unobtrusive System Tray Integration:**
  * Runs quietly in the Windows notification area with a status-aware icon.
  * Allows toggling active state, configuring hotkeys, setting edit distance, and managing Windows startup.

---

## Keyboard Shortcuts

| Shortcut | Function | Description |
| :--- | :--- | :--- |
| **`F2`** | Next Prediction / Activate | Corrects the word preceding the cursor; pressing repeatedly cycles forward through suggestions. |
| **`Shift+F2`** | Previous Prediction | Cycles backward to the previous suggestion. |
| **`Esc`** | Restore Original | Instantly reverts all suggestions and restores your original typed word. |
| **`Ctrl+F2`** | Sentence Correction | Corrects spelling, grammar, and agreement of highlighted text. |

*All shortcuts can be customized in the Settings window (accessible via the System Tray icon).*

---

## Project Architecture

```
TypoPilot/
├── main.py                     # Main background desktop application and tray lifecycle
├── config.py                   # Persistent configuration manager (JSON)
├── config.json                 # User settings, shortcuts, and NLP thresholds
├── requirements.txt            # Environment dependency specifications
├── run.bat                     # 1-click Windows background launcher
├── run_typopilot.pyw           # Windowless background pythonw launcher
│
├── core/
│   ├── keyboard_manager.py     # Low-level global keyboard listener with loop prevention
│   ├── text_handler.py         # Cursor-aware text detection & safe replacement
│   ├── correction_manager.py   # State manager for prediction cycling and undo
│   ├── undo_manager.py         # Stack-based history of applied corrections
│   └── startup_manager.py      # Windows Startup folder integration
│
├── nlp/
│   ├── spell_checker.py        # Unified spelling correction coordinator
│   ├── candidate_generator.py  # SymSpell Symmetric Delete candidate generator
│   ├── context_ranker.py       # Bigram language model contextual re-ranker
│   ├── sentence_corrector.py   # Dual-mode sentence engine (Local CPU + GPU Neural)
│   └── text_preprocessor.py    # Tokenization and apostrophe normalizer
│
├── ui/
│   ├── tray_manager.py         # Windows System Tray icon, menu, and notifications
│   └── settings_window.py      # Compact settings dialog for shortcuts and NLP options
│
└── tests/
    ├── test_config.py          # Configuration loading and persistence tests
    ├── test_keyboard_manager.py# Global shortcut priority and suppression tests
    ├── test_text_handler.py    # Cursor word extraction and casing tests
    ├── test_spell_checker.py   # Word-level candidate generation & N-gram tests
    ├── test_sentence_corrector.py # Grammar agreement and tense tests
    ├── test_sentence_handling.py  # Selected text detection and replacement tests
    ├── test_correction_manager.py # Cycling and Esc restoration tests
    ├── test_startup_manager.py # Windows startup launcher tests
    ├── test_ui.py              # System tray icon and dialog tests
    └── test_e2e_scenarios.py   # Comprehensive end-to-end integration tests
```

---

## Installation & Setup

### Running on This Machine (or Laptop):
```bash
# Double-click run.bat OR execute in terminal:
D:\TypoPilot\.venv\Scripts\python.exe main.py
```

### Running on Another PC (e.g. Tomorrow's GPU Workstation):
1. **Clone the repository:**
   ```bash
   git clone https://github.com/ganesh2007-abd/TypoPilot.git
   cd TypoPilot
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Launch TypoPilot:**
   ```bash
   python main.py
   ```

---

## Automated Verification & Testing

TypoPilot includes a full test suite with **28 automated unit and end-to-end tests** covering all specifications:

```bash
# Run the test suite:
pytest -v
```

### Verified Test Cases:
* **Word-Level Typos:**
  * `recieve` &rarr; `receive`
  * `teh` &rarr; `the`
  * `accomodate` &rarr; `accommodate`
  * `definately` &rarr; `definitely`
  * `seperate` &rarr; `separate`
* **Sentence-Level Grammar & Agreement:**
  * *"He go to college everyday and attend classes regularly."* &rarr; **"He goes to college every day and attends classes regularly."**
  * *"He go to college every day."* &rarr; **"He goes to college every day."**
  * *"She don't like mathematics."* &rarr; **"She doesn't like mathematics."**
  * *"They was playing football."* &rarr; **"They were playing football."**
  * *"I has completed my assignment."* &rarr; **"I have completed my assignment."**
* **Interaction Scenarios:**
  * Cursor moved backwards after typing an entire paragraph.
  * Capitalization preservation (`Recieve` &rarr; `Receive`, `RECIEVE` &rarr; `RECEIVE`).
  * Punctuation preservation (`recieve,` &rarr; `receive,`).
  * Prediction cycling forward (`F2`) and backward (`Shift+F2`).
  * Restoring original misspelled word (`Esc`).
  * Non-destructive clipboard preservation.
  * Privacy protection on password/secure input fields.
