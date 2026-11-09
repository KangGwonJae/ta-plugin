#!/bin/bash
# 이 케이스의 fixtures/ 를 실행 폴더(현재 디렉터리)로 복사한다. claude plugin eval ... --scaffold 로 켠다.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p fixtures
cp -R "$HERE/fixtures/." fixtures/
echo "fixtures copied to $(pwd)/fixtures:"; ls fixtures
