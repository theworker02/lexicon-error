# LexiconError model training

This package trains a compact diagnostic router from the published LexiconError JSONL corpus. It
predicts language, category, and severity from diagnostic text without sending code or stack traces
to a service.

## Train

~~~powershell
python modeling\train_router.py `
  --dataset hf\lexiconerror-diagnostics\data\diagnostics.jsonl `
  --output artifacts\model\lexiconerror-router
~~~

The output includes the joblib model, exact dataset and model hashes, evaluation metrics,
requirements, a model card, and the LexiconError logo. Training is deterministic apart from normal
numeric-library implementation differences.

## Test and infer

~~~powershell
python modeling\test_router.py
python modeling\test_model_package.py --package artifacts\model\lexiconerror-router
python modeling\predict_router.py "error[E0382]: borrow of moved value"
~~~

Joblib uses Python pickle semantics. Only load model files from trusted sources and verify the
published `SHA256SUMS.txt` first.

## Review policy

Training includes the entire catalog because the targets are routing labels, not remediation
approval. Records marked `Needs Review` remain unapproved in the source dataset and model card.
Verified entries receive a modest sample-weight increase; the pipeline never rewrites verification
status.
