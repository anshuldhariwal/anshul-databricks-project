const dataUrl = "latest_market_summary.json";

const text = (id, value) => {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
};

const asNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
};

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: asNumber(value) >= 1000 ? 0 : 2,
  }).format(asNumber(value));

const formatCompact = (value) =>
  new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(asNumber(value));

const formatDate = (value) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

const typeLabel = (value) => String(value || "").toUpperCase();

const renderSummary = (rows) => {
  const body = document.getElementById("summary-rows");
  body.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td><strong>${row.symbol}</strong></td>
          <td><span class="asset-tag ${row.asset_type}">${typeLabel(row.asset_type)}</span></td>
          <td>${formatCurrency(row.latest_price)}</td>
          <td>${formatCompact(row.volume)}</td>
          <td>${formatDate(row.last_updated)}</td>
        </tr>
      `,
    )
    .join("");
};

const renderLeaders = (id, rows) => {
  const list = document.getElementById(id);
  list.innerHTML = rows
    .map(
      (row) => `
        <li>
          <span class="rank">${row.rank}</span>
          <div>
            <strong>${row.symbol}</strong>
            <span>${formatCurrency(row.price)} x ${formatCompact(row.volume)}</span>
          </div>
          <em>${formatCurrency(row.transaction_value)}</em>
        </li>
      `,
    )
    .join("");
};

const renderBronze = (rows) => {
  const grid = document.getElementById("bronze-records");
  grid.innerHTML = rows
    .map(
      (row) => `
        <article class="record-card">
          <div>
            <strong>${row.symbol}</strong>
            <span class="asset-tag ${row.asset_type}">${typeLabel(row.asset_type)}</span>
          </div>
          <dl>
            <dt>Source</dt><dd>${row.source}</dd>
            <dt>Price</dt><dd>${formatCurrency(row.price)}</dd>
            <dt>Volume</dt><dd>${formatCompact(row.volume)}</dd>
            <dt>Event time</dt><dd>${formatDate(row.event_time)}</dd>
          </dl>
        </article>
      `,
    )
    .join("");
};

const render = (payload) => {
  const summary = payload.gold?.latest_summary || [];
  const bronze = payload.bronze?.latest_records || [];
  const stocks = summary.filter((row) => row.asset_type === "stock");
  const crypto = summary.filter((row) => row.asset_type === "crypto");

  text("last-updated", formatDate(payload.generated_at));
  text("target-pill", payload.bundle_target || "target");
  text("asset-count", summary.length);
  text("stock-count", stocks.length);
  text("crypto-count", crypto.length);
  text("batch-count", bronze.length);
  text("principal-label", payload.principal || "");

  renderSummary(summary);
  renderLeaders("stock-leaders", payload.gold?.top_stock_transactions || []);
  renderLeaders("crypto-leaders", payload.gold?.top_crypto_transactions || []);
  renderBronze(bronze);
};

fetch(dataUrl, { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`Could not load ${dataUrl}`);
    return response.json();
  })
  .then(render)
  .catch((error) => {
    text("last-updated", "Data unavailable");
    const main = document.querySelector("main");
    const message = document.createElement("p");
    message.className = "error-message";
    message.textContent = error.message;
    main.prepend(message);
  });
