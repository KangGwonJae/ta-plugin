---
type: regex
pattern: '<!--ta-review v1 hash=[0-9a-f]{16} scope=(full|part) reviewer=(agent|self)'
match: contains
target:
  source: file
  path: 학습자료/lecture3_regression.pdf_학습자료.html
---
