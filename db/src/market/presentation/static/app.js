const byId = (id) => document.getElementById(id);
const searchPage = document.body.dataset.page === 'search';
const parameters = new URLSearchParams(window.location.search);
let selected = null;
let listRequest = null;
let historyRequest = null;
let searchTimer;

if (searchPage) {
  const symbol = parameters.get('symbol') || '';
  const quote = parameters.get('quote') || 'USDT';
  if (['USDT', 'TMN'].includes(quote)) byId('quote').value = quote;
  if (/^[A-Z0-9]{1,50}$/.test(symbol)) {
    selected = symbol;
    byId('search').value = symbol;
  }
}

function clearChart(message) {
  historyRequest?.abort();
  byId('chart').replaceChildren();
  byId('chart').setAttribute('hidden', '');
  byId('chart-title').textContent = 'تاریخچه قیمت';
  byId('chart-unit').textContent = '';
  byId('chart-start').textContent = '';
  byId('chart-end').textContent = '';
  byId('chart-message').hidden = false;
  byId('chart-message').textContent = message;
}

function tableMessage(message) {
  const row = document.createElement('tr');
  const cell = document.createElement('td');
  cell.colSpan = 4;
  cell.textContent = message;
  row.append(cell);
  byId('markets').replaceChildren(row);
}

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
  const search = searchPage ? byId('search').value.trim() : '';
  const quote = byId('quote').value;
  if (searchPage) {
    clearChart(search ? 'در حال دریافت نمودار...' : 'پس از جست‌وجو، نمودار بازار نمایش داده می‌شود.');
    if (!search) {
      selected = null;
      tableMessage('برای شروع، نماد یک بازار را جست‌وجو کنید.');
      byId('list-title').textContent = 'نتایج جست‌وجو';
      byId('updated').textContent = '';
      byId('status').textContent = 'آماده جست‌وجو';
      byId('status').classList.remove('stale');
      byId('error').hidden = true;
      return;
    }
  }
  const query = new URLSearchParams({ search, quote, limit: searchPage ? '100' : '10' });
  if (!searchPage) query.set('featured', 'true');
  try {
    const data = await getJSON('/api/v1/markets?' + query, controller.signal);
    byId('error').hidden = true;
    byId('list-title').textContent = searchPage ? 'نتایج جست‌وجو (' + data.total + ')' : '۱۰ بازار معروف';
    byId('updated').textContent = 'آخرین دریافت: ' + dateText(data.updated_at);
    byId('status').textContent = data.stale ? 'داده ذخیره‌شده؛ به‌روزرسانی موقتاً در دسترس نیست' : 'قیمت‌ها به‌روز هستند';
    byId('status').classList.toggle('stale', data.stale);
    const body = byId('markets');
    body.replaceChildren();
    if (searchPage && !data.items.some((market) => market.symbol === selected)) {
      const exact = data.items.find((market) => market.symbol === search.toUpperCase());
      selected = exact?.symbol || data.items[0]?.symbol || null;
    }
    if (!data.items.length) {
      tableMessage('بازاری با این عبارت پیدا نشد.');
      if (searchPage) clearChart('بازاری برای نمایش نمودار پیدا نشد.');
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
      const button = document.createElement(searchPage ? 'button' : 'a');
      button.textContent = 'نمودار';
      button.setAttribute('aria-label', 'نمودار ' + market.symbol);
      if (!searchPage) {
        button.className = 'market-link';
        button.href = '/website/search?' + new URLSearchParams({ symbol: market.symbol, quote: market.quote_asset });
      } else button.addEventListener('click', () => {
        selected = market.symbol;
        body.querySelectorAll('tr').forEach((r) => r.classList.remove('selected'));
        row.classList.add('selected');
        loadHistory(market.symbol, market.quote_asset);
      });
      cell.append(button);
      row.append(cell);
      body.append(row);
    }
    if (searchPage && selected) loadHistory(selected, quote);
  } catch (error) {
    if (error.name === 'AbortError') return;
    byId('error').textContent = error.message;
    byId('error').hidden = false;
    byId('status').textContent = 'خطا در دریافت اطلاعات';
    byId('status').classList.add('stale');
    if (searchPage) clearChart('دریافت نمودار انجام نشد. دوباره تلاش کنید.');
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
    chart.toggleAttribute('hidden', !points.length);
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
    byId('chart').setAttribute('hidden', '');
    byId('chart-message').hidden = false;
    byId('chart-message').textContent = error.message;
  }
}

if (searchPage) {
  byId('search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    listRequest?.abort();
    historyRequest?.abort();
    selected = null;
    searchTimer = setTimeout(loadMarkets, 300);
  });
  byId('search').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      clearTimeout(searchTimer);
      loadMarkets();
    }
  });
}
byId('quote').addEventListener('change', () => { selected = null; loadMarkets(); });
byId('reload').addEventListener('click', loadMarkets);
loadMarkets();
setInterval(loadMarkets, 60000);
