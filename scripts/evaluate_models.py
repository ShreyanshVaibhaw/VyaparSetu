"""Model evaluation for VyaparSetu classifiers and SNP ranking."""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from sklearn.metrics import confusion_matrix as sk_confusion_matrix
    from sklearn.metrics import precision_recall_fscore_support as sk_prf
    from sklearn.metrics import roc_auc_score as sk_roc_auc_score
except Exception:
    sk_confusion_matrix = None
    sk_prf = None
    sk_roc_auc_score = None

try:
    from config import SNP_MATCH_WEIGHTS
    from src.llm.ollama_client import LLMClient
    from src.sahayakmap.scoring import SNPScorer
    from src.sahayakmap.snp_profiler import SNPProfiler
    from src.udyambodh.business_classifier import BusinessClassifier
    from src.vastrasuchi.product_classifier import ProductClassifier
except Exception as exc:  # pragma: no cover - graceful import failure
    print(f"Import error: {exc}")
    raise SystemExit(1)


@dataclass
class ProductCase:
    description: str
    expected_l1: str


@dataclass
class BusinessCase:
    nic_code: str
    expected_l1: str


@dataclass
class SNPCase:
    mse_name: str
    state: str
    district: str
    pincode: str
    language: str
    categories: list[str]
    products: list[str]
    tech_comfort: str
    expected_snp_id: str


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    arr = np.array(values, dtype=float)
    return float(np.quantile(arr, q))


def _manual_confusion(y_true: list[str], y_pred: list[str], labels: list[str]) -> list[list[int]]:
    idx = {label: i for i, label in enumerate(labels)}
    mat = [[0 for _ in labels] for _ in labels]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            mat[idx[t]][idx[p]] += 1
    return mat


