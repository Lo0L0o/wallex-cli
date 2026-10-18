const byId = (id) => document.getElementById(id);
let selected = null;
let listRequest = null;
let historyRequest = null;
let searchTimer;

function numberText(value) {
  const [whole, fraction] = String(value).split('.');
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (fraction ? '.' + fraction : '');
}

function dateText(value) {
  return value ? new Date(value).toLocaleString('fa-IR') : 'نامشخص';
}

async function getJSON(url, signal) {
  const response = await fetch(url, { signal });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error?.code === 'market_unavailable'
      ? 'فعلاً داده‌ای در دسترس نیست. کمی بعد دوباره تلاش کنید.'
      : 'دریافت اطلاعات انجام نشد. دوباره تلاش کنید.');
  }
  return data;
}

async function loadMarkets() {
  listRequest?.abort();
  const controller = new AbortController();
  listRequest = controller;
  const search = byId('search').value.trim();
  const quote = byId('quote').value;
  const query = new URLSearchParams({ search, quote, limit: search ? '100' : '20' });
  try {
    const data = await getJSON('/api/v1/markets?' + query, controller.signal);
    byId('error').hidden = true;
    byId('list-title').textContent = search ? 'نتایج جست‌وجو (' + data.total + ')' : '۲۰ بازار برتر';
    byId('updated').textContent = 'آخرین دریافت: ' + dateText(data.updated_at);
    byId('status').textContent = data.stale ? 'داده ذخیره‌شده؛ به‌روزرسانی موقتاً در دسترس نیست' : 'قیمت‌ها به‌روز هستند';
    byId('status').classList.toggle('stale', data.stale);
    const body = byId('markets');
    body.replaceChildren();
    if (!data.items.length) {
      const cell = document.createElement('td');
      cell.colSpan = 4;
      cell.textContent = 'بازاری با این عبارت پیدا نشد.';
      const row = document.createElement('tr');
      row.append(cell);
      body.append(row);
    }
    for (const market of data.items) {
      const row = document.createElement('tr');
      row.classList.toggle('selected', selected === market.symbol);
      for (const value of [market.symbol, numberText(market.price), numberText(market.quote_volume)]) {
        const cell = document.createElement('td');
        cell.textContent = value;
        cell.className = 'numeric';
        row.append(cell);
      }
      const cell = document.createElement('td');
      const button = document.createElement('button');
      button.textContent = 'نمودار';
      button.setAttribute('aria-label', 'نمودار ' + market.symbol);
      button.addEventListener('click', () => {
        selected = market.symbol;
        body.querySelectorAll('tr').forEach((r) => r.classList.remove('selected'));
        row.classList.add('selected');
        loadHistory(market.symbol, market.quote_asset);
      });
      cell.append(button);
      row.append(cell);
      body.append(row);
    }
    if (!selected && data.items.length) {
      selected = data.items[0].symbol;
      body.firstElementChild.classList.add('selected');
    }
    if (selected) loadHistory(selected, quote);
  } catch (error) {
    if (error.name === 'AbortError') return;
    byId('error').textContent = error.message;
    byId('error').hidden = false;
    byId('status').textContent = 'خطا در دریافت اطلاعات';
    byId('status').classList.add('stale');
  }
}

function svgElement(name, attributes) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  return element;
}

async function loadHistory(symbol, quote) {
  historyRequest?.abort();
  const controller = new AbortController();
  historyRequest = controller;
  byId('chart-title').textContent = 'تاریخچه ' + symbol;
  byId('chart-unit').textContent = quote === 'TMN' ? 'تومان' : 'تتر';
  try {
    const data = await getJSON('/api/v1/markets/' + encodeURIComponent(symbol) + '/history?limit=100', controller.signal);
    const points = data.points;
    const chart = byId('chart');
    chart.replaceChildren();
    chart.hidden = !points.length;
    byId('chart-message').hidden = points.length > 1;
    byId('chart-message').textContent = points.length
      ? 'فعلاً یک قیمت ثبت شده است؛ با دریافت‌های بعدی نمودار کامل‌تر می‌شود.'
      : 'هنوز تاریخچه‌ای ثبت نشده است.';
    byId('chart-start').textContent = points.length ? dateText(points[0].recorded_at) : '';
    byId('chart-end').textContent = points.length ? dateText(points.at(-1).recorded_at) : '';
    if (!points.length) return;
    const values = points.map((p) => Number(p.price));
    const low = Math.min(...values);
    const high = Math.max(...values);
    const range = high - low || Math.max(Math.abs(high) * 0.01, 1);
    const firstTime = Date.parse(points[0].recorded_at);
    const duration = Date.parse(points.at(-1).recorded_at) - firstTime || 1;
    const coordinates = values.map((value, i) => [
      110 + (Date.parse(points[i].recorded_at) - firstTime) / duration * 760,
      high === low ? 140 : 240 - (value - low) / range * 200,
    ]);
    for (const y of [40, 140, 240]) chart.append(svgElement('line', { x1: 100, x2: 880, y1: y, y2: y, stroke: '#304155' }));
    chart.append(svgElement('polyline', { points: coordinates.map((p) => p.join(',')).join(' '), fill: 'none', stroke: '#71ddbc', 'stroke-width': 3 }));
    for (let i = 0; i < coordinates.length; i++) {
      const circle = svgElement('circle', { cx: coordinates[i][0], cy: coordinates[i][1], r: 4, fill: '#71ddbc' });
      const title = svgElement('title', {});
      title.textContent = dateText(points[i].recorded_at) + ' · ' + numberText(points[i].price);
      circle.append(title);
      chart.append(circle);
    }
    for (const [value, y] of [[high, 40], [low, 240]]) {
      const label = svgElement('text', { x: 6, y, fill: '#a9b9cc', 'font-size': 12 });
      label.textContent = value.toLocaleString('en-US', { maximumSignificantDigits: 8 });
      chart.append(label);
    }
  } catch (error) {
    if (error.name === 'AbortError') return;
    byId('chart').hidden = true;
    byId('chart-message').hidden = false;
    byId('chart-message').textContent = error.message;
  }
}

byId('search').addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadMarkets, 300);
});
byId('quote').addEventListener('change', () => { selected = null; loadMarkets(); });
byId('reload').addEventListener('click', loadMarkets);
loadMarkets();
setInterval(loadMarkets, 60000);
