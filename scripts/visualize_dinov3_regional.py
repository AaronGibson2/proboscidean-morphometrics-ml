"""Explain saved regional results with charts; never rerun or modify the analysis."""

import hashlib
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/results/regional-results-v1.json"
FIGURES = ROOT / "docs/results/regional-figures"
LOCAL = ROOT / "outputs/dinov3_regional_v1"
METHODS = ("cls", "regional_mean", "regional_patch")
NAMES = {"cls": "Whole image (original)", "regional_mean": "Three-region averages",
         "regional_patch": "Patch-to-patch matching"}
INK, GREEN, ORANGE, GRAY = "#172d43", "#167b63", "#c95b32", "#758392"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK,
                     "svg.fonttype": "none", "savefig.facecolor": "white"})


def short_name(name):
    if name == "Mixson + Tyner":
        return name
    return next(label for label in ("Love", "Mixson", "Tyner") if label in name)


def save(fig, name):
    for suffix in ("png", "svg"):
        fig.savefig(FIGURES / f"{name}.{suffix}", dpi=160)
    plt.close(fig)


def ordered_groups(row):
    order = {"Love": 0, "Mixson": 1, "Tyner": 2, "Mixson + Tyner": 1}
    return sorted(row["per_group"].items(), key=lambda pair: order[short_name(pair[0])])


def dots(ax, row):
    groups = ordered_groups(row)
    for y, (name, group) in enumerate(groups):
        count = group["specimens"]
        if group["eligible"]:
            correct = group["correct"]
            ax.scatter(np.arange(1, correct+1), [y]*correct, s=60, c=GREEN, marker="o")
            ax.scatter(np.arange(correct+1, count+1), [y]*(count-correct), s=65,
                       c=ORANGE, marker="x", linewidths=2)
            label = f"{correct}/{count}"
        else:
            ax.scatter(np.arange(1, count+1), [y]*count, s=60,
                       facecolors="none", edgecolors=GRAY, linewidths=1.5)
            label = "Not scored"
        ax.text(13.2, y, label, va="center", fontsize=10, color=INK)
    ax.set_yticks(range(len(groups)), [short_name(name) for name, _ in groups])
    ax.set_ylim(len(groups)-.35, -.65)
    ax.set_xlim(.2, 16)
    ax.set_xticks([])
    ax.tick_params(axis="y", length=0, pad=8)
    for spine in ax.spines.values():
        spine.set_visible(False)


def count_charts(lookup, target, name, title):
    fig, axes = plt.subplots(2, 3, figsize=(17, 8.8))
    fig.subplots_adjust(left=.085, right=.985, top=.75, bottom=.16, wspace=.43, hspace=.85)
    fig.suptitle(title, fontsize=22, fontweight="bold", x=.045, ha="left", y=.96)
    fig.text(.045, .90, "Each symbol is one catalog ID in that evaluation. Green = same-group neighbor; orange = different-group neighbor.", fontsize=12)
    handles = [Line2D([], [], color=GREEN, marker="o", linestyle="none", label="Matched correctly"),
               Line2D([], [], color=ORANGE, marker="x", linestyle="none", label="Matched a different group")]
    if target == "locality":
        handles.append(Line2D([], [], color=GRAY, marker="o", markerfacecolor="white",
                              linestyle="none", label="Cannot score (no same-site reference)"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.04, .87), ncol=3, frameon=False, fontsize=11)
    for position, axrow in zip(("upper", "lower"), axes):
        for method, ax in zip(METHODS, axrow):
            r = lookup[position, target, method]
            dots(ax, r)
            ax.set_title(f'{position.title()} teeth | {NAMES[method]}\n{r["correct"]} of {r["eligible_specimens"]} correct overall',
                         loc="left", pad=14, fontsize=11, fontweight="bold", linespacing=1.7)
    if target == "locality":
        footer = "Upper Tyner has one catalog ID, so it cannot find another independent Tyner reference. It is unscored, not counted as a failure."
    else:
        footer = "Mixson + Tyner is a provisional grouping, not a verified species label. Upper Tyner is eligible here because it can match Mixson."
    fig.text(.045, .075, footer, fontsize=11)
    fig.text(.045, .035, "Dots show counts, not individual identities. The same specimens appear again in each method; these are not independent samples.", fontsize=10, color=GRAY)
    save(fig, name)


