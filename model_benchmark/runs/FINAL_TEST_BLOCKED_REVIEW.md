# Final test blocked before inference

Review date: 2026-09-09. No test predictions or test scores were produced in this attempt.

## Checks completed

- All 21,216 dataset files matched their manifest SHA-256, per-file lock SHA-256 and size; no missing or unlisted dataset files.
- All 18 completed checkpoints matched recorded SHA-256 and checkpoint metadata (architecture, seed, ordered classes, contract, manifest, best epoch and validation score).
- Synthetic metric checks matched scikit-learn and exact McNemar matched SciPy.
- All 1,100 external files matched stored SHA-256, decoded-pixel hashes and recomputed canonical pHash.

## Why inference was refused

The existing evaluator's all-label cross-set pHash gate found two external images at Hamming distance 8, whereas the earlier claim of minimum distance 10 concerned a narrower check. No exact-file or decoded-pixel overlap was found. Visual inspection of these two cross-label pairs shows different subjects with similar composition, not confirmed duplicate leakage:

1. external stem_borer/stem_borer_031.jpg versus train brown_planthopper/brown_planthopper_002016.jpg.
2. external stem_borer/stem_borer_040.jpg versus train leaf_roller/leaf_roller_004208.jpg.

The external set itself contains 14 candidate pairs at distance <=8 and 128 candidate pairs at distance <=12. These counts are candidate pairs, not counts of confirmed duplicates or distinct redundant images.

Visual inspection confirms that external brown_planthopper_008.jpg and brown_planthopper_009.jpg depict the same source photograph with small image differences. They both even retain the same image-search overlay. External stem_borer_031.jpg and stem_borer_040.jpg also appear to be crops of the same photograph. The train leaf_roller example is a butterfly-like insect on a purple flower and is flagged for expert label review, not automatically relabelled.

## Required resolution

Before final inference, review similarity groups and source/observation identities while still blind to predictions. Register reviewed false-positive cross-set exceptions using exact file hashes, and either group correlated external images for statistical inference or create a separately versioned deduplicated test manifest. Retain original manifests, images, locks and all 18 checkpoints. Do not quietly bypass the failed gate or force metrics under 90%.

Claims of fully independent external samples, flawless labels or proven real-world accuracy are unsupported at this point. Earlier blanket assurances about external near-duplicate isolation were too strong and are superseded by this review.

Detailed candidate list: external_similarity_pretest_review.json in this directory.
