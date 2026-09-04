TwinVerse Inspect AI does the first pass of a structural inspection from ordinary photographs, so nobody has to climb a bridge to find out whether it needs looking at.

Upload drone, CCTV or phone imagery. A fine-tuned YOLOv11 model locates cracks in concrete, scores each one for severity, ranks them worst-first, and produces a PDF an engineer can act on. It is built for inspection teams who survey by hand today: slow work, done at height, and inconsistent between inspectors.

What makes it different is that you can check its work. Every severity score on screen is three numbers multiplied together — the defect's share of the frame, the model's confidence, and a class weight — and all three are stored and shown. Nothing is a black box.

We also published what it gets wrong. The detector is benchmarked against four datasets rather than one, and its operating threshold was chosen by simulating inspection campaigns instead of maximising a symmetric accuracy metric — because a missed crack is found when something fails, while a false alarm costs an engineer thirty seconds. It finds 84-100% of cracks on the datasets it trained on and 56% on one it has never seen, and it flags about 60% of photographs for human review. Every one of those numbers, and the decisions behind them, are in the repository.

It is a screening pass, not an engineering assessment. A qualified engineer still signs off.

Built and running: FastAPI, PostgreSQL, MinIO, Next.js, Docker Compose, 104 tests.