def _manual_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    matrix = _manual_confusion(y_true, y_pred, labels)
    per_class: dict[str, dict[str, float]] = {}
    supports: dict[str, int] = {}
    f1_scores: list[float] = []
    precisions: list[float] = []
    recalls: list[float] = []

    total = sum(sum(r) for r in matrix)
    correct = sum(matrix[i][i] for i in range(len(labels)))

    for i, label in enumerate(labels):
        tp = matrix[i][i]
        fp = sum(matrix[r][i] for r in range(len(labels)) if r != i)
        fn = sum(matrix[i][c] for c in range(len(labels)) if c != i)
        support = sum(matrix[i])
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)

        per_class[label] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": int(support),
        }
        supports[label] = support
        f1_scores.append(f1)
        precisions.append(precision)
        recalls.append(recall)

    weighted_f1 = _safe_div(
        sum(per_class[label]["f1"] * supports[label] for label in labels),
        sum(supports.values()),
    )

    return {
        "accuracy": round(_safe_div(correct, total), 6),
        "macro_precision": round(float(np.mean(precisions)) if precisions else 0.0, 6),
        "macro_recall": round(float(np.mean(recalls)) if recalls else 0.0, 6),
        "macro_f1": round(float(np.mean(f1_scores)) if f1_scores else 0.0, 6),
        "weighted_f1": round(weighted_f1, 6),
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def _binary_auc(y_true_bin: list[int], y_score: list[float]) -> float:
    pos = [(score, label) for score, label in zip(y_score, y_true_bin) if label == 1]
    neg = [(score, label) for score, label in zip(y_score, y_true_bin) if label == 0]
    n_pos = len(pos)
    n_neg = len(neg)
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    ranked = sorted([(s, i) for i, s in enumerate(y_score)], key=lambda x: x[0])
    ranks = [0.0] * len(y_score)
    i = 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[ranked[k][1]] = avg_rank
        i = j + 1

    sum_pos_ranks = sum(r for r, label in zip(ranks, y_true_bin) if label == 1)
    auc = (sum_pos_ranks - (n_pos * (n_pos + 1) / 2.0)) / (n_pos * n_neg)
    return float(auc)


def _compute_auc_ovr(y_true: list[str], labels: list[str], score_matrix: list[list[float]]) -> dict[str, float]:
    auc_map: dict[str, float] = {}
    if sk_roc_auc_score is not None:
        y_true_arr = np.array(y_true)
        score_arr = np.array(score_matrix, dtype=float)
        for idx, label in enumerate(labels):
            y_bin = (y_true_arr == label).astype(int)
            if y_bin.sum() == 0 or y_bin.sum() == len(y_bin):
                auc_map[label] = float("nan")
                continue
            try:
                auc_map[label] = float(sk_roc_auc_score(y_bin, score_arr[:, idx]))
            except Exception:
                auc_map[label] = float("nan")
        return auc_map

    for idx, label in enumerate(labels):
        y_bin = [1 if item == label else 0 for item in y_true]
        auc_map[label] = _binary_auc(y_bin, [row[idx] for row in score_matrix])
    return auc_map


def _load_json(path: Path, default: Any) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload
    except Exception:
        return default


def _stateful_paths() -> dict[str, Path]:
    data = ROOT / "data"
    return {
        "categories": data / "ondc_taxonomy" / "categories.json",
        "hsn": data / "ondc_taxonomy" / "hsn_mapping.json",
        "nic": data / "ondc_taxonomy" / "nic_to_ondc.json",
        "snp_db": data / "snp_profiles" / "snp_database.json",
        "snp_perf": data / "snp_profiles" / "snp_performance.json",
    }


def _product_cases() -> list[ProductCase]:
    rows = [
        ("Mango Pickle 500g homemade achaar", "Food & Beverage"),
        ("Lemon pickle spicy chutney jar", "Food & Beverage"),
        ("Turmeric powder masala organic", "Food & Beverage"),
        ("Red chilli powder spice mix", "Food & Beverage"),
        ("Masala tea premix beverage", "Food & Beverage"),
        ("South filter coffee powder", "Food & Beverage"),
        ("Baked cookies butter snack", "Food & Beverage"),
        ("Traditional mithai sweets box", "Food & Beverage"),
        ("Ready to eat poha meal pack", "Food & Beverage"),
        ("Fruit juice beverage tetra pack", "Food & Beverage"),
        ("Basmati rice grocery basics", "Grocery"),
        ("Toor dal pulses grocery pack", "Grocery"),
        ("Wheat atta flour grocery", "Grocery"),
        ("Cold pressed cooking oil ghee", "Grocery"),
        ("Agarbatti dhoop puja needs", "Grocery"),
        ("Garbage bags daily essentials", "Grocery"),
        ("Laundry detergent household cleaning", "Grocery"),
        ("Camphor pooja oil cotton wicks", "Grocery"),
        ("Women silk saree zari border", "Fashion"),
        ("Cotton salwar kurta set", "Fashion"),
        ("Handbag leather accessories bag wallet", "Fashion"),
        ("Men shirt trousers apparel", "Fashion"),
        ("Kids winterwear jacket", "Fashion"),
        ("Fashion jewellery necklace", "Fashion"),
        ("Belts scarves stoles accessories", "Fashion"),
        ("Sports shoes footwear pair", "Fashion"),
        ("Cotton bedsheet furnishing", "Home & Kitchen"),
        ("Steel utensil cookware kitchen tool", "Home & Kitchen"),
        ("Storage container kitchen", "Home & Kitchen"),
        ("Wooden chair furniture", "Home & Kitchen"),
        ("Wall art handcrafted decor", "Home & Kitchen"),
        ("Brass metal crafts home decor", "Home & Kitchen"),
        ("Carpet rugs furnishing", "Home & Kitchen"),
        ("Garden planter pot", "Home & Kitchen"),
        ("LED bulb electricals", "Electronics"),
        ("Mobile charger fast charging", "Electronics"),
        ("Wireless earphones audio", "Electronics"),
        ("Power bank mobile accessories", "Electronics"),
        ("Laptop monitor computer peripherals", "Electronics"),
        ("USB drive storage electronics", "Electronics"),
        ("Water purifier home appliances", "Electronics"),
        ("Emergency light inverter", "Electronics"),
        ("Ayurvedic herbal supplements", "Health & Wellness"),
        ("Yoga mat fitness equipment", "Health & Wellness"),
        ("First aid medical essentials", "Health & Wellness"),
        ("Herbal tea immunity booster", "Health & Wellness"),
        ("Skincare body care personal care", "Health & Wellness"),
        ("Handmade soap bath body", "Beauty & Personal Care"),
        ("Hair oil serum styling", "Beauty & Personal Care"),
        ("Face cream moisturizer skincare", "Beauty & Personal Care"),
        ("Lipstick makeup beauty", "Beauty & Personal Care"),
        ("Perfume deodorant fragrances", "Beauty & Personal Care"),
        ("Vegetable seeds hybrid seeds", "Agriculture"),
        ("Organic fertilizer farm inputs", "Agriculture"),
        ("Bio pesticide fungicide", "Agriculture"),
        ("Irrigation pump tools equipment", "Agriculture"),
        ("Compost cocopeat farm input", "Agriculture"),
        ("Jute bag handicraft eco gift", "Handicrafts & Handloom"),
        ("Handloom saree artisanal textile", "Handicrafts & Handloom"),
        ("Wooden crafts bamboo cane item", "Handicrafts & Handloom"),
    ]
    return [ProductCase(description=d, expected_l1=e) for d, e in rows]


def _business_cases() -> list[BusinessCase]:
    rows = [
        ("10", "Food & Beverage"),
        ("11", "Food & Beverage"),
        ("12", "Grocery"),
        ("13", "Fashion"),
        ("14", "Fashion"),
        ("15", "Fashion"),
        ("16", "Home & Kitchen"),
        ("17", "Stationery & Books"),
        ("18", "Stationery & Books"),
        ("20", "Health & Wellness"),
        ("21", "Health & Wellness"),
        ("22", "Home & Kitchen"),
        ("23", "Handicrafts & Handloom"),
        ("24", "Handicrafts & Handloom"),
        ("25", "Home & Kitchen"),
        ("26", "Electronics"),
        ("27", "Electronics"),
        ("28", "Agriculture"),
        ("31", "Home & Kitchen"),
        ("32", "Handicrafts & Handloom"),
        ("33", "Services"),
        ("41", "Services"),
        ("42", "Services"),
        ("43", "Services"),
        ("46", "Grocery"),
        ("47", "Food & Beverage"),
        ("49", "Services"),
        ("52", "Services"),
        ("56", "Services"),
        ("62", "Services"),
        ("75", "Agriculture"),
        ("85", "Services"),
        ("86", "Health & Wellness"),
        ("90", "Handicrafts & Handloom"),
        ("96", "Beauty & Personal Care"),
    ]
    return [BusinessCase(nic_code=nic, expected_l1=exp) for nic, exp in rows]


def _snp_cases() -> list[SNPCase]:
    return [
        SNPCase("Maru Pickles", "Rajasthan", "Jaipur", "302001", "hi", ["Food & Beverage"], ["pickle", "papad"], "low", "SNP001"),
        SNPCase("Kanchi Sarees", "Tamil Nadu", "Chennai", "600001", "ta", ["Fashion"], ["silk saree"], "medium", "SNP021"),
        SNPCase("Moradabad Brass", "Uttar Pradesh", "Moradabad", "244001", "hi", ["Handicrafts & Handloom"], ["brass decor"], "medium", "SNP026"),
        SNPCase("Bengaluru Repairs", "Karnataka", "Bengaluru Urban", "560001", "en", ["Electronics", "Services"], ["repair service"], "high", "SNP014"),
        SNPCase("Northeast Basket", "Assam", "Guwahati", "781001", "en", ["Food & Beverage"], ["regional snacks"], "medium", "SNP022"),
        SNPCase("Women Beauty Hub", "Maharashtra", "Mumbai", "400001", "mr", ["Beauty & Personal Care"], ["face wash"], "low", "SNP019"),
        SNPCase("Punjab Agri Inputs", "Punjab", "Ludhiana", "141001", "hi", ["Agriculture"], ["seeds fertilizer"], "medium", "SNP012"),
        SNPCase("Kerala Spices", "Kerala", "Ernakulam", "682001", "en", ["Food & Beverage"], ["spice mix"], "low", "SNP017"),
        SNPCase("Delhi Hyperlocal", "Delhi", "New Delhi", "110001", "hi", ["Services"], ["local services"], "low", "SNP023"),
        SNPCase("Gujarat Handloom", "Gujarat", "Ahmedabad", "380001", "gu", ["Handicrafts & Handloom", "Fashion"], ["khadi"], "medium", "SNP015"),
        SNPCase("UP Grocery Chain", "Uttar Pradesh", "Lucknow", "226001", "hi", ["Grocery"], ["daily essentials"], "low", "SNP024"),
        SNPCase("Pan India Books", "West Bengal", "Kolkata", "700001", "bn", ["Stationery & Books"], ["notebooks"], "medium", "SNP016"),
        SNPCase("Rural Seeds", "Madhya Pradesh", "Bhopal", "462001", "hi", ["Agriculture", "Food & Beverage"], ["seeds"], "low", "SNP011"),
        SNPCase("Urban Food Chain", "Karnataka", "Bengaluru Urban", "560001", "kn", ["Food & Beverage", "Grocery"], ["beverage"], "medium", "SNP009"),
        SNPCase("Electro Retail", "Maharashtra", "Pune", "411001", "en", ["Electronics"], ["led bulbs"], "high", "SNP025"),
        SNPCase("Service Aggregator", "Telangana", "Hyderabad", "500001", "te", ["Services", "Home & Kitchen"], ["home service"], "medium", "SNP023"),
        SNPCase("South Agri Market", "Telangana", "Hyderabad", "500001", "te", ["Agriculture", "Food & Beverage"], ["farm produce"], "low", "SNP004"),
        SNPCase("Pan India Fashion", "Bihar", "Patna", "800001", "hi", ["Fashion", "Beauty & Personal Care"], ["women apparel"], "low", "SNP007"),
        SNPCase("Craft Marketplace", "Rajasthan", "Jodhpur", "342001", "hi", ["Handicrafts & Handloom", "Home & Kitchen"], ["wood craft"], "medium", "SNP018"),
        SNPCase("Bharat Bazaar", "Odisha", "Bhubaneswar", "751001", "or", ["Food & Beverage", "Grocery", "Fashion"], ["mixed catalog"], "low", "SNP010"),
    ]


def evaluate_product_classifier(llm: LLMClient) -> dict[str, Any]:
    paths = _stateful_paths()
    classifier = ProductClassifier(
        categories_path=str(paths["categories"]),
        hsn_mapping_path=str(paths["hsn"]),
        llm_client=llm,
    )

    cases = _product_cases()
    y_true: list[str] = []
    y_pred: list[str] = []
    latencies: list[float] = []

    labels = sorted({case.expected_l1 for case in cases})
    score_rows: list[list[float]] = []

    for case in cases:
        start = time.perf_counter()
        result = classifier.classify(case.description)
        elapsed = time.perf_counter() - start

        pred = str(result.get("l1", ""))
        conf = float(result.get("confidence", 0.0) or 0.0)
        conf = max(0.0, min(1.0, conf))

        y_true.append(case.expected_l1)
        y_pred.append(pred)
        latencies.append(elapsed)

        if pred in labels and len(labels) > 1:
            off = _safe_div(1.0 - conf, len(labels) - 1)
            score_rows.append([conf if label == pred else off for label in labels])
        else:
            uniform = _safe_div(1.0, max(len(labels), 1))
            score_rows.append([uniform for _ in labels])

    if sk_prf is not None and sk_confusion_matrix is not None:
        accuracy = round(_safe_div(sum(1 for t, p in zip(y_true, y_pred) if t == p), len(y_true)), 6)
        p, r, f, support = sk_prf(y_true, y_pred, labels=labels, average=None, zero_division=0)
        p_macro, r_macro, f_macro, _ = sk_prf(y_true, y_pred, labels=labels, average="macro", zero_division=0)
        _, _, f_weighted, _ = sk_prf(y_true, y_pred, labels=labels, average="weighted", zero_division=0)

        per_class = {
            label: {
                "precision": round(float(p[idx]), 6),
                "recall": round(float(r[idx]), 6),
                "f1": round(float(f[idx]), 6),
                "support": int(support[idx]),
            }
            for idx, label in enumerate(labels)
        }
        confusion = sk_confusion_matrix(y_true, y_pred, labels=labels).astype(int).tolist()

        metrics = {
            "accuracy": float(accuracy),
            "macro_precision": round(float(p_macro), 6),
            "macro_recall": round(float(r_macro), 6),
            "macro_f1": round(float(f_macro), 6),
            "weighted_f1": round(float(f_weighted), 6),
            "per_class": per_class,
            "confusion_matrix": confusion,
        }
    else:
        metrics = _manual_metrics(y_true, y_pred, labels)

    auc_by_class = _compute_auc_ovr(y_true, labels, score_rows)
    auc_clean = {label: (None if math.isnan(score) else round(float(score), 6)) for label, score in auc_by_class.items()}

    return {
        "accuracy": metrics["accuracy"],
        "macro_precision": metrics["macro_precision"],
        "macro_recall": metrics["macro_recall"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "per_class_f1": {k: float(v["f1"]) for k, v in metrics["per_class"].items()},
        "auc_roc": auc_clean,
        "confusion_matrix": metrics["confusion_matrix"],
        "class_labels": labels,
        "inference_latency_mean_sec": round(float(statistics.mean(latencies)) if latencies else 0.0, 6),
        "inference_latency_p50_sec": round(_quantile(latencies, 0.50), 6),
        "inference_latency_p95_sec": round(_quantile(latencies, 0.95), 6),
        "num_samples": len(cases),
    }


def evaluate_business_classifier(llm: LLMClient) -> dict[str, Any]:
    paths = _stateful_paths()
    classifier = BusinessClassifier(
        llm_client=llm,
        nic_to_ondc_path=str(paths["nic"]),
        categories_path=str(paths["categories"]),
    )

    cases = _business_cases()
    hits = 0
    covered = 0
    for case in cases:
        predicted = classifier.classify_from_nic(case.nic_code)
        if predicted:
            covered += 1
        if case.expected_l1 in predicted:
            hits += 1

    return {
        "accuracy": round(_safe_div(hits, len(cases)), 6),
        "coverage": round(_safe_div(covered, len(cases)), 6),
        "num_samples": len(cases),
    }


def _rank_snps(case: SNPCase, scorer: SNPScorer, snps: list[Any]) -> list[tuple[str, float]]:
    commissions = [float(s.commission_rate) for s in snps]
    ranked: list[tuple[str, float]] = []

    for snp in snps:
        scores = {
            "domain": scorer.score_domain(case.categories, snp.supported_categories, snp.specialization_tags, case.products),
            "geography": scorer.score_geography(case.state, case.district, snp.geographic_coverage, snp.pincode_coverage or [], case.pincode),
            "language": scorer.score_language(case.language, snp.languages_supported),
            "cost": scorer.score_cost(float(snp.commission_rate), float(snp.monthly_fee), commissions),
            "performance": scorer.score_performance(float(snp.seller_success_rate), int(snp.avg_activation_days), float(snp.rating)),
            "tech_fit": scorer.score_tech_fit(case.tech_comfort, snp.platform_type, snp.catalog_upload_method, snp.seller_support),
        }
        total = scorer.calculate_total(scores)
        ranked.append((snp.snp_id, float(total)))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def evaluate_snp_scorer() -> dict[str, Any]:
    paths = _stateful_paths()
    profiler = SNPProfiler(
        snp_database_path=str(paths["snp_db"]),
        snp_performance_path=str(paths["snp_perf"]),
    )
    scorer = SNPScorer(SNP_MATCH_WEIGHTS)

    snps = profiler.get_all_snps()
    cases = _snp_cases()

    top3_hits = 0
    rr_values: list[float] = []

    for case in cases:
        ranked = _rank_snps(case, scorer, snps)
        top_ids = [item[0] for item in ranked[:3]]
        if case.expected_snp_id in top_ids:
            top3_hits += 1

        rr = 0.0
        for idx, (snp_id, _) in enumerate(ranked, start=1):
            if snp_id == case.expected_snp_id:
                rr = 1.0 / idx
                break
        rr_values.append(rr)

    return {
        "top3_accuracy": round(_safe_div(top3_hits, len(cases)), 6),
        "mrr": round(float(np.mean(rr_values)) if rr_values else 0.0, 6),
        "num_samples": len(cases),
    }


def _build_markdown(report: dict[str, Any]) -> str:
    product = report["product_classifier"]
    business = report["business_classifier"]
    snp = report["snp_scorer"]

    per_class_rows = [
        f"| {label} | {score:.4f} |"
        for label, score in sorted(product["per_class_f1"].items())
    ]
    auc_rows = [
        f"| {label} | {('N/A' if value is None else f'{value:.4f}')} |"
        for label, value in sorted(product["auc_roc"].items())
    ]

    return "\n".join(
        [
            "# VyaparSetu Model Evaluation Report",
            "",
            f"Generated at: `{report['generated_at']}`",
            "",
            "## Summary",
            "",
            "| Model | Metric | Value |",
            "|---|---:|---:|",
            f"| Product Classifier | Accuracy | {product['accuracy']:.4f} |",
            f"| Product Classifier | Macro Precision | {product['macro_precision']:.4f} |",
            f"| Product Classifier | Macro Recall | {product['macro_recall']:.4f} |",
            f"| Product Classifier | Macro F1 | {product['macro_f1']:.4f} |",
            f"| Product Classifier | Weighted F1 | {product['weighted_f1']:.4f} |",
            f"| Product Classifier | Latency Mean (s) | {product['inference_latency_mean_sec']:.4f} |",
            f"| Product Classifier | Latency P50 (s) | {product['inference_latency_p50_sec']:.4f} |",
            f"| Product Classifier | Latency P95 (s) | {product['inference_latency_p95_sec']:.4f} |",
            f"| Business Classifier | Accuracy | {business['accuracy']:.4f} |",
            f"| Business Classifier | Coverage | {business['coverage']:.4f} |",
            f"| SNP Scorer | Top-3 Accuracy | {snp['top3_accuracy']:.4f} |",
            f"| SNP Scorer | MRR | {snp['mrr']:.4f} |",
            "",
            "## Product Classifier Per-Class F1",
            "",
            "| Class | F1 |",
            "|---|---:|",
            *per_class_rows,
            "",
            "## Product Classifier One-vs-Rest AUC-ROC",
            "",
            "| Class | AUC-ROC |",
            "|---|---:|",
            *auc_rows,
            "",
            "## Confusion Matrix",
            "",
            f"Labels (rows=true, cols=pred): `{', '.join(product['class_labels'])}`",
            "",
            "```text",
            pd.DataFrame(product["confusion_matrix"], index=product["class_labels"], columns=product["class_labels"]).to_string(),
            "```",
        ]
    )


def _print_console_summary(report: dict[str, Any]) -> None:
    product = report["product_classifier"]
    business = report["business_classifier"]
    snp = report["snp_scorer"]

    table = pd.DataFrame(
        [
            ["Product Classifier", "Accuracy", product["accuracy"]],
            ["Product Classifier", "Macro F1", product["macro_f1"]],
            ["Product Classifier", "Weighted F1", product["weighted_f1"]],
            ["Product Classifier", "Latency Mean (s)", product["inference_latency_mean_sec"]],
            ["Product Classifier", "Latency P95 (s)", product["inference_latency_p95_sec"]],
            ["Business Classifier", "Accuracy", business["accuracy"]],
            ["Business Classifier", "Coverage", business["coverage"]],
            ["SNP Scorer", "Top-3 Accuracy", snp["top3_accuracy"]],
            ["SNP Scorer", "MRR", snp["mrr"]],
        ],
        columns=["Model", "Metric", "Value"],
    )
    print("\nVyaparSetu Model Evaluation")
    print(table.to_string(index=False))


def main() -> int:
    outputs_dir = ROOT / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    llm = LLMClient()
    # Force demo fallback path to avoid repeated network timeouts when Ollama is unavailable.
    try:
        llm.health_check = lambda: False  # type: ignore[method-assign]
    except Exception:
        pass

    product_metrics = evaluate_product_classifier(llm)
    business_metrics = evaluate_business_classifier(llm)
    snp_metrics = evaluate_snp_scorer()

    report = {
        "product_classifier": product_metrics,
        "business_classifier": business_metrics,
        "snp_scorer": snp_metrics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    json_path = outputs_dir / "model_evaluation_report.json"
    md_path = outputs_dir / "model_evaluation_report.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_build_markdown(report), encoding="utf-8")

    _print_console_summary(report)
    print(f"\nSaved: {json_path}")
    print(f"Saved: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
