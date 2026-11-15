# Pre-registrations

Each file here fixes a comparison before it is run on held-out data (ML layer
design §8.1): the systems and their frozen versions, the data, the
hypotheses and their pass and fail conditions, and the procedure. A file is
merged before the run, and never edited afterwards; the run's reports
record its digest. `python -m ntip.evaluation.compare` refuses the test
split without one.

| File | Comparison | Status |
|---|---|---|
| [ml-10-frozen-comparison.md](ml-10-frozen-comparison.md) | ML-10: B0, B1, B1e and hybrids on the generated, curated and challenge test splits | Run once at `7e58089`; [results](../results/README.md#ml-10-pre-registered-frozen-comparison-on-the-test-splits): H1 to H5 pass, H6 (latency target) missed |
