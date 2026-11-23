// Copies the app UI (../src) into ./www for Capacitor. Run after `npm install` in the repo root so src/vendor (Leaflet, fonts) exists.
const fs = require('fs'), path = require('path');
const from = path.join(__dirname, '..', 'src'), to = path.join(__dirname, 'www');
fs.rmSync(to, { recursive: true, force: true });
const skip = new Set(['setup.html', 'splash.html']);
fs.cpSync(from, to, { recursive: true, filter: src => !skip.has(path.basename(src)) });
if (!fs.existsSync(path.join(to, 'vendor', 'leaflet'))) console.warn('WARNING: src/vendor/leaflet missing - run "npm install" in the repo root first (the map will fall back to the CDN).');
console.log('www ready:', fs.readdirSync(to).length, 'entries');
