"""Offline labelled-data evaluation; no database writes or provider calls."""

import hashlib
import json
import math
import platform
import random
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.test import override_settings

from .profile_extractor import ProfileExtractor
from .matching.matcher import compute_hybrid_match
from .matching.scorer import SCORING_VERSION, validate_weights

SPLITS = {"regression", "challenge", "train", "validation", "test"}


def finite(value, low=0, high=60):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and low <= value <= high
    )


def validate_dataset(dataset):
    if not isinstance(dataset, dict) or not isinstance(dataset.get("version"), str):
        raise ValueError("Dataset requires a version and labelled records/jobs.")
    date.fromisoformat(dataset["as_of_date"])
    jobs, rows = dataset.get("jobs"), dataset.get("records")
    if (
        not isinstance(jobs, list)
        or not 1 <= len(jobs) <= 10
        or not isinstance(rows, list)
        or not 1 <= len(rows) <= 500
    ):
        raise ValueError("Provide 1-10 jobs and 1-500 labelled records.")
    ids = set()
    for job in jobs:
        if (
            not isinstance(job, dict)
            or not isinstance(job.get("id"), str)
            or not job["id"]
            or job["id"] in ids
        ):
            raise ValueError("Job IDs must be unique nonempty strings.")
        ids.add(job["id"])
        if (
            not isinstance(job.get("required_skills"), list)
            or not job["required_skills"]
            or any(not isinstance(s, str) or not s.strip() for s in job["required_skills"])
        ):
            raise ValueError("Jobs require labelled skill requirements.")
        if not finite(job.get("minimum_experience")) or not isinstance(
            job.get("education_requirement", ""), str
        ):
            raise ValueError("Invalid job experience or education requirement.")
        validate_weights(job.get("scoring_weights", {}))
    ids = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not row["id"]
            or row["id"] in ids
        ):
            raise ValueError("Record IDs must be unique nonempty strings.")
        ids.add(row["id"])
        if row.get("split") not in SPLITS:
            raise ValueError(
                "Each record needs a regression/challenge/train/validation/test split."
            )
        if (
            not isinstance(row.get("text"), str)
            or not 1 <= len(row["text"]) <= 20000
            or not isinstance(row.get("email"), str)
            or not finite(row.get("years"))
        ):
            raise ValueError("Invalid text, expected email, or experience label.")
        if (
            not isinstance(row.get("skills"), list)
            or len(row["skills"]) > 100
            or any(not isinstance(s, str) or not s.strip() for s in row["skills"])
        ):
            raise ValueError("Skills must be labelled with nonempty strings.")
        if (
            not isinstance(row.get("grades"), list)
            or len(row["grades"]) != len(jobs)
            or any(
                isinstance(g, bool) or not isinstance(g, int) or not 0 <= g <= 3
                for g in row["grades"]
            )
        ):
            raise ValueError("Each record needs one relevance grade (0-3) for each job.")
        if "ratings" in row and (
            not isinstance(row["ratings"], list)
            or len(row["ratings"]) != 2
            or any(
                not isinstance(r, list)
                or len(r) != len(jobs)
                or any(isinstance(g, bool) or not isinstance(g, int) or not 0 <= g <= 3 for g in r)
                for r in row["ratings"]
            )
        ):
            raise ValueError("Optional ratings require exactly two complete annotator grade lists.")
    return dataset


def skill_metrics(cases):
    tp = sum(c["true_positive_skills"] for c in cases)
    fp = sum(len(c["unexpected_skills"]) for c in cases)
    fn = sum(len(c["missing_skills"]) for c in cases)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {
        "skill_precision": precision,
        "skill_recall": recall,
        "skill_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
    }


def extraction_metrics(cases):
    return {
        "email_accuracy": sum(c["email_correct"] for c in cases) / len(cases),
        "experience_mae_years": sum(c["experience_absolute_error"] for c in cases) / len(cases),
        **skill_metrics(cases),
    }


def intervals(cases, samples=500):
    rng = random.Random(42)
    draws = {key: [] for key in ["email_accuracy", "experience_mae_years", "skill_f1"]}
    for _ in range(samples):
        metrics = extraction_metrics(rng.choices(cases, k=len(cases)))
        for key in draws:
            draws[key].append(metrics[key])
    return {
        key: [
            round(sorted(values)[int(0.025 * samples)], 4),
            round(sorted(values)[min(samples - 1, int(0.975 * samples))], 4),
        ]
        for key, values in draws.items()
    }


