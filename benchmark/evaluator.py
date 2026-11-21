"""TypoPilot Automated Benchmark Evaluator.

Universal benchmark tool for evaluating word-level spelling accuracy and sentence-level
grammar correction. Supports Peter Norvig format (.txt), JSON, CSV, and TSV datasets.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from config import TypoPilotConfig
from nlp.sentence_corrector import SentenceCorrector
from nlp.spell_checker import SpellChecker


def parse_dataset_file(file_path: Path) -> Tuple[str, List[Dict]]:
    """Universal dataset loader.

    Supports:
    1. Norvig colon format (.txt): 'correct: typo1 typo2 typo3'
    2. JSON format (.json): [{'misspelled': '...', 'correct': '...'}, ...] or sentence pairs
    3. CSV / TSV format (.csv, .tsv): 'typo,correct' or 'input\texpected'

    Returns:
        Tuple of (dataset_type, items_list) where dataset_type is 'word' or 'sentence'.
    """
    clean_path = str(file_path).strip().strip('"').strip("'")
    path_obj = Path(clean_path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Dataset file not found: {clean_path}")

    # 1. JSON parsing
    if path_obj.suffix.lower() == ".json":
        with open(path_obj, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return "word", []

        sample = data[0]
        if "input" in sample or "sentence" in sample:
            items = []
            for row in data:
                inp = row.get("input") or row.get("sentence") or row.get("original", "")
                exp = row.get("expected") or row.get("correct") or row.get("corrected", "")
                items.append({"input": inp, "expected": exp})
            return "sentence", items
        else:
            items = []
            for row in data:
                misp = row.get("misspelled") or row.get("typo") or row.get("error", "")
                corr = row.get("correct") or row.get("word") or row.get("target", "")
                items.append({"misspelled": misp, "correct": corr})
            return "word", items

    # 2. Text / CSV / TSV parsing
    with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        return "word", []

    # Check if Peter Norvig format: 'target: typo1 typo2 ...'
    has_colon_typos = any(":" in line and len(line.split(":", 1)[1].split()) >= 1 for line in lines[:5])
    if has_colon_typos:
        items = []
        for line in lines:
            if ":" not in line:
                continue
            target, typos = line.split(":", 1)
            target = target.strip()
            for t in typos.split():
                items.append({"misspelled": t, "correct": target})
        return "word", items

    # Delimited CSV / TSV format
    delimiter = "\t" if "\t" in lines[0] else ("," if "," in lines[0] else None)
    if delimiter:
        items = []
        is_sentence = False
        reader = csv.reader(lines, delimiter=delimiter)
        for row in reader:
            if len(row) >= 2:
                col1, col2 = row[0].strip(), row[1].strip()
                if len(col1.split()) > 2 or len(col2.split()) > 2:
                    is_sentence = True
                    items.append({"input": col1, "expected": col2})
                else:
                    items.append({"misspelled": col1, "correct": col2})
        return ("sentence" if is_sentence else "word"), items

    # Fallback space-separated: 'typo correct'
    items = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            items.append({"misspelled": parts[0], "correct": parts[1]})
    return "word", items


def evaluate_words(spell_checker: SpellChecker, items: List[Dict], dataset_name: str = "Custom") -> Dict[str, float]:
    """Evaluates word-level spelling suggestions on test items."""
    total = len(items)
    if total == 0:
        print("[!] No items found to evaluate.")
        return {}

    top1 = 0
    top3 = 0
    top5 = 0
    latencies = []

    print(f"\n[+] Running Word Spelling Benchmark: {dataset_name} ({total} test cases)...")

    for idx, item in enumerate(items, 1):
        misspelled = item["misspelled"]
        target = item["correct"].lower()

        t0 = time.perf_counter()
        suggestions = spell_checker.get_suggestions(misspelled, max_suggestions=5)
        t1 = time.perf_counter()

        latencies.append((t1 - t0) * 1000.0)
        sug_lower = [s.lower() for s in suggestions]

        if sug_lower and sug_lower[0] == target:
            top1 += 1
        if target in sug_lower[:3]:
            top3 += 1
        if target in sug_lower[:5]:
            top5 += 1

        # Periodic progress update for large datasets
        if idx % 100 == 0 or idx == total:
            sys.stdout.write(f"\r    Processed: {idx}/{total} words (Top-1 so far: {top1/idx*100:.1f}%)")
            sys.stdout.flush()

    print()

    top1_acc = (top1 / total) * 100.0
    top3_acc = (top3 / total) * 100.0
    top5_acc = (top5 / total) * 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 65)
    print(f"       WORD SPELLING RESULTS: {dataset_name.upper()}")
    print("=" * 65)
    print(f" Total Test Cases Evaluated:       {total}")
    print(f" Top-1 Accuracy (1st suggestion):  {top1_acc:.2f}%  ({top1}/{total})")
    print(f" Top-3 Recall (In Top 3):          {top3_acc:.2f}%  ({top3}/{total})")
    print(f" Top-5 Recall (In Top 5):          {top5_acc:.2f}%  ({top5}/{total})")
    print(f" Average Speed:                    {avg_latency:.2f} ms / word")
    print("=" * 65)

    return {"total": total, "top1": top1_acc, "top3": top3_acc, "top5": top5_acc, "latency": avg_latency}


def evaluate_sentences(corrector: SentenceCorrector, items: List[Dict], dataset_name: str = "Custom") -> Dict[str, float]:
    """Evaluates sentence-level grammar correction on test items."""
    total = len(items)
    if total == 0:
        print("[!] No sentence items found to evaluate.")
        return {}

    exact_matches = 0
    latencies = []

    print(f"\n[+] Running Sentence Grammar Benchmark: {dataset_name} ({total} test cases)...")

    for idx, item in enumerate(items, 1):
        inp = item["input"]
        expected = item["expected"]

        t0 = time.perf_counter()
        actual = corrector.correct_text(inp)
        t1 = time.perf_counter()

        latencies.append((t1 - t0) * 1000.0)

        # Normalize comparison
        if actual.strip().rstrip(".!?").lower() == expected.strip().rstrip(".!?").lower():
            exact_matches += 1

        if idx % 20 == 0 or idx == total:
            sys.stdout.write(f"\r    Processed: {idx}/{total} sentences (Accuracy: {exact_matches/idx*100:.1f}%)")
            sys.stdout.flush()

    print()

    acc = (exact_matches / total) * 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 65)
    print(f"     SENTENCE GRAMMAR RESULTS: {dataset_name.upper()}")
    print("=" * 65)
    print(f" Total Sentences Evaluated:        {total}")
    print(f" Exact Match Accuracy:             {acc:.2f}%  ({exact_matches}/{total})")
    print(f" Average Processing Speed:         {avg_latency:.2f} ms / sentence")
    print("=" * 65)

    return {"total": total, "accuracy": acc, "latency": avg_latency}


def main():
    base_dir = Path(__file__).resolve().parent
    norvig1_file = base_dir / "norvig_testset1.txt"
    norvig2_file = base_dir / "norvig_testset2.txt"
    default_word_file = base_dir / "word_testset.json"
    default_sentence_file = base_dir / "sentence_testset.json"

    print("=" * 65)
    print("           TYPOPILOT UNIVERSAL BENCHMARK SUITE")
    print("=" * 65)

    # Check CLI argument (passed when file is dragged onto .bat or run from terminal)
    file_arg: str | None = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        file_arg = sys.argv[1].strip().strip('"').strip("'")

    if not file_arg:
        print("\nSelect an evaluation option:")
        print("  [1] Peter Norvig Gold Benchmark Set 1 (270 real human typos)")
        print("  [2] Peter Norvig Gold Benchmark Set 2 (400 real human typos)")
        print("  [3] Built-in Standard Suite (129 common words + 15 sentences)")
        print("  [4] Full Combined Evaluation (Norvig 1 + Norvig 2 + Sentences)")
        print("  [Or] Drag and drop your downloaded file (.txt, .json, .csv) here")
        print()
        choice = input("Enter choice (1/2/3/4) or drag & drop file path [Default: 3]: ").strip().strip('"').strip("'")
        if choice in ("1", "2", "3", "4", ""):
            file_arg = choice
        else:
            file_arg = choice

    cfg = TypoPilotConfig()
    spell_checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, spell_checker)

    # Route based on choice or file path
    if file_arg == "1":
        dtype, items = parse_dataset_file(norvig1_file)
        evaluate_words(spell_checker, items, "Peter Norvig Testset 1")
    elif file_arg == "2":
        dtype, items = parse_dataset_file(norvig2_file)
        evaluate_words(spell_checker, items, "Peter Norvig Testset 2")
    elif file_arg in ("3", ""):
        # Default suite
        dtype, word_items = parse_dataset_file(default_word_file)
        evaluate_words(spell_checker, word_items, "Default Word Suite")
        dtype, sent_items = parse_dataset_file(default_sentence_file)
        evaluate_sentences(corrector, sent_items, "Default Grammar Suite")
    elif file_arg == "4":
        # All combined
        dtype, n1_items = parse_dataset_file(norvig1_file)
        dtype, n2_items = parse_dataset_file(norvig2_file)
        dtype, def_items = parse_dataset_file(default_word_file)
        combined_words = n1_items + n2_items + def_items
        evaluate_words(spell_checker, combined_words, f"All Combined Word Sets ({len(combined_words)} words)")
        dtype, sent_items = parse_dataset_file(default_sentence_file)
        evaluate_sentences(corrector, sent_items, "Default Grammar Suite")
    else:
        # Custom user-provided file!
        target_path = Path(file_arg)
        if not target_path.exists():
            print(f"\n[ERROR] File not found: {file_arg}")
            return
        dtype, items = parse_dataset_file(target_path)
        if dtype == "sentence":
            evaluate_sentences(corrector, items, target_path.name)
        else:
            evaluate_words(spell_checker, items, target_path.name)


if __name__ == "__main__":
    main()
