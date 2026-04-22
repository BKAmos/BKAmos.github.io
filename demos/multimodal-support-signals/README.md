# Multimodal support signals

Synthetic tickets with **text** (subject/body), **categorical** fields (product line, channel), and **numeric** attachment size. Early fusion (TF–IDF + SVD + encoded tabular) then k-means; weekly cluster mix.

```bash
python3 data/generate.py
python3 src/run.py
```
