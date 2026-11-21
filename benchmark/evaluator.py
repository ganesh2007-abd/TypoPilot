"""TypoPilot Automated Benchmark Evaluator.

Measures accuracy, precision, top-k recall, and processing latency
across standard human spelling error benchmarks and sentence grammar corpora.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from config import TypoPilotConfig
from nlp.sentence_corrector import SentenceCorrector
from nlp.spell_checker import SpellChecker


def run_word_benchmark(spell_checker: SpellChecker, testset_path: Path) -> Dict[str, float]:
    """Evaluates word-level spelling correction accuracy across Top-1, Top-3, and Top-5."""
    with open(testset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0
    latencies = []

    print(f"\n[+] Running Word Spelling Benchmark ({total} test cases)...")

    for item in data:
        misspelled = item["misspelled"]
        target = item["correct"].lower()

        t0 = time.perf_counter()
        suggestions = spell_checker.get_suggestions(misspelled, max_suggestions=5)
        t1 = time.perf_counter()

        latencies.append((t1 - t0) * 1000.0)  # ms
        suggested_lower = [s.lower() for s in suggestions]

        if suggested_lower and suggested_lower[0] == target:
            top1_correct += 1

        if target in suggested_lower[:3]:
            top3_correct += 1

        if target in suggested_lower[:5]:
            top5_correct += 1

    top1_acc = (top1_correct / total) * 100.0
    top3_acc = (top3_correct / total) * 100.0
    top5_acc = (top5_correct / total) * 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "total": total,
        "top1_acc": top1_acc,
        "top3_acc": top3_acc,
        "top5_acc": top5_acc,
        "avg_latency_ms": avg_latency,
    }


def run_sentence_benchmark(corrector: SentenceCorrector, testset_path: Path) -> Dict[str, float]:
    """Evaluates sentence-level grammar and spelling correction accuracy."""
    with open(testset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    exact_matches = 0
    latencies = []

    print(f"\n[+] Running Sentence Grammar Benchmark ({total} test cases)...")

    for item in data:
        inp = item["input"]
        expected = item["expected"]

        t0 = time.perf_counter()
        actual = corrector.correct_text(inp)
        t1 = time.perf_counter()

        latencies.append((t1 - t0) * 1000.0)

        # Normalize casing and punctuation for clean comparison
        if actual.strip().rstrip(".!?").lower() == expected.strip().rstrip(".!?").lower():
            exact_matches += 1

    acc = (exact_matches / total) * 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "total": total,
        "exact_matches": exact_matches,
        "accuracy": acc,
        "avg_latency_ms": avg_latency,
    }


def main():
    print("=" * 65)
    print("           TYPOPILOT ACCURACY & PERFORMANCE BENCHMARK")
    print("=" * 65)

    base_dir = Path(__file__).resolve().parent
    word_testset = base_dir / "word_testset.json"
    sentence_testset = base_dir / "sentence_testset.json"

    cfg = TypoPilotConfig()
    spell_checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, spell_checker)

    # 1. Word Benchmark
    word_res = run_word_benchmark(spell_checker, word_testset)

    # 2. Sentence Benchmark
    sentence_res = run_sentence_benchmark(corrector, sentence_testset)

    # Print Final Summary Report
    print("\n" + "=" * 65)
    print("                       BENCHMARK RESULTS")
    print("=" * 65)
    print(f" WORD-LEVEL SPELLING CORRECTION ({word_res['total']} words):")
    print(f"   - Top-1 Accuracy (Exact first suggestion):  {word_res['top1_acc']:.2f}%")
    print(f"   - Top-3 Recall (In first 3 suggestions):   {word_res['top3_acc']:.2f}%")
    print(f"   - Top-5 Recall (In first 5 suggestions):   {word_res['top5_acc']:.2f}%")
    print(f"   - Average Lookup Speed:                    {word_res['avg_latency_ms']:.2f} ms / word")
    print("-" * 65)
    print(f" SENTENCE & GRAMMAR CORRECTION ({sentence_res['total']} sentences):")
    print(f"   - Exact Match Accuracy:                    {sentence_res['accuracy']:.2f}%")
    print(f"   - Average Processing Speed:                {sentence_res['avg_latency_ms']:.2f} ms / sentence")
    print("=" * 65)


if __name__ == "__main__":
    main()