def weighted_kappa(rows):
    pairs = [
        (r["ratings"][0][j], r["ratings"][1][j])
        for r in rows
        if "ratings" in r
        for j in range(len(r["grades"]))
    ]
    if not pairs:
        return None
    n = len(pairs)
    a = Counter(x for x, _ in pairs)
    b = Counter(y for _, y in pairs)
    observed = sum((x - y) ** 2 for x, y in pairs) / n
    expected = sum(a[i] * b[j] * (i - j) ** 2 for i in range(4) for j in range(4)) / (n * n)
    return {
        "quadratic_weighted_kappa": 1 - observed / expected if expected else None,
        "rated_pairs": n,
        "note": "Two supplied annotators only; independence is not verified.",
    }


def ranking_metrics(order, grades, k):
    relevant = {i for i, g in enumerate(grades) if g >= 2}
    return {
        "ndcg_at_k": round(ndcg(order, grades, k), 4),
        "recall_at_k": round(len(set(order[:k]) & relevant) / len(relevant), 4)
        if relevant
        else None,
        "mrr": round(next((1 / (p + 1) for p, i in enumerate(order) if i in relevant), 0), 4),
    }


def cosine(query, document, corpus):
    def tokens(s):
        return re.findall(r"[a-z]+", s.lower())

    docs = [tokens(s) for s in corpus]
    idf = {
        t: math.log((len(docs) + 1) / (sum(t in d for d in docs) + 1)) + 1
        for t in set(sum(docs, []))
    }

    def vector(text):
        return {t: n * idf.get(t, 1) for t, n in Counter(tokens(text)).items()}

    a, b = vector(query), vector(document)
    den = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return sum(v * b.get(t, 0) for t, v in a.items()) / den if den else 0


def latent_semantic_scores(query, corpus, dimensions=2):
    """Small LSA experiment: project document/query TF-IDF onto shared SVD axes."""
    import numpy as np

    documents = [re.findall(r"[a-z]+", text.lower()) for text in corpus]
    vocabulary = sorted(set(word for document in documents for word in document))
    if not vocabulary:
        return [0.0] * len(corpus)
    idf = np.array(
        [
            math.log((len(documents) + 1) / (sum(word in document for document in documents) + 1))
            + 1
            for word in vocabulary
        ]
    )
    matrix = (
        np.array(
            [[Counter(document)[word] for word in vocabulary] for document in documents],
            dtype=float,
        )
        * idf
    )
    query_counts = Counter(re.findall(r"[a-z]+", query.lower()))
    query_vector = np.array([query_counts[word] for word in vocabulary], dtype=float) * idf
    _, _, axes = np.linalg.svd(matrix, full_matrices=False)
    basis = axes[: min(dimensions, len(axes))].T
    projected = matrix @ basis
    projected_query = query_vector @ basis
    denominator = np.linalg.norm(projected, axis=1) * np.linalg.norm(projected_query)
    return np.divide(
        projected @ projected_query, denominator, out=np.zeros(len(corpus)), where=denominator > 0
    ).tolist()


def ndcg(order, grades, k=5):
    def gain(seq):
        return sum((2**value - 1) / math.log2(i + 2) for i, value in enumerate(seq[:k]))

    ideal = gain(sorted(grades, reverse=True))
    return gain([grades[i] for i in order]) / ideal if ideal else 0


def tfidf_scores(query, corpus):
    docs = [Counter(re.findall(r"[a-z]+", text.lower())) for text in corpus]
    vocabulary = set(t for d in docs for t in d)
    idf = {t: math.log((len(docs) + 1) / (sum(t in d for d in docs) + 1)) + 1 for t in vocabulary}
    q = {t: n * idf.get(t, 1) for t, n in Counter(re.findall(r"[a-z]+", query.lower())).items()}
    qnorm = math.sqrt(sum(v * v for v in q.values()))
    scores = []
    for doc in docs:
        vector = {t: n * idf[t] for t, n in doc.items()}
        denominator = qnorm * math.sqrt(sum(v * v for v in vector.values()))
        scores.append(
            sum(v * q.get(t, 0) for t, v in vector.items()) / denominator if denominator else 0
        )
    return scores


