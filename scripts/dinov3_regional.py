"""Geometric crown comparisons and exact specimen-level evaluation; no fitting."""

import itertools
import math
import numpy as np

from dinov3_pipeline import normalize


def regional_features(tokens, coverage):
    coverage = np.asarray(coverage, dtype=float)
    tokens = np.asarray(tokens)
    if (coverage.ndim != 2 or tokens.ndim != 2 or len(tokens) != coverage.size
            or not np.isfinite(coverage).all() or np.any((coverage < 0) | (coverage > 1))):
        raise ValueError("Invalid spatial tokens or crown coverage")
    selected = np.flatnonzero(coverage.ravel() >= .5)
    if len(selected) < 3:
        raise ValueError("Too few crown patches")
    y, x = np.unravel_index(selected, coverage.shape)
    xy = np.column_stack([x + .5, y + .5]) * 16
    weights = coverage.ravel()[selected]
    centered = xy - np.average(xy, axis=0, weights=weights)
    covariance = (centered * weights[:, None]).T @ centered / weights.sum()
    values, axes = np.linalg.eigh(covariance)
    axis = axes[:, -1]
    if axis[np.argmax(np.abs(axis))] < 0:
        axis = -axis
    projected = centered @ axis
    span = np.ptp(projected)
    if span <= 0:
        raise ValueError("Degenerate crown axis")
    bands = np.minimum(((projected - projected.min()) / span * 3).astype(int), 2)
    if set(bands) != {0, 1, 2}:
        raise ValueError("Each geometric region must contain crown patches")
    vectors = normalize(tokens[selected])
    means = normalize(np.stack([np.average(vectors[bands == k], axis=0,
                                           weights=weights[bands == k]) for k in range(3)]))
    return {"vectors": vectors, "weights": weights, "bands": bands, "xy": xy,
            "indices": selected, "means": means, "axis": axis,
            "axis_eigenvalue_ratio": float(values[-1] / max(values[0], 1e-12)),
            "region_patch_counts": [int(sum(bands == k)) for k in range(3)]}


def compare_regions(a, b, method):
    if method not in ("regional_mean", "regional_patch"):
        raise ValueError("Unknown regional method")
    cosine = a["vectors"] @ b["vectors"].T if method == "regional_patch" else None
    alternatives = []
    for reverse in (False, True):
        scores = []
        for k in range(3):
            l = 2-k if reverse else k
            if cosine is None:
                score = a["means"][k] @ b["means"][l]
            else:
                ia, ib = np.flatnonzero(a["bands"] == k), np.flatnonzero(b["bands"] == l)
                block = cosine[np.ix_(ia, ib)]
                score = (np.average(block.max(axis=1), weights=a["weights"][ia])
                         + np.average(block.max(axis=0), weights=b["weights"][ib])) / 2
            scores.append(float(score))
        alternatives.append({"score": float(np.mean(scores)), "reversed": reverse,
                             "region_scores": scores})
    return max(alternatives, key=lambda r: r["score"])


def mutual_matches(a, b, reverse):
    """All within-band reciprocal best matches; no arbitrary feature threshold."""
    matches = []
    for k in range(3):
        ia = np.flatnonzero(a["bands"] == k)
        ib = np.flatnonzero(b["bands"] == (2-k if reverse else k))
        block = a["vectors"][ia] @ b["vectors"][ib].T
        ab, ba = block.argmax(axis=1), block.argmax(axis=0)
        for i, j in enumerate(ab):
            if ba[j] == i:
                matches.append((int(ia[i]), int(ib[j]), float(block[i, j]), k))
    return sorted(matches, key=lambda m: (-m[2], m[0], m[1]))


def specimen_similarity(image_scores, records, specimens):
    """Average all cross-image pairs, excluding the entire query catalog ID."""
    scores = np.asarray(image_scores)
    if scores.shape != (len(records), len(records)):
        raise ValueError("Image score inventory mismatch")
    ids = [s["specimen_id"] for s in specimens]
    if len(ids) != len(set(ids)) or set(ids) != {r["specimen_id"] for r in records}:
        raise ValueError("Require complete distinct specimen inventory")
    groups = [[i for i, r in enumerate(records) if r["specimen_id"] == sid] for sid in ids]
    result = np.zeros((len(ids), len(ids)), dtype=float)
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            values = scores[np.ix_(groups[i], groups[j])]
            if not np.isfinite(values).all():
                raise ValueError("Missing cross-specimen scores")
            result[i, j] = result[j, i] = values.mean()
    return result


def label_assignments(counts):
    """Enumerate each distinct allocation of fixed label counts exactly once."""
    counts = list(counts)
    labels = np.empty(sum(counts), dtype=int)

    def assign(label, remaining):
        if label == len(counts)-1:
            labels[list(remaining)] = label
            yield labels.copy()
            return
        for subset in itertools.combinations(remaining, counts[label]):
            labels[list(subset)] = label
            chosen = set(subset)
            yield from assign(label+1, tuple(i for i in remaining if i not in chosen))

    yield from assign(0, tuple(range(len(labels))))


def exact_retrieval(similarity, rows, labels):
    similarity = np.array(similarity, dtype=float, copy=True)
    n = len(rows)
    if (n < 2 or similarity.shape != (n, n) or len(labels) != n
            or len({r["specimen_id"] for r in rows}) != n
            or not np.isfinite(similarity).all()
            or not np.allclose(similarity, similarity.T)):
        raise ValueError("Require finite symmetric scores and unique specimen IDs")
    # A tie must never prefer a site because its rows sort first.
    order = np.argsort([r["specimen_id"] for r in rows], kind="stable")
    np.fill_diagonal(similarity, -np.inf)
    nearest = order[np.argmax(similarity[:, order], axis=1)]
    names, encoded, counts = np.unique(labels, return_inverse=True, return_counts=True)
    supported = np.flatnonzero(counts >= 2)
    if len(supported) < 2:
        raise ValueError("Need at least two supported groups")
    total = math.factorial(n) // math.prod(math.factorial(int(c)) for c in counts)
    if total > 100000:
        raise ValueError("Too many assignments for exact enumeration")

    def score(current):
        correct = current == current[nearest]
        return float(np.mean([correct[current == k].mean() for k in supported]))

    observed = score(encoded)
    exceed = sum(score(current) >= observed-1e-12 for current in label_assignments(counts))
    correct = encoded == encoded[nearest]
    eligible = np.isin(encoded, supported)
    per_group = {str(name): {"specimens": int(counts[k]), "eligible": bool(k in supported),
                             "correct": int(correct[encoded == k].sum()) if k in supported else None,
                             "recall": float(correct[encoded == k].mean()) if k in supported else None}
                 for k, name in enumerate(names)}
    return {"macro_recall": observed, "ordinary_accuracy": float(correct[eligible].mean()),
            "correct": int(correct[eligible].sum()), "eligible_specimens": int(eligible.sum()),
            "per_group": per_group, "majority_macro_baseline": 1/len(supported),
            "majority_accuracy_baseline": float(max(counts[supported])/eligible.sum()),
            "exact_p": exceed/total, "assignments": total, "nearest_indices": nearest.tolist()}
