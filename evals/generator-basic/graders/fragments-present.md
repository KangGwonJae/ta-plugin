---
type: regex
pattern: '<!--jump:start v\d+-->[\s\S]*<!--glossary:start v\d+-->[\s\S]*<!--pageidx:start v\d+-->[\s\S]*<!--reader:start v\d+-->'
match: contains
target:
  source: file
  path: 학습자료/lecture3_regression.pdf_학습자료.html
---
