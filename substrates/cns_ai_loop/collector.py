"""
NFI v2.1 — EVL Channel B: Decision Latency Collector
=====================================================
External witness for cognitive decision quality.
Measures: latency, time-to-first-token (approximated), accuracy.
All tasks have objective ground truth. Zero self-report.

Usage:
    python collector.py                  # baseline session
    python collector.py --perturbation   # with perturbation blocks
    python collector.py --duration 45    # custom duration in minutes
"""

import time
import json
import uuid
import random
import math
import sys
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# ─── Clock ───────────────────────────────────────────────────────────────

def now_ns() -> int:
    return time.monotonic_ns()

def utc_ns() -> int:
    return int(time.time() * 1e9)

# ─── Storage ─────────────────────────────────────────────────────────────

SESSION_ID = time.strftime("%Y%m%d_%H%M%S")
BASE = Path(f"evidence/sessions/session_{SESSION_ID}")
BASE.mkdir(parents=True, exist_ok=True)

def log_jsonl(filename: str, obj: dict):
    path = BASE / filename
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")

# ─── Task Generators (all with verifiable ground truth) ──────────────────

@dataclass
class Task:
    task_id: str
    task_type: str
    prompt: str
    ground_truth: str
    difficulty: int  # 1-5

def _uid() -> str:
    return uuid.uuid4().hex[:8]

# --- Type 1: Arithmetic (exact) ---
def gen_arithmetic(difficulty: int = 2) -> Task:
    ops = {1: (10, 99), 2: (100, 999), 3: (1000, 9999), 4: (10000, 99999), 5: (100000, 999999)}
    lo, hi = ops.get(difficulty, (100, 999))
    a, b = random.randint(lo, hi), random.randint(lo, hi)
    op = random.choice(['+', '-', '*'])
    if op == '+':
        answer = a + b
    elif op == '-':
        answer = a - b
    else:
        # keep multiplication manageable
        b = random.randint(2, 99)
        answer = a * b
    expr = f"{a} {op} {b}"
    return Task(_uid(), "arithmetic", f"Compute: {expr}", str(answer), difficulty)

# --- Type 2: Modular arithmetic ---
def gen_modular(difficulty: int = 3) -> Task:
    mods = {1: 7, 2: 13, 3: 37, 4: 97, 5: 257}
    m = mods.get(difficulty, 37)
    a = random.randint(100, 9999)
    b = random.randint(100, 9999)
    answer = (a * b) % m
    return Task(_uid(), "modular", f"({a} * {b}) mod {m} = ?", str(answer), difficulty)

