# TypoPilot

An Intelligent Desktop-Based NLP Assistant for Real-Time Word and Sentence Correction on Windows.

## Overview
TypoPilot is a lightweight, background-running desktop assistant designed to intelligently correct typos and grammatical errors across ordinary Windows applications (Microsoft Word, Notepad, Google Chrome, WhatsApp Desktop, etc.).

Unlike aggressive autocorrect systems, TypoPilot corrects text **only on explicit user request** via keyboard shortcuts, preserving original text and allowing cycling through predictions.

## Features
- **Word-Level Correction (F2):** Automatically identifies the word preceding the cursor, ranks candidate corrections using Levenshtein distance & frequency dictionaries, and replaces the typo in-place.
- **Prediction Cycling (F2 repeatedly):** Pressing the shortcut again cycles through alternative suggestions.
- **Undo / Restore (Esc):** Restores the original text if suggestions are cancelled.
- **Sentence & Paragraph Grammar Correction (Ctrl + F2):** Corrects grammatical errors in selected text using NLP models.
- **Cross-Application Support:** Works seamlessly via Windows UI Automation with safe clipboard fallback.

## Setup & Portability
To run this project on any Windows machine (including GPU workstations):

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd TypoPilot

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```
