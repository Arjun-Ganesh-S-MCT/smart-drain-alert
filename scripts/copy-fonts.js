const fs = require('fs');
const path = require('path');

const from = path.join(__dirname, '..', 'node_modules', '@fontsource', 'jetbrains-mono', 'files');
const to = path.join(__dirname, '..', 'src', 'fonts');

try {
  fs.mkdirSync(to, { recursive: true });
  for (const weight of [400, 600, 700]) {
    const name = `jetbrains-mono-latin-${weight}-normal.woff2`;
    const source = path.join(from, name);
    if (fs.existsSync(source)) fs.copyFileSync(source, path.join(to, name));
    else console.warn('Font file not found:', name);
  }
} catch (e) {
  console.warn('Font copy skipped:', e.message);
}