# --- Type 3: Sequence next element (deterministic) ---
def gen_sequence(difficulty: int = 2) -> Task:
    seq_type = random.choice(["fib_mod", "power_mod", "triangular"])
    if seq_type == "fib_mod":
        m = random.choice([10, 100, 1000])
        seq = [0, 1]
        for _ in range(8):
            seq.append((seq[-1] + seq[-2]) % m)
        shown = seq[:8]
        answer = str(seq[8])
        prompt = f"Fibonacci mod {m}: {', '.join(map(str, shown))}, next = ?"
    elif seq_type == "power_mod":
        base = random.randint(2, 5)
        m = random.choice([7, 11, 13])
        seq = [(base**i) % m for i in range(9)]
        shown = seq[:8]
        answer = str(seq[8])
        prompt = f"{base}^n mod {m}: {', '.join(map(str, shown))}, next = ?"
    else:
        # triangular numbers
        seq = [n * (n + 1) // 2 for n in range(1, 10)]
        shown = seq[:7]
        answer = str(seq[7])
        prompt = f"Sequence: {', '.join(map(str, shown))}, next = ?"
    return Task(_uid(), "sequence", prompt, answer, difficulty)

# --- Type 4: Bitwise operations ---
def gen_bitwise(difficulty: int = 2) -> Task:
    bits = {1: 8, 2: 12, 3: 16, 4: 20, 5: 24}
    n = bits.get(difficulty, 12)
    a = random.randint(0, (1 << n) - 1)
    b = random.randint(0, (1 << n) - 1)
    op = random.choice(['AND', 'OR', 'XOR'])
    if op == 'AND':
        answer = a & b
    elif op == 'OR':
        answer = a | b
    else:
        answer = a ^ b
    return Task(_uid(), "bitwise", f"{a} {op} {b} = ?", str(answer), difficulty)

# --- Type 5: Pattern matching (string) ---
def gen_pattern(difficulty: int = 2) -> Task:
    length = {1: 20, 2: 40, 3: 80, 4: 120, 5: 200}.get(difficulty, 40)
    alphabet = "ABCDEFGHIJKLMNOP"[:4 + difficulty]
    haystack = ''.join(random.choice(alphabet) for _ in range(length))
    needle_len = random.randint(3, 5)
    # plant needle at random position
    pos = random.randint(0, length - needle_len)
    needle = haystack[pos:pos + needle_len]
    # count all occurrences
    count = 0
    for i in range(len(haystack) - needle_len + 1):
        if haystack[i:i + needle_len] == needle:
            count += 1
    return Task(
        _uid(), "pattern",
        f"Count occurrences of '{needle}' in: {haystack}",
        str(count), difficulty
    )

# --- Type 6: Logic / Boolean evaluation ---
def gen_logic(difficulty: int = 2) -> Task:
    vars_count = min(2 + difficulty, 6)
    names = list("ABCDEF")[:vars_count]
    vals = {n: random.choice([True, False]) for n in names}

    # build expression
    ops = ['and', 'or']
    expr_parts = [names[0]]
    for i in range(1, vars_count):
        op = random.choice(ops)
        if random.random() < 0.3:
            expr_parts.append(f"{op} not {names[i]}")
        else:
            expr_parts.append(f"{op} {names[i]}")
    expr = ' '.join(expr_parts)

    # evaluate
    env = {n: v for n, v in vals.items()}
    result = eval(expr, {"__builtins__": {}}, env)

    assignment = ', '.join(f"{n}={'T' if v else 'F'}" for n, v in vals.items())
    return Task(
        _uid(), "logic",
        f"Given {assignment}: evaluate ({expr})",
        "True" if result else "False", difficulty
    )

GENERATORS = [
    gen_arithmetic, gen_modular, gen_sequence,
    gen_bitwise, gen_pattern, gen_logic
]

# ─── Perturbation Engine ─────────────────────────────────────────────────

class PerturbationManager:
    """Manages perturbation schedule: baseline → stress → recovery."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.phase = "baseline"
        self.phase_start = now_ns()
        self.block_index = 0
        self.schedule = []  # filled on start

    def build_schedule(self, total_min: int):
        """3-5 min baseline, 1-2 min perturbation, 3-5 min recovery, repeat."""
        if not self.enabled:
            return
        t = 0
        while t < total_min:
            bl = random.randint(3, 5)
            self.schedule.append(("baseline", bl))
            t += bl
            if t >= total_min:
                break
            pt = random.randint(1, 2)
            ptype = random.choice(["time_pressure", "rule_change", "increased_difficulty"])
            self.schedule.append((f"perturbation:{ptype}", pt))
            t += pt
            if t >= total_min:
                break
            rc = random.randint(3, 5)
            self.schedule.append(("recovery", rc))
            t += rc
        self.phase = self.schedule[0][0] if self.schedule else "baseline"
        self.phase_start = now_ns()

    def get_current_phase(self, elapsed_min: float) -> str:
        if not self.enabled or not self.schedule:
            return "baseline"
        acc = 0
        for phase, dur in self.schedule:
            acc += dur
            if elapsed_min < acc:
                if phase != self.phase:
                    self.phase = phase
                    self.phase_start = now_ns()
                    log_jsonl("events.jsonl", {
                        "t_ns": now_ns(),
                        "utc_ns": utc_ns(),
                        "event": "phase_change",
                        "phase": phase,
                        "elapsed_min": round(elapsed_min, 2)
                    })
                return phase
        return "recovery"

    def modify_task(self, task: Task, phase: str) -> Task:
        """Apply perturbation effects to task generation."""
        if "time_pressure" in phase:
            # no task modification, but time limit enforced in runner
            pass
        elif "increased_difficulty" in phase:
            task.difficulty = min(task.difficulty + 2, 5)
        elif "rule_change" in phase:
            # reverse the prompt format (minor cognitive disruption)
            task.prompt = f"[REVERSED] Answer first, then verify: {task.prompt}"
        return task

    def get_time_limit(self, phase: str, base_limit: float) -> float:
        if "time_pressure" in phase:
            return base_limit * 0.5
        return base_limit

# ─── Session Runner ──────────────────────────────────────────────────────

class SessionRunner:
    def __init__(self, duration_min: int = 30, perturbation: bool = False):
        self.duration_min = duration_min
        self.perturbation = PerturbationManager(perturbation)
        self.perturbation.build_schedule(duration_min)
        self.session_start = None
        self.task_count = 0
        self.correct_count = 0

    def run(self):
        self.session_start = now_ns()
        session_start_utc = utc_ns()

        # Write manifest
        manifest = {
            "session_id": SESSION_ID,
            "start_utc_ns": session_start_utc,
            "duration_target_min": self.duration_min,
            "perturbation_enabled": self.perturbation.enabled,
            "perturbation_schedule": self.perturbation.schedule if self.perturbation.enabled else [],
            "task_generators": [g.__name__ for g in GENERATORS],
            "python_version": sys.version,
            "platform": sys.platform,
        }
        manifest_dir = Path("evidence/manifests")
        manifest_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_dir / f"manifest_{SESSION_ID}.json", "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n{'='*60}")
        print(f"  NFI v2.1 — Channel B: Decision Latency Collector")
        print(f"  Session: {SESSION_ID}")
        print(f"  Duration: {self.duration_min} min")
        print(f"  Perturbation: {'ON' if self.perturbation.enabled else 'OFF'}")
        print(f"{'='*60}\n")
        print("  Type answer and press Enter. 'q' to quit.\n")

        # Log session start event
        log_jsonl("events.jsonl", {
            "t_ns": now_ns(),
            "utc_ns": session_start_utc,
            "event": "session_start",
            "meta": {"duration_min": self.duration_min}
        })

        try:
            while True:
                elapsed_ns = now_ns() - self.session_start
                elapsed_min = elapsed_ns / 60e9

                if elapsed_min >= self.duration_min:
                    print(f"\n  Time limit reached ({self.duration_min} min).")
                    break

                # Get current phase
                phase = self.perturbation.get_current_phase(elapsed_min)
                phase_display = phase.split(":")[-1] if ":" in phase else phase

                # Generate task
                gen = random.choice(GENERATORS)
                difficulty = random.randint(1, 3)
                if "increased_difficulty" in phase:
                    difficulty = random.randint(3, 5)
                task = gen(difficulty)
                task = self.perturbation.modify_task(task, phase)

                # Time limit
                base_limit = 120.0  # seconds
                time_limit = self.perturbation.get_time_limit(phase, base_limit)

                # Display
                remaining = self.duration_min - elapsed_min
                self.task_count += 1
                print(f"  [{phase_display}] Task #{self.task_count} "
                      f"({task.task_type} d={task.difficulty}) "
                      f"[{remaining:.1f} min left]")
                if "time_pressure" in phase:
                    print(f"  ⚡ TIME PRESSURE: {time_limit:.0f}s limit")
                print(f"  → {task.prompt}")

                # Capture response
                start_ns = now_ns()
                try:
                    answer = input("  ← ").strip()
                except EOFError:
                    break

                end_ns = now_ns()
                latency_ms = (end_ns - start_ns) / 1e6

                if answer.lower() == 'q':
                    print("\n  Session terminated by user.")
                    break

                # Validate
                correct = (answer == task.ground_truth)
                timed_out = (latency_ms / 1000) > time_limit

                if correct:
                    self.correct_count += 1
                    print(f"  ✓ Correct ({latency_ms:.0f} ms)")
                else:
                    print(f"  ✗ Wrong. Expected: {task.ground_truth} ({latency_ms:.0f} ms)")

                if timed_out and "time_pressure" in phase:
                    print(f"  ⏱ TIMEOUT ({latency_ms/1000:.1f}s > {time_limit:.0f}s)")

                # Log decision
                log_jsonl("decisions.jsonl", {
                    "t_ns": end_ns,
                    "utc_ns": utc_ns(),
                    "session_id": SESSION_ID,
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "difficulty": task.difficulty,
                    "phase": phase,
                    "latency_ms": round(latency_ms, 2),
                    "correct": int(correct),
                    "timed_out": int(timed_out),
                    "prompt": task.prompt,
                    "expected": task.ground_truth,
                    "given": answer,
                })

                # Log perturbation event if relevant
                if "perturbation" in phase:
                    log_jsonl("events.jsonl", {
                        "t_ns": end_ns,
                        "utc_ns": utc_ns(),
                        "event": "perturbation_task",
                        "type": phase,
                        "task_id": task.task_id,
                    })

                print()

        except KeyboardInterrupt:
            print("\n\n  Session interrupted.")

        # End session
        end_utc = utc_ns()
        total_ns = now_ns() - self.session_start
        accuracy = (self.correct_count / self.task_count * 100) if self.task_count > 0 else 0

        log_jsonl("events.jsonl", {
            "t_ns": now_ns(),
            "utc_ns": end_utc,
            "event": "session_end",
            "meta": {
                "total_tasks": self.task_count,
                "correct": self.correct_count,
                "accuracy_pct": round(accuracy, 1),
                "duration_actual_s": round(total_ns / 1e9, 1),
            }
        })

        print(f"\n{'='*60}")
        print(f"  Session Complete")
        print(f"  Tasks: {self.task_count}")
        print(f"  Correct: {self.correct_count} ({accuracy:.1f}%)")
        print(f"  Duration: {total_ns/60e9:.1f} min")
        print(f"  Data: {BASE}/")
        print(f"{'='*60}\n")

# ─── Entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    duration = 30
    perturbation = False

    args = sys.argv[1:]
    if "--perturbation" in args:
        perturbation = True
    for i, arg in enumerate(args):
        if arg == "--duration" and i + 1 < len(args):
            duration = int(args[i + 1])

    runner = SessionRunner(duration_min=duration, perturbation=perturbation)
    runner.run()
