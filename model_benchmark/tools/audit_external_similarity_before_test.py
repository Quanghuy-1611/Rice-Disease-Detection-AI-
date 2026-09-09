"""Inventory external similarity without evaluating predictions or changing data."""
import json
import sys
from collections import Counter
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmark_common import sha256_file
import final_evaluate_11class_large as ev
from audit_dataset_v4 import canonical_phash, pixel_digest

rows=ev.read_csv(ev.EXTERNAL_MANIFEST)
errors=[]
hashes=[]
for row in rows:
    path=ev.EXTERNAL_ROOT/row['locked_relative_path']
    if sha256_file(path)!=row['sha256']:
        errors.append({'path':str(path),'error':'sha_mismatch'})
    with Image.open(path) as im:
        h=canonical_phash(im)
        if h!=int(row['canonical_phash64'],16):
            errors.append({'path':str(path),'error':'phash_mismatch'})
        if pixel_digest(im)!=row['pixel_sha256']:
            errors.append({'path':str(path),'error':'pixel_hash_mismatch'})
        hashes.append(h)
pairs=[]
for i in range(len(rows)):
    for j in range(i):
        distance=(hashes[i]^hashes[j]).bit_count()
        if distance<=12:
            pairs.append({'a':rows[j]['locked_relative_path'],'b':rows[i]['locked_relative_path'],'distance':distance,'same_label':rows[i]['label']==rows[j]['label']})
report={'status':'blocked_before_test_predictions','image_count':len(rows),'file_hash_errors':errors,
    'external_pairs_phash_le8':sum(p['distance']<=8 for p in pairs),
    'external_pairs_phash_le12':len(pairs),'candidate_pairs_for_review':pairs,
    'visually_reviewed_crop_pair':['stem_borer/stem_borer_031.jpg','stem_borer/stem_borer_040.jpg'],
    'interpretation':'Similarity pairs are candidates, not confirmed duplicates. The named crop pair appears to show the same photograph with different cropping. Requires group-aware assessment before iid statistical inference.',
    'cross_split_gate_failure':{'external_phash_le8_count':2,'min_distance':8,'sha_overlap':0,'pixel_overlap':0},
    'cross_split_visual_review':'Two cross-label pairs are visually different images with similar layouts; these are not confirmed duplicate leaks.',
    'training_label_review_flag':'train/leaf_roller/leaf_roller_004208.jpg: butterfly-like insect on purple flower; needs expert label confirmation.',
    'test_predictions_produced':False}
out=ROOT/'runs'/'external_similarity_pretest_review.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='candidate_pairs_for_review'},ensure_ascii=True,indent=2))
print(json.dumps(pairs[:20],indent=2))