def evaluate_dataset(path, split="all", k=5, live_ai=False, limit=None, include_lsa=False):
    path = Path(path)
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Dataset must be at most 10 MB.")
    dataset = validate_dataset(json.loads(path.read_text(encoding="utf-8")))
    if split != "all" and split not in SPLITS:
        raise ValueError("Unknown split.")
    if not 1 <= k <= 100 or (limit is not None and not 1 <= limit <= 500):
        raise ValueError("k must be 1-100; limit must be 1-500.")
    all_rows = dataset["records"]
    rows = [r for r in all_rows if split == "all" or r["split"] == split]
    if limit:
        rows = rows[:limit]
    if not rows:
        raise ValueError("The requested split is empty.")
    if include_lsa and len(rows) > 100:
        raise ValueError("The optional LSA experiment is limited to 100 records.")
    hashes = {}
    for row in all_rows:
        digest = hashlib.sha256(" ".join(row["text"].lower().split()).encode("utf-8")).hexdigest()
        hashes.setdefault(digest, set()).add(row["split"])
    overlaps = sum(len(s) > 1 for s in hashes.values())
    extractor = ProfileExtractor(use_nlp=False, as_of=date.fromisoformat(dataset["as_of_date"]))
    profiles = []
    cases = []
    start = time.perf_counter()
    for row in rows:
        data = extractor.extract(row["text"])
        profiles.append(data)
        actual = {s.casefold() for s in data["skills"]}
        expected = {s.casefold() for s in row["skills"]}
        cases.append(
            {
                "id": row["id"],
                "split": row["split"],
                "category": row.get("category", "general"),
                "email_correct": data["email"] == row["email"],
                "experience_absolute_error": abs(float(data["years_of_experience"]) - row["years"]),
                "expected_years": row["years"],
                "extracted_years": float(data["years_of_experience"]),
                "true_positive_skills": len(actual & expected),
                "unexpected_skills": sorted(actual - expected),
                "missing_skills": sorted(expected - actual),
            }
        )
    extraction_seconds = time.perf_counter() - start
    predictions = {}
    score_runs = []
    calls = 0
    ai_successes = 0
    rank_start = time.perf_counter()
    flags = {"USE_LLM_FOR_SCORING": live_ai}
    if not live_ai:
        flags.update(USE_GROQ_AI=False, USE_GEMINI_FALLBACK=False)
    with override_settings(**flags):
        for job_spec in dataset["jobs"]:
            job = SimpleNamespace(
                **{
                    **job_spec,
                    "scoring_weights": job_spec.get("scoring_weights", {}),
                    "education_requirement": job_spec.get("education_requirement", ""),
                }
            )
            results = [compute_hybrid_match(SimpleNamespace(**p), job) for p in profiles]
            values = {
                "rubric": [r["deterministic_score"] for r in results],
                "exact_skills": [
                    len(
                        set(s.casefold() for s in p["skills"])
                        & set(s.casefold() for s in job.required_skills)
                    )
                    / len(set(s.casefold() for s in job.required_skills))
                    for p in profiles
                ],
                "tfidf": tfidf_scores(" ".join(job.required_skills), [r["text"] for r in rows]),
            }
            if include_lsa:
                values["lsa_2d"] = latent_semantic_scores(
                    " ".join(job.required_skills), [r["text"] for r in rows]
                )
            if live_ai:
                values["hybrid_ai"] = [r["score"] for r in results]
                for row, result in zip(rows, results):
                    calls += sum(
                        a["status"]
                        not in {
                            "missing_key",
                            "disabled",
                            "missing_configuration",
                            "insecure_endpoint",
                        }
                        for a in result["provider_attempts"]
                    )
                    ai_successes += result["llm_score"] is not None
                    score_runs.append(
                        {
                            "record_id": row["id"],
                            "job_id": job.id,
                            "snapshot": result["scoring_snapshot"],
                        }
                    )
            predictions[job.id] = values

    def rank_report(indices):
        report = {}
        for j, job in enumerate(dataset["jobs"]):
            grades = [rows[i]["grades"][j] for i in indices]
            report[job["id"]] = {}
            for name, values in predictions[job["id"]].items():
                order = sorted(
                    range(len(indices)), key=lambda p: (-values[indices[p]], rows[indices[p]]["id"])
                )
                report[job["id"]][name] = {
                    **ranking_metrics(order, grades, k),
                    "ordered_ids": [rows[indices[p]]["id"] for p in order],
                    "scores": [round(values[indices[p]], 4) for p in order],
                }
        return report

    by_split = {}
    for group in sorted({r["split"] for r in rows}):
        indices = [i for i, r in enumerate(rows) if r["split"] == group]
        selected = [cases[i] for i in indices]
        by_split[group] = {
            "records": len(selected),
            **extraction_metrics(selected),
            "ranking": rank_report(indices),
        }
    metrics = extraction_metrics(cases)
    check_group = "regression" if "regression" in by_split else split
    gated = by_split.get(check_group, metrics)
    checks = {
        "split": check_group,
        "email_accuracy_min": 0.9,
        "experience_mae_years_max": 0.5,
        "skill_f1_min": 0.8,
        "passed": gated["email_accuracy"] >= 0.9
        and gated["experience_mae_years"] <= 0.5
        and gated["skill_f1"] >= 0.8,
        "scope": "Extraction regression thresholds only; not AI quality or ranking certification.",
    }
    code_files = sorted((settings.BASE_DIR / "apps/recruitment/services").rglob("*.py"))
    code_hash = hashlib.sha256(
        b"".join(
            p.relative_to(settings.BASE_DIR).as_posix().encode() + p.read_bytes()
            for p in code_files
        )
    ).hexdigest()
    return {
        "report_version": "evaluation-v2",
        "dataset_version": dataset["version"],
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "implementation_sha256": code_hash,
        "as_of_date": dataset["as_of_date"],
        "python": platform.python_version(),
        "scoring_version": SCORING_VERSION,
        "annotation": dataset.get("annotation", {}),
        "independence_verified": False,
        "selection": {"split": split, "limit": limit, "total_dataset_records": len(all_rows)},
        "records": len(rows),
        "k": k,
        "mode": "live hybrid AI and local baselines"
        if live_ai
        else "offline local extraction and matching; no providers",
        **metrics,
        "confidence_intervals_95": intervals(cases),
        "bootstrap": {
            "samples": 500,
            "seed": 42,
            "method": "Resume-level percentile bootstrap; conditional on this corpus, not population validity.",
        },
        "ranking": rank_report(list(range(len(rows)))),
        "by_split": by_split,
        "failure_cases": [
            c
            for c in cases
            if not c["email_correct"]
            or c["experience_absolute_error"] > 0
            or c["unexpected_skills"]
            or c["missing_skills"]
        ],
        "cases": cases,
        "cross_split_duplicate_documents": overlaps,
        "independent_human_agreement": weighted_kappa(rows),
        "external_requests": calls,
        "external_cost_usd": None if live_ai else 0,
        "successful_ai_scores": ai_successes,
        "score_runs": score_runs,
        "checks": checks,
        "extraction_wall_seconds": round(extraction_seconds, 6),
        "ranking_wall_seconds": round(time.perf_counter() - rank_start, 6),
        "limitations": [
            "Bundled examples and grades are synthetic developer-authored cases, not independent hiring evidence."
            if path.resolve() == (settings.BASE_DIR / "evaluation/dataset.json").resolve()
            else "External dataset provenance and annotator independence are self-reported, not verified.",
            "Cross-split duplicate checks detect normalized identical text, not near-duplicate resumes or label leakage.",
            "Train/validation/test labels alone do not establish an independent held-out study.",
            "Ranking ties use record ID; recall treats grades 2-3 as relevant; no relevant records yields null recall.",
            "Email, experience and skills are measured; education, OCR, multilingual coverage and demographic fairness are not established.",
            "Live models may change. Saved AI scores allow arithmetic replay, not identical future model generations.",
            "Baseline TF-IDF/optional LSA fit the selected corpus; this is a within-corpus ranking comparison.",
        ],
    }
