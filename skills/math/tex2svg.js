// LaTeX → MathJax SVG (외부 의존 없는 단독 <svg>, 글자색 currentColor → 라이트/다크 자동 대응)
//
// 한 개:  node tex2svg.js '\sum_p \lambda_p'            → 문장 속(inline) 수식 HTML
//         node tex2svg.js --display '\sum_p \lambda_p'  → 단독 줄(display) 수식 HTML
// 여러 개: echo '[{"tex":"...","display":true}, ...]' | node tex2svg.js --json
//         → 같은 순서의 HTML 문자열 JSON 배열
//
// 결과는 <span class="m" data-tex="원본 LaTeX" role="img" aria-label="원본 LaTeX"><svg>…</svg></span>.
// data-tex를 남겨 두므로 나중에 이 속성만 고쳐 다시 렌더링할 수 있다.
const path = require('path');
// mathjax-full은 플러그인 루트(package.json이 있는 곳)의 node_modules에 설치된다.
// require.resolve가 이 파일 위치에서 상위 폴더로 올라가며 찾으므로, 이 스킬 폴더나 루트 어느 쪽에 있어도 된다.
let nm;
try {
  nm = path.join(path.dirname(require.resolve('mathjax-full/package.json')), 'js');
} catch (e) {
  const root = path.resolve(__dirname, '..', '..');
  process.stderr.write(`mathjax-full not found. Run: cd "${root}" && npm install\n`);
  process.exit(1);
}
const {mathjax} = require(path.join(nm, 'mathjax.js'));
const {TeX} = require(path.join(nm, 'input/tex.js'));
const {SVG} = require(path.join(nm, 'output/svg.js'));
const {liteAdaptor} = require(path.join(nm, 'adaptors/liteAdaptor.js'));
const {RegisterHTMLHandler} = require(path.join(nm, 'handlers/html.js'));
const {AllPackages} = require(path.join(nm, 'input/tex/AllPackages.js'));

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const doc = mathjax.document('', {
  InputJax: new TeX({packages: AllPackages}),
  OutputJax: new SVG({fontCache: 'local'}),
});

const esc = s => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

function render(tex, display) {
  const node = doc.convert(tex, {display});
  let svg = adaptor.innerHTML(node);
  if (/data-mjx-error|merror/.test(svg)) throw new Error('LaTeX 오류: ' + tex);
  svg = svg.replace(/ role="img" focusable="false"/, ' aria-hidden="true" focusable="false"');
  const cls = display ? 'm m-d' : 'm';
  return `<span class="${cls}" data-tex="${esc(tex)}" role="img" aria-label="${esc(tex)}">${svg}</span>`;
}

process.on('uncaughtException', e => { console.error(String(e.message || e)); process.exit(1); });

const args = process.argv.slice(2);
if (args[0] === '--json') {
  const input = require('fs').readFileSync(0, 'utf8');
  const items = JSON.parse(input);
  process.stdout.write(JSON.stringify(items.map(it => render(it.tex, !!it.display))));
} else {
  const display = args[0] === '--display';
  const tex = display ? args[1] : args[0];
  if (!tex) { console.error('사용: node tex2svg.js [--display] "<LaTeX>" | --json'); process.exit(1); }
  process.stdout.write(render(tex, display));
}
