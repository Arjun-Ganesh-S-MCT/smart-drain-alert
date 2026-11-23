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

// Leaflet (city drainage map): copy the browser build next to the app so it works offline-installed
try {
  const lf = path.join(__dirname, '..', 'node_modules', 'leaflet', 'dist');
  const lt = path.join(__dirname, '..', 'src', 'vendor', 'leaflet');
  if (fs.existsSync(lf)) {
    fs.mkdirSync(path.join(lt, 'images'), { recursive: true });
    for (const f of ['leaflet.js', 'leaflet.css']) fs.copyFileSync(path.join(lf, f), path.join(lt, f));
    for (const f of fs.readdirSync(path.join(lf, 'images'))) fs.copyFileSync(path.join(lf, 'images', f), path.join(lt, 'images', f));
  } else console.warn('Leaflet not found: run npm install');
} catch (e) {
  console.warn('Leaflet copy skipped:', e.message);
}
