// three.js 일부(entry.js)와 런타임(runtime.js)을 묶어 ../v3d.html 공용 조각을 만든다.
// 실행: 저장소 루트에서 `npm run build:v3d` (three·esbuild를 --no-save로 받아 쓴다)
import { build } from 'esbuild';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const VERSION = 1; // v3d.html을 바꾸면 올린다(ta.py fragments가 옛 문서의 조각을 교체)
const here = dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(join(here, '../../../node_modules/three/package.json'), 'utf8'));
const out = await build({ entryPoints: [join(here, 'entry.js')], bundle: true, minify: true, format: 'iife', legalComments: 'none', write: false });
const lib = out.outputFiles[0].text.trim();
const runtime = readFileSync(join(here, 'runtime.js'), 'utf8').trim();
const html = `<!--v3d:start v${VERSION}-->
<script>/* three.js r${pkg.version.split('.')[1]} (MIT License, https://github.com/mrdoob/three.js) — ta viz 3D에 필요한 부분만 묶음 */
${lib}</script>
<script>
${runtime}
</script>
<!--v3d:end-->
`;
writeFileSync(join(here, '../v3d.html'), html);
console.log(`v3d.html v${VERSION}: three ${pkg.version}, ${(html.length / 1024).toFixed(0)} KB`);