def balanced_chart(lookup):
    fig, axes = plt.subplots(2, 2, figsize=(15, 10.5))
    fig.subplots_adjust(left=.20, right=.95, top=.79, bottom=.15, wspace=.60, hspace=.77)
    fig.suptitle("Did the new methods improve the balance across groups?", fontsize=21,
                 fontweight="bold", x=.045, ha="left", y=.96)
    fig.text(.045, .91, "Balanced score = average of the groups' success rates. Every eligible group gets equal weight.", fontsize=12)
    fig.text(.045, .865, "Compare methods within each panel. Original localities and the proposed two-group question are different tasks.", fontsize=11)
    for col, target in enumerate(("locality", "provisional_group")):
        for row, position in enumerate(("upper", "lower")):
            ax = axes[row, col]
            rows = [lookup[position, target, m] for m in METHODS]
            values = [r['macro_recall']*100 for r in rows]
            ax.barh(range(3), values, height=.55, color=["#354f6d", "#258b91", "#8a6ca8"], zorder=3)
            for y, value in enumerate(values):
                ax.text(value+1.6, y, f"{value:.1f}%", va="center", fontsize=12, fontweight="bold",
                        zorder=5, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
            baseline = rows[0]['majority_macro_baseline']*100
            ax.axvline(baseline, color=ORANGE, linestyle="--", linewidth=1.6, zorder=4)
            ax.set_xlim(0, 105)
            ax.set_ylim(2.65, -.6)
            ax.set_xticks([0, 25, 50, 75, 100], ['0%', '25%', '50%', '75%', '100%'])
            ax.set_yticks(range(3), ["Whole image\n(original)", "Three-region\naverages", "Patch-to-patch\nmatching"])
            question = "Original localities" if target == "locality" else "Love vs Mixson + Tyner"
            ax.set_title(f"{position.title()} teeth | {question}", loc="left", pad=20, fontsize=12, fontweight="bold")
            ax.grid(axis="x", color="#e4e9ee", zorder=0)
            ax.tick_params(length=0, pad=8)
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.text(0, -.26, f"Dashed line: always choosing Love = {baseline:.1f}%", transform=ax.transAxes, fontsize=10, color=ORANGE)
    fig.text(.045, .065, "Small sample, repeated use of the same specimens. The slight upper-locality gain is descriptive; no corrected test meets 0.05.", fontsize=11)
    fig.text(.045, .025, "The dashed line is a simple benchmark, not a statistical significance threshold. No species-identification accuracy is measured here.", fontsize=10, color=GRAY)
    save(fig, 'balanced-scores')


def imbalance_example(lookup):
    r = lookup['lower', 'locality', 'cls']
    fig = plt.figure(figsize=(12, 6.4))
    fig.text(.06, .91, "Why 75% overall can still be a poor result", fontsize=23, fontweight="bold")
    fig.text(.06, .845, "Lower teeth, original whole-image method: every specimen's nearest neighbor comes from Love.", fontsize=12)
    ax = fig.add_axes([.12, .40, .80, .32])
    dots(ax, r)
    fig.text(.08, .27, f'Overall: {r["correct"]}/{r["eligible_specimens"]} = {r["ordinary_accuracy"]:.0%}', fontsize=19, fontweight="bold")
    fig.text(.52, .27, f'Balanced: (100% + 0% + 0%) / 3 = {r["macro_recall"]:.1%}', fontsize=15, fontweight="bold")
    fig.text(.08, .18, "Love supplies most of the specimens, so it dominates the overall score.", fontsize=12)
    fig.text(.08, .115, "But zero Mixson and zero Tyner specimens find a same-site neighbor. This method is not separating all three sites.", fontsize=12)
    fig.text(.08, .045, "Green circle = correct neighbor group. Orange cross = wrong neighbor group. One symbol = one catalog ID.", fontsize=10, color=GRAY)
    save(fig, 'why-overall-misleads')


def main():
    original = SOURCE.read_bytes()
    results = json.loads(original)['results']
    lookup = {(r['position'], r['target'], r['method']): r for r in results}
    expected = {(p, t, m) for p in ('upper', 'lower') for t in ('locality', 'provisional_group') for m in METHODS}
    if set(lookup) != expected or len(results) != 12:
        raise ValueError('Require the complete fixed twelve-condition result table')
    for r in results:
        eligible = [g for g in r['per_group'].values() if g['eligible']]
        assert sum(g['correct'] for g in eligible) == r['correct']
        assert sum(g['specimens'] for g in eligible) == r['eligible_specimens']
        assert np.isclose(np.mean([g['correct']/g['specimens'] for g in eligible]), r['macro_recall'])
    FIGURES.mkdir(parents=True, exist_ok=True)
    imbalance_example(lookup)
    count_charts(lookup, 'locality', 'locality-counts', 'Which teeth found a neighbor from the same site?')
    count_charts(lookup, 'provisional_group', 'group-counts', 'Does Love separate from the proposed Mixson + Tyner group?')
    balanced_chart(lookup)
    (FIGURES / 'provenance.json').write_text(json.dumps({
        'source': SOURCE.relative_to(ROOT).as_posix(),
        'source_sha256': hashlib.sha256(original).hexdigest(),
        'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'conditions': 12, 'analysis_rerun': False,
        'note': 'Descriptive displays of saved results; repeated specimens and reused baselines. No uncertainty intervals or superiority tests inferred.'
    }, indent=2)+'\n', encoding='utf-8')
    if LOCAL.exists():
        # Presentation only: retain the original table and all numerical artifacts.
        base = '../../docs/results/regional-figures/'
        block = '<!-- regional-visuals:start --><section aria-label="Visual explanation">'
        block += ('<h2>Start here: what counts as a correct match?</h2>'
            '<p>For each tooth specimen, DINOv3 finds the most visually similar <strong>different catalog ID</strong>. '
            'A correct match means that neighbor has the same site or proposed group. '
            'It does not mean DINOv3 identified a species.</p>'
            '<p><strong>What happened:</strong> regional averages found one extra correct upper-locality match overall '
            '(13/15 instead of 12/15). They did not improve the proposed two-group comparison or lower teeth. '
            'None of the statistical tests passed correction for the 12 comparisons.</p>')
        charts = [('why-overall-misleads', '1. Why the overall percentage can be misleading',
                   'The lower whole-image result gets every Love specimen right but misses every Mixson and Tyner specimen. The large Love sample makes the overall score look better than the site separation.'),
                  ('locality-counts', '2. Count the successful matches at each site',
                   'Green circles are correct; orange crosses are wrong. The hollow upper-Tyner circle is unscored because there is no second independent Tyner specimen. Read across a row to compare methods.'),
                  ('group-counts', '3. Ask the separate Love versus Mixson + Tyner question',
                   'For upper teeth, both whole-image and regional-average methods get 13/16 overall. But regional averages gain one Love match and lose one minority-group match. That is why the balanced score falls.'),
                  ('balanced-scores', '4. Give each group an equal say',
                   'Balanced score averages the groups\' success rates. Compare bars within each panel. The dashed line shows what always choosing Love achieves; it is not a significance threshold.')]
        for name, title, explanation in charts:
            block += f'<h2>{title}</h2><p>{explanation}</p><img src="{base}{name}.png" alt="{title}" style="display:block;width:100%;height:auto;margin:20px 0" loading="lazy">'
        block += ('<h2>What should we conclude?</h2><p>There is a small upper-locality improvement worth inspecting, '
                  'but no reliable separation of the proposed groups has been demonstrated. '
                  'The corrected p-values ask whether label-shuffling can produce results this strong, '
                  'with an adjustment for trying several comparisons. They are not accuracy percentages or probabilities of species identity. '
                  'Here none is below 0.05; this does not prove that biological differences are absent.</p>'
                  '<p><a href="../../docs/dinov3-visual-guide.md">Written visual guide</a> | '
                  '<a href="review.html">Inspect tooth-to-tooth correspondences</a></p>'
                  '</section><!-- regional-visuals:end -->')
        page = LOCAL / 'index.html'
        if page.exists():
            text = page.read_text(encoding='utf-8')
            pattern = r'<!-- regional-visuals:start -->.*?<!-- regional-visuals:end -->'
            if re.search(pattern, text, flags=re.S):
                text = re.sub(pattern, lambda _: block, text, flags=re.S)
            else:
                anchor = '<div class="scroll">'
                if anchor not in text:
                    raise ValueError('Cannot locate the existing report table')
                text = text.replace(anchor, block+'<h2>Detailed numerical results</h2>'+anchor, 1)
            page.write_text(text, encoding='utf-8')
    assert SOURCE.read_bytes() == original
    print(f'Created four PNG/SVG charts in {FIGURES}; updated local report presentation if present.')


if __name__ == '__main__':
    main()
