# LexiconError model training

This package trains three compact diagnostic routers from the published LexiconError JSONL corpus.
Every variant predicts language, category, and severity without sending code or stack traces to a
service. They use the same deterministic split and optimization settings; vocabulary capacity is
the controlled sizing dimension.

| Variant | Fitted features | Learned parameters | Artifact size | Hugging Face |
| --- | ---: | ---: | ---: | --- |
| Small | 25,000 | 2,425,097 | 8.35 MB | [lexiconerror-router-small](https://huggingface.co/Magnexis/lexiconerror-router-small) |
| Medium | 100,000 | 9,700,097 | 31.22 MB | [lexiconerror-router-medium](https://huggingface.co/Magnexis/lexiconerror-router-medium) |
| Large | 225,546 | 21,878,059 | 65.94 MB | [lexiconerror-router-large](https://huggingface.co/Magnexis/lexiconerror-router-large) |

Large has a 250,000-feature budget and fits all 225,546 features available in this release corpus.
More parameters increase representational capacity; they do not guarantee higher accuracy on every
metric. Medium is the recommended desktop default.

## Train

~~~powershell
python modeling\train_family.py `
  --dataset hf\lexiconerror-diagnostics\data\diagnostics.jsonl `
  --output-root artifacts\model
~~~

The output includes the joblib model, exact dataset and model hashes, evaluation metrics,
requirements, a model card, and the LexiconError logo. Training is deterministic apart from normal
numeric-library implementation differences.

## Test and infer

~~~powershell
python modeling\test_router.py
python -B modeling\test_family.py --root artifacts\model
python -B modeling\test_model_package.py --package artifacts\model\lexiconerror-router-small
python -B modeling\test_model_package.py --package artifacts\model\lexiconerror-router-medium
python -B modeling\test_model_package.py --package artifacts\model\lexiconerror-router-large
python modeling\predict_router.py "error[E0382]: borrow of moved value"
~~~

Joblib uses Python pickle semantics. Only load model files from trusted sources and verify the
published `SHA256SUMS.txt` first.

## Review policy

Training includes the entire catalog because the targets are routing labels, not remediation
approval. Records marked `Needs Review` remain unapproved in the source dataset and model card.
Verified entries receive a modest sample-weight increase; the pipeline never rewrites verification
status.
