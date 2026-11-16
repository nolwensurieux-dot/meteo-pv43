// Calculs agro-météo — reproduit les formules du fichier "Donnees_meteo_2026.xlsx"
// Fonctionne dans le navigateur (window.Calc) et dans Node (module.exports).
(function (root) {
  const DAY = 86400000;
  const toUTC = (s) => { const [y, m, d] = s.split("-").map(Number); return Date.UTC(y, m - 1, d); };
  const iso = (t) => new Date(t).toISOString().slice(0, 10);
  const addDays = (s, n) => iso(toUTC(s) + n * DAY);
  const shiftYear = (s, n) => { const [y, m, d] = s.split("-"); let dd = d; if (m === "02" && d === "29") dd = "28"; return `${+y + n}-${m}-${dd}`; };

  function idx(st, date) { return Math.round((toUTC(date) - toUTC(st.start)) / DAY); }
  function val(arr, i) { return i >= 0 && i < arr.length ? arr[i] : null; }

  // Température moyenne : comme dans Excel, une donnée manquante compte pour 0
  function mean(st, i) { return ((val(st.tn, i) ?? 0) + (val(st.tx, i) ?? 0)) / 2; }

  const DAILY = {
    // Base 0 "INRA" : moyenne bornée entre 0 et 18 °C
    b0inra: (st, i) => Math.min(18, Math.max(0, mean(st, i))),
    // Base 0 simple : moyenne si positive
    b0: (st, i) => Math.max(0, mean(st, i)),
    // Base 6 avec TX plafonnée à 30 °C
    b6: (st, i) => {
      const e = mean(st, i);
      if (e < 6) return 0;
      const tx = val(st.tx, i) ?? 0, tn = val(st.tn, i) ?? 0;
      return tx > 30 ? (tn + 30) / 2 - 6 : e - 6;
    },
    rr: (st, i) => val(st.rr, i) ?? 0,
  };

  // Les sommes suivies par l'équipe (début = jour/mois de l'année de la date de référence)
  const METRICS = [
    { id: "b0feb", label: "Base 0 · depuis le 1er février", short: "Base 0 · 1er fév.", fn: "b0inra", from: "02-01", note: "Moyenne bornée 0–18 °C" },
    { id: "b6_0420", label: "Base 6 · depuis le 20 avril", short: "Base 6 · 20/04", fn: "b6", from: "04-20", note: "TX plafonnée à 30 °C" },
    { id: "b6_0501", label: "Base 6 · depuis le 1er mai", short: "Base 6 · 01/05", fn: "b6", from: "05-01", note: "TX plafonnée à 30 °C" },
    { id: "b6_0510", label: "Base 6 · depuis le 10 mai", short: "Base 6 · 10/05", fn: "b6", from: "05-10", note: "TX plafonnée à 30 °C" },
    { id: "b6_0520", label: "Base 6 · depuis le 20 mai", short: "Base 6 · 20/05", fn: "b6", from: "05-20", note: "TX plafonnée à 30 °C" },
    { id: "b0jan", label: "Base 0 · depuis le 1er janvier", short: "Base 0 · 1er janv.", fn: "b0", from: "01-01", note: "Pour info (céréales d'automne)" },
  ];

  function sumRange(st, fn, from, to) {
    const f = DAILY[fn];
    let i0 = Math.max(0, idx(st, from)), i1 = Math.min(st.tn.length - 1, idx(st, to));
    if (idx(st, to) < idx(st, from)) return null;
    let s = 0, missing = 0;
    for (let i = i0; i <= i1; i++) {
      if (fn === "rr" ? st.rr[i] == null : (st.tn[i] == null || st.tx[i] == null)) missing++;
      s += f(st, i);
    }
    return { value: s, missing };
  }

  function metricAt(st, metric, date) {
    const m = typeof metric === "string" ? METRICS.find((x) => x.id === metric) : metric;
    const from = `${date.slice(0, 4)}-${m.from}`;
    if (date < from) return null; // pas encore commencé
    return sumRange(st, m.fn, from, date);
  }

  // Valeur, gain sur 7 jours, valeur à la même date l'an dernier
  function metricSummary(st, metric, date) {
    const now = metricAt(st, metric, date);
    const before = metricAt(st, metric, addDays(date, -7));
    const prevDate = shiftYear(date, -1);
    const prev = idx(st, prevDate) >= 0 ? metricAt(st, metric, prevDate) : null;
    return {
      value: now ? now.value : null,
      missing: now ? now.missing : 0,
      gain7: now ? now.value - (before ? before.value : 0) : null,
      prev: prev ? prev.value : null,
    };
  }

  function rain(st, from, to) { const r = sumRange(st, "rr", from, to); return r ? r.value : null; }

  // ETP estimée — formule AP3C 2017-2018 (identique au fichier)
  function etpDay(st, i) {
    const tx = val(st.tx, i);
    if (tx == null) return null;
    const date = addDays(st.start, i);
    const P = Math.round((toUTC(date) - toUTC("1979-12-31")) / DAY);
    const rr = val(st.rr, i) ?? 0;
    const rrPrev = i > 0 ? (val(st.rr, i - 1) ?? 0) : rr;
    const txPrev = i > 0 ? (val(st.tx, i - 1) ?? tx) : tx;
    const Q = Math.log10(rr + 0.01), R = Math.log10(rrPrev + 0.01);
    const S = st.alt / 1000, T = st.x / 100000, U = st.y / 100000;
    const PI2 = 2 * Math.PI, sin = Math.sin;
    const v =
      ((0.141 - 0.0361 * S) + (0.1489 - 0.0095 * T) * sin(PI2 * (P / 365.25) + (-1.6388 + 0.1914 * S + (-0.1155 - 0.6753 * S) * P / 36524)) +
        (0.0033 + 0.0014 * T) * sin(PI2 * (P / 182.625) + (-8.4768 + 0.1281 * U + (1.0381 + 1.7061 * S) * P / 36524))) * tx +
      ((-0.2863 + 0.0286 * T + (-0.152 - 0.2819 * S) * P / 36524) + (0.6632 - 0.0343 * S + 0.0233 * T - 0.0111 * U + 0.1622 * P / 36524) * sin(PI2 * (P / 365.25) + (2.5035 - 0.089 * T))) * Q +
      (0.2999 - 0.007 * S + 0.0088 * T - 0.0054 * U) * txPrev +
      ((-0.0705) + (1.0484 + 0.0077 * T - 0.0164 * U) * sin(PI2 * (P / 365.25) + (-15.8078 - 0.2643 * T + 0.3071 * U))) * R +
      (-0.786 + 0.8935 * S + (0.0315 - 0.1779 * S) * P / 36524) +
      (1.267 - 0.6409 * S) * sin(PI2 * (P / 365.25) + (1.2554 - 0.2578 * S + (-0.1478 - 0.9776 * S) * P / 36524)) +
      (0.375 - 0.097 * S) * sin(PI2 * (P / 182.625) + (-2.5301 + 0.1579 * S));
    return Math.max(0, v);
  }

  // Bilan mensuel : pluie, ETP, classe de sécheresse (0 très sec … 3 humide)
  function monthly(st, year, upTo) {
    const out = [];
    for (let m = 1; m <= 12; m++) {
      const from = `${year}-${String(m).padStart(2, "0")}-01`;
      if (from > upTo) break;
      const end = iso(Date.UTC(year, m, 0));
      const to = end < upTo ? end : upTo;
      let p = 0, etp = 0, tsum = 0, n = 0;
      for (let i = idx(st, from); i <= idx(st, to); i++) {
        if (i < 0 || i >= st.tn.length) continue;
        p += st.rr[i] ?? 0; etp += etpDay(st, i) ?? 0; tsum += mean(st, i); n++;
      }
      if (!n) continue;
      const ratio = etp ? p / etp : null;
      const cls = ratio == null ? null : ratio < 0.33 ? 0 : ratio < 0.67 ? 1 : ratio < 1 ? 2 : 3;
      out.push({ month: m, rain: p, etp, ratio, cls, tmean: tsum / n, partial: to !== end });
    }
    return out;
  }

  // Série cumulée jour par jour (pour le graphique)
  function series(st, metric, year, upTo) {
    const m = METRICS.find((x) => x.id === metric);
    const from = `${year}-${m.from}`;
    const f = DAILY[m.fn];
    const pts = [];
    let s = 0;
    const end = upTo || `${year}-12-31`;
    for (let d = from; d <= end; d = addDays(d, 1)) {
      const i = idx(st, d);
      if (i < 0) continue;
      if (i >= st.tn.length) break;
      s += f(st, i);
      pts.push([d.slice(5), s]);
    }
    return pts;
  }

  const api = { METRICS, DAILY, metricAt, metricSummary, rain, etpDay, monthly, series, addDays, shiftYear, idx, mean };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Calc = api;
})(typeof window !== "undefined" ? window : globalThis);
