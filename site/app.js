'use strict';
(function () {
  // ---------------------------------------------------------------- vocab
  const AREAS = {
    security: 'Security', crypto: 'Cryptography', ai: 'AI / ML', nlp: 'NLP', data: 'Data & KG',
    vision: 'Vision', networking: 'Networking', communications: 'Communications',
    systems: 'Systems', software: 'Software Eng.', general: 'General EECS',
  };
  const TIERS = { top: 'Top', major: 'Major', minor: 'Minor', domestic: 'Domestic' };
  const TIER_ORDER = { top: 0, major: 1, minor: 2, domestic: 3 };
  const TYPES = { conference: 'Conference', workshop: 'Workshop', industry: 'Industry' };
  const REGIONS = {
    japan: 'Japan', korea: 'Korea', taiwan: 'Taiwan', china: 'China', 'southeast-asia': 'Southeast Asia',
    'south-asia': 'South Asia', 'asia-pacific': 'Asia-Pacific (rotating)', oceania: 'Oceania',
    europe: 'Europe', 'north-america': 'North America', 'latin-america': 'Latin America',
    'middle-east': 'Middle East', africa: 'Africa', worldwide: 'Worldwide (rotating)', online: 'Online',
  };
  const ORG = {
    japan: 'Japan', korea: 'Korea', taiwan: 'Taiwan', china: 'China', singapore: 'Singapore', india: 'India',
    vietnam: 'Vietnam', thailand: 'Thailand', indonesia: 'Indonesia', malaysia: 'Malaysia', philippines: 'Philippines',
    australia: 'Australia', 'new-zealand': 'New Zealand', usa: 'USA', canada: 'Canada', europe: 'Europe',
    international: 'International', other: 'Other',
  };
  const ASIA = new Set(['japan', 'korea', 'taiwan', 'china', 'southeast-asia', 'south-asia', 'asia-pacific']);
  const ASIA_ORG = new Set(['japan', 'korea', 'taiwan', 'china', 'singapore', 'india', 'vietnam', 'thailand', 'indonesia', 'malaysia', 'philippines']);
  const CORE_ORDER = { 'A*': 0, A: 1, B: 2, C: 3, National: 4, Regional: 5, Unranked: 6 };
  const CCF_ORDER = { A: 0, B: 1, C: 2 };
  const KIND = { abstract: 'Abstract', submission: 'Paper', notification: 'Notification', camera_ready: 'Camera-ready', other: 'Other' };
  const FREQ = { annual: 'Every year', biennial: 'Every two years', 'multiple-per-year': 'Several times a year', irregular: 'Irregular' };
  const LANG = { english: 'English', japanese: 'Japanese', korean: 'Korean', chinese: 'Chinese', mixed: 'Mixed' };
  // Offsets in minutes. Must match TIMEZONES in scripts/build.py.
  const TZ = {
    AoE: -720, UTC: 0, GMT: 0, JST: 540, KST: 540, CET: 60, CEST: 120, WET: 0, WEST: 60, EET: 120, EEST: 180,
    PST: -480, PDT: -420, MST: -420, MDT: -360, EST: -300, EDT: -240, IST: 330, SGT: 480, HKT: 480,
    AEST: 600, AEDT: 660, ICT: 420, WIB: 420,
  };
  // Publisher detection for the Proceedings column and filter. Label and filter keys both use the
  // current main outlet: the first ";" segment, ignoring parentheses about past or additional outlets.
  const KOREAN_SOC = /\b(KIISE|KIPS|KICS|KSII|IEIE|KIISC|KIICE|KMMS|KMIS|KSCI|KIIS|KAIA)\b/;
  const PUBS = [
    ['ieee', 'IEEE', /\bIEEE\b/i], ['springer', 'Springer', /\bSpringer\b|\b(LNCS|LNAI|CCIS|LNICST|LNDECT|AICT|LNNS)\b/],
    ['acm', 'ACM', /\bACM\b/], ['usenix', 'USENIX', /\bUSENIX\b/i], ['acl', 'ACL Anthology', /ACL Anthology/i],
    ['pmlr', 'PMLR', /\bPMLR\b/], ['openreview', 'OpenReview', /OpenReview/i], ['scitepress', 'SCITEPRESS', /SCITEPRESS/i],
    ['ndss', 'NDSS', /\bNDSS\b|Internet Society/], ['iacr', 'IACR', /\bIACR\b/], ['aaai', 'AAAI', /\bAAAI\b/],
    ['ijcai', 'IJCAI', /\bIJCAI\b/], ['neurips', 'NeurIPS', /NeurIPS/], ['ifaamas', 'IFAAMAS', /IFAAMAS/],
    ['elsevier', 'Elsevier', /Elsevier/i], ['ios', 'IOS Press', /IOS Press/i], ['siam', 'SIAM', /\bSIAM\b/],
    ['isca', 'ISCA', /\bISCA\b/], ['easychair', 'EasyChair', /EasyChair/i], ['ceur', 'CEUR-WS', /CEUR/i],
    ['jstage', 'J-STAGE', /J-STAGE/i], ['ipsjdl', 'IPSJ Digital Library', /IPSJ Digital Library|Joho Gakkai Hiroba/i],
    ['anlp', 'ANLP website', /\bANLP\b/], ['ieice', 'IEICE', /\bIEICE\b/], ['ipsj', 'IPSJ', /\bIPSJ\b/],
    ['korea', 'Korean society', KOREAN_SOC],
    ['iaria', 'IARIA', /\bIARIA\b/],
  ];
  const SERIES = /\b(LNCS|LNAI|CCIS|LNICST|LNDECT|AICT|LNNS)\b/;
  const HIST = /\([^()]*\b(until|through|previously|formerly|also|before|since|earlier|not in)\b[^()]*\)/gi;
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const DAY = 86400000;
  const RESOURCES = [
    { name: 'Security & Privacy Deadlines', url: 'https://sec-deadlines.github.io/', tag: 'Security', desc: 'Countdowns for security and privacy conferences and many co-located workshops.' },
    { name: 'CCF Deadlines (ccfddl)', url: 'https://ccfddl.com/', tag: 'All CS', desc: 'Deadlines across computer science with CCF, CORE and THCPL ranks. Open data on GitHub.' },
    { name: 'AI Deadlines (Hugging Face)', url: 'https://huggingface.co/spaces/huggingface/ai-deadlines', tag: 'AI', desc: 'Countdowns for machine learning, NLP, vision and speech conferences.' },
    { name: 'WikiCFP', url: 'http://www.wikicfp.com/cfp/', tag: 'All CS', desc: 'Calls for papers, including many small and regional conferences.' },
    { name: 'CORE Conference Portal', url: 'https://portal.core.edu.au/conf-ranks/', tag: 'Rankings', desc: 'ICORE2026 conference rankings (A*, A, B, C) and older editions.' },
    { name: 'CCF recommended venues', url: 'https://www.ccf.org.cn/Academic_Evaluation/By_category/', tag: 'Rankings', desc: 'China Computer Federation list of recommended conferences and journals (A, B, C).' },
    { name: 'IACR events calendar', url: 'https://iacr.org/events/', tag: 'Crypto', desc: 'Cryptography conferences, workshops and schools.' },
    { name: 'ACL Rolling Review dates', url: 'https://aclrollingreview.org/dates', tag: 'NLP', desc: 'ARR submission cycles that feed ACL, EMNLP, NAACL and EACL.' },
    { name: 'researchr conferences', url: 'https://conf.researchr.org/', tag: 'Software', desc: 'Software engineering and programming language conferences (ICSE, FSE, ASE, ...).' },
    { name: 'CSRankings', url: 'https://csrankings.org/', tag: 'Rankings', desc: 'Which venues count as the top venues of each CS area.' },
    { name: 'Google Scholar Metrics', url: 'https://scholar.google.com/citations?view_op=top_venues&hl=en&vq=eng_computersecuritycryptography', tag: 'Rankings', desc: 'h5-index of venues by field (link opens Security & Cryptography).' },
    { name: 'dblp', url: 'https://dblp.org/', tag: 'All CS', desc: 'Past proceedings and papers of almost every CS venue.' },
  ];

  // ---------------------------------------------------------------- helpers
  const $ = (sel) => document.querySelector(sel);
  const pad = (n) => String(n).padStart(2, '0');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  const fmtUTC = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  const fmtLocal = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });

  function parseISO(iso) { const [y, m, d] = iso.split('-').map(Number); return { y, m, d }; }
  function isoUTC(iso) { const p = parseISO(iso); return Date.UTC(p.y, p.m - 1, p.d); }
  function isLeap(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }
  function shiftYears(iso, n) {
    const p = parseISO(iso); const y = p.y + n;
    const d = p.m === 2 && p.d === 29 && !isLeap(y) ? 28 : p.d;
    return `${y}-${pad(p.m)}-${pad(d)}`;
  }
  function localISO(ms) { const d = new Date(ms); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
  function addDaysISO(iso, n) { const d = new Date(isoUTC(iso) + n * DAY); return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`; }
  function tzOffset(tz) {
    if (!tz) return TZ.AoE;
    if (Object.prototype.hasOwnProperty.call(TZ, tz)) return TZ[tz];
    const m = /^(?:UTC|GMT)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$/.exec(tz);
    return m ? (m[1] === '-' ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3] || 0)) : TZ.AoE;
  }
  function instant(date, time, tz) {
    const p = parseISO(date); const [hh, mm] = (time || '23:59').split(':').map(Number);
    return Date.UTC(p.y, p.m - 1, p.d, hh, mm) - tzOffset(tz) * 60000;
  }
  function fmtDate(iso) { return fmtUTC.format(isoUTC(iso)); }
  function fmtRange(a, b) {
    if (!b || a === b) return fmtDate(a);
    const pa = parseISO(a), pb = parseISO(b);
    if (pa.y === pb.y && pa.m === pb.m) return `${MONTHS[pa.m - 1]} ${pa.d}-${pb.d}, ${pa.y}`;
    if (pa.y === pb.y) return `${MONTHS[pa.m - 1]} ${pa.d} - ${MONTHS[pb.m - 1]} ${pb.d}, ${pa.y}`;
    return `${fmtDate(a)} - ${fmtDate(b)}`;
  }
  function fmtMonthOnly(it) { return `~${MONTHS[it.m - 1]} ${it.y}`; }
  function monthsText(ms) { return (ms || []).map((m) => MONTHS[m - 1]).join(', '); }
  function coreOrder(v) {
    if (!v) return 99;
    if (v in CORE_ORDER) return CORE_ORDER[v];
    return /^(National|Regional|Australasian)/.test(v) ? 4 : /^(Journal|Multiconference)/.test(v) ? 5 : 98;
  }
  function isSub(kind) { return kind === 'abstract' || kind === 'submission'; }
  function leftText(t) {
    const diff = t - state.now;
    if (diff < 0) return { text: 'passed', cls: 'later' };
    const days = Math.floor(diff / DAY);
    const cls = diff < 7 * DAY ? 'urgent' : diff < 30 * DAY ? 'soon' : 'later';
    if (days >= 2) return { text: `in ${days} days`, cls };
    const hours = Math.floor(diff / 3600000);
    if (hours >= 1) return { text: `in ${hours} h`, cls };
    return { text: `in ${Math.max(1, Math.floor(diff / 60000))} min`, cls };
  }

  // ---------------------------------------------------------------- state
  const DEFAULT_FILTERS = () => ({
    q: '', areas: new Set(), tiers: new Set(), types: new Set(), region: '', org: '', core: '', ccf: '', proc: '',
    dlFrom: '', dlTo: '', cfFrom: '', cfTo: '', within: 0, est: true, upcoming: false,
  });
  const now0 = Date.now();
  const state = {
    meta: {}, all: [], byId: new Map(), now: now0, today: localISO(now0),
    view: 'table', sort: { key: 'deadline', dir: 1 }, f: DEFAULT_FILTERS(), open: new Set(),
    cal: { y: new Date(now0).getFullYear(), m: new Date(now0).getMonth() }, calSelected: null,
    tl: { y: new Date(now0).getFullYear(), m: new Date(now0).getMonth() },
    calShow: { dl: true, cf: true, nt: false },
  };

  // ---------------------------------------------------------------- data preparation
  function mk(c, ed, kind, date, extra) {
    const it = Object.assign({ c, ed, kind, date, est: false }, extra || {});
    if (kind === 'conf') { it.end = it.end || date; it.t = isoUTC(date); it.tEnd = isoUTC(it.end) + DAY; }
    else if (!it.monthOnly) it.t = instant(date, it.time, it.tz);
    return it;
  }

  function prepare(c) {
    c.areas = c.areas || []; c.notes = c.notes || []; c.editions = c.editions || [];
    c.rank = c.rank || {}; c.typical = c.typical || {}; c.links = c.links || {}; c.sources = c.sources || [];
    c.organizer_country = c.organizer_country || [];
    const step = c.frequency === 'biennial' ? 2 : 1;
    const now = state.now;
    const items = [];
    for (const ed of c.editions) {
      const tentative = ed.status === 'tentative';
      for (const d of ed.deadlines || []) items.push(mk(c, ed, d.kind, d.date, { time: d.time, tz: d.tz, label: d.label, tentative }));
      if (ed.start) items.push(mk(c, ed, 'conf', ed.start, { end: ed.end, location: ed.location, tentative }));
    }
    const est = [];
    {
      const hasFutureSub = items.some((i) => isSub(i.kind) && i.t >= now);
      const withSubs = c.editions.filter((e) => (e.deadlines || []).some((d) => isSub(d.kind)));
      if (!hasFutureSub && withSubs.length) {
        const src = withSubs[withSubs.length - 1];
        const subs = src.deadlines.filter((d) => isSub(d.kind));
        const last = subs[subs.length - 1];
        let k = step;
        while (instant(shiftYears(last.date, k), last.time, last.tz) < now) k += step;
        const year = src.year + k;
        for (const d of src.deadlines) {
          est.push(mk(c, src, d.kind, shiftYears(d.date, k), { time: d.time, tz: d.tz, label: d.label, est: true, estYear: year, basedOn: src.year }));
        }
        const actualSameYear = c.editions.some((e) => e.year === year && e.start);
        if (src.start && !actualSameYear) {
          est.push(mk(c, src, 'conf', shiftYears(src.start, k), { end: shiftYears(src.end || src.start, k), location: src.location, est: true, estYear: year, basedOn: src.year }));
        }
      } else if (!hasFutureSub && (c.typical.deadline_months || []).length) {
        const it = nextMonthOnly(c.typical.deadline_months);
        est.push(Object.assign(it, { c, kind: 'submission', est: true, monthOnly: true }));
      }
      const hasFutureConf = items.concat(est).some((i) => i.kind === 'conf' && i.tEnd > now);
      if (!hasFutureConf) {
        const withConf = c.editions.filter((e) => e.start);
        if (withConf.length) {
          const src = withConf[withConf.length - 1];
          let k = step;
          while (isoUTC(shiftYears(src.end || src.start, k)) + DAY < now) k += step;
          est.push(mk(c, src, 'conf', shiftYears(src.start, k), { end: shiftYears(src.end || src.start, k), location: src.location, est: true, estYear: src.year + k, basedOn: src.year }));
        } else if ((c.typical.conference_months || []).length) {
          const it = nextMonthOnly(c.typical.conference_months);
          est.push(Object.assign(it, { c, kind: 'conf', est: true, monthOnly: true, tEnd: it.t }));
        }
      }
    }
    items.sort((a, b) => a.t - b.t); est.sort((a, b) => a.t - b.t);
    c._items = items; c._est = est;
    c._nextSub = items.find((i) => isSub(i.kind) && i.t >= now) || null;
    c._nextSubEst = est.find((i) => isSub(i.kind) && i.t >= now) || null;
    c._nextConf = items.find((i) => i.kind === 'conf' && i.tEnd > now) || null;
    c._nextConfEst = est.find((i) => i.kind === 'conf' && i.tEnd > now) || null;
    c._proc = procInfo(c);
    const locs = c.editions.map((e) => e.location).filter(Boolean).join(' ');
    c._hay = [c.id, c.name, c.full_name, c.name_local, c.organizer, c.proceedings, locs, REGIONS[c.region],
      c.areas.map((a) => AREAS[a]).join(' '), c.notes.join(' '), (c.indexing || []).join(' '),
      c.organizer_country.map((o) => ORG[o]).join(' ')].join(' \u0001 ').toLowerCase();
  }

  // has: papers are published somewhere; refereed: counts as a formal publication (not marked archival: false).
  function primary(raw) {
    // Drop parentheticals about other or past outlets, keep the first ';' segment (the current main outlet).
    const first = raw.replace(HIST, ' ').split(';')[0];
    const bare = first.replace(/\([^()]*\)/g, ' ').replace(/\s+/g, ' ').trim();
    for (const text of [bare, first]) {
      const hits = PUBS.map((p) => [p, text.search(p[2])]).filter(([, i]) => i >= 0).sort((a, b) => a[1] - b[1]).map(([p]) => p)
        .filter(([k], _, all) => !(k === 'ipsj' && all.some(([x]) => x === 'ipsjdl')));
      if (hits.length) return { hits, text };
    }
    return { hits: [], text: bare };
  }
  function procInfo(c) {
    const raw = c.proceedings || '';
    if (!raw) return { has: null, keys: [], label: '', raw: '' };
    if (/^none\b/i.test(raw)) return { has: false, keys: [], label: /participants only/i.test(raw) ? 'Participants only' : 'None', raw };
    const { hits, text } = primary(raw);
    const series = SERIES.exec(text);
    const names = hits.map(([k, name]) => (k === 'springer' && series ? `Springer ${series[1]}`
      : k === 'ieee' && /Xplore/i.test(text) ? 'IEEE Xplore'
      : k === 'ieee' && /CS Digital Library|Computer Society Digital Library|CSDL/i.test(text) ? 'IEEE CSDL' : k === 'acm' && /\bDL\b|Digital Library/.test(text) ? 'ACM DL'
      : k === 'korea' ? text.match(KOREAN_SOC)[0] : name));
    // Show every outlet the filter uses (at most three), so a filter hit is always visible in the label.
    const shown = names.slice(0, 3);
    let label = shown.length ? shown.join(' / ') : text.split(/\s*,\s*/)[0];
    if (!shown.length && label.length > 30) label = `${label.slice(0, 30).replace(/\s+\S*$/, '')}…`;
    return { has: true, refereed: c.archival !== false, keys: hits.length ? hits.slice(0, 3).map(([k]) => k) : ['other'], label, raw, lncs: /\bLNCS\b/.test(text) };
  }

  // Nearest month in `months` that has not ended yet (end of month, AoE).
  function nextMonthOnly(months) {
    const cy = new Date(state.now).getUTCFullYear();
    let best = null;
    for (const m of months) {
      for (let y = cy - 1; y <= cy + 2; y++) {
        const t = Date.UTC(y, m, 1) + 12 * 3600000;
        if (t < state.now) continue;
        const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
        if (!best || t < best.t) best = { y, m, t, date: `${y}-${pad(m)}-01`, end: `${y}-${pad(m)}-${pad(last)}` };
        break;
      }
    }
    return best;
  }

  // ---------------------------------------------------------------- filtering
  function subItems(c) { return state.f.est ? c._items.concat(c._est) : c._items; }
  function inRange(it, from, to) {
    const a = it.date;
    const b = it.monthOnly || it.kind === 'conf' ? it.end : it.date;
    return (!from || b >= from) && (!to || a <= to);
  }
  function withinWindow(i) { return i.t >= state.now && i.t <= state.now + state.f.within * DAY; }
  function shownDeadline(c) {
    const f = state.f;
    if (f.within) {
      return subItems(c).filter((i) => isSub(i.kind) && !i.monthOnly && withinWindow(i)).sort((a, b) => a.t - b.t)[0] || null;
    }
    if (f.dlFrom || f.dlTo) {
      const list = subItems(c).filter((i) => isSub(i.kind) && inRange(i, f.dlFrom, f.dlTo)).sort((a, b) => a.t - b.t);
      const future = list.find((i) => i.t >= state.now);
      return future || list[list.length - 1] || null;
    }
    return c._nextSub || (f.est ? c._nextSubEst : null);
  }
  function shownConf(c) {
    const f = state.f;
    if (f.cfFrom || f.cfTo) {
      const list = subItems(c).filter((i) => i.kind === 'conf' && inRange(i, f.cfFrom, f.cfTo)).sort((a, b) => a.t - b.t);
      return list[0] || null;
    }
    return c._nextConf || (f.est ? c._nextConfEst : null);
  }

  function matches(c) {
    const f = state.f;
    if (f.q) {
      for (const tok of f.q.toLowerCase().split(/\s+/).filter(Boolean)) if (!c._hay.includes(tok)) return false;
    }
    if (f.areas.size && !c.areas.some((a) => f.areas.has(a))) return false;
    if (f.tiers.size && !f.tiers.has(c.tier)) return false;
    if (f.types.size && !f.types.has(c.type)) return false;
    if (f.region) {
      if (f.region === 'asia') { if (!ASIA.has(c.region)) return false; }
      else if (f.region === 'other') { if (['japan', 'korea', 'taiwan', 'china', 'southeast-asia', 'south-asia', 'asia-pacific', 'europe', 'north-america', 'worldwide'].includes(c.region)) return false; }
      else if (c.region !== f.region) return false;
    }
    const core = c.rank.core;
    if (f.core) {
      const o = coreOrder(core);
      if (f.core === 'A+' && o > 1) return false;
      else if (f.core === 'B+' && o > 2) return false;
      else if (f.core === 'C+' && o > 3) return false;
      else if (f.core === 'none' && o <= 3) return false;
      else if (['A*', 'A', 'B', 'C'].includes(f.core) && core !== f.core) return false;
    }
    if (f.org) {
      if (f.org === 'asia') { if (!c.organizer_country.some((o) => ASIA_ORG.has(o))) return false; }
      else if (!c.organizer_country.includes(f.org)) return false;
    }
    if (f.proc) {
      const p = c._proc;
      if (f.proc === 'yes' && p.has !== true) return false;
      else if (f.proc === 'refereed' && !(p.has === true && p.refereed)) return false;
      else if (f.proc === 'nonref' && !(p.has === true && !p.refereed)) return false;
      else if (f.proc === 'no' && p.has !== false) return false;
      else if (f.proc === 'lncs' && !p.lncs) return false;
      else if (!['yes', 'refereed', 'nonref', 'no', 'lncs'].includes(f.proc) && !p.keys.includes(f.proc)) return false;
    }
    const ccf = c.rank.ccf;
    if (f.ccf) {
      if (f.ccf === 'listed' && !ccf) return false;
      else if (f.ccf === 'none' && ccf) return false;
      else if (['A', 'B', 'C'].includes(f.ccf) && ccf !== f.ccf) return false;
    }
    if (f.within) {
      if (!subItems(c).some((i) => isSub(i.kind) && !i.monthOnly && withinWindow(i))) return false;
    } else if (f.dlFrom || f.dlTo) {
      if (!subItems(c).some((i) => isSub(i.kind) && inRange(i, f.dlFrom, f.dlTo))) return false;
    }
    if (f.cfFrom || f.cfTo) {
      if (!subItems(c).some((i) => i.kind === 'conf' && inRange(i, f.cfFrom, f.cfTo))) return false;
    }
    if (f.upcoming && !(c._nextSub || (f.est && c._nextSubEst))) return false;
    return true;
  }

  function sortKey(c, key) {
    switch (key) {
      case 'name': return c.name.toLowerCase();
      case 'tier': return TIER_ORDER[c.tier] ?? 9;
      case 'core': return coreOrder(c.rank.core);
      case 'ccf': return c.rank.ccf in CCF_ORDER ? CCF_ORDER[c.rank.ccf] : 99;
      case 'region': return (REGIONS[c.region] || 'zz').toLowerCase();
      case 'org': return c.organizer_country.length ? c.organizer_country.map((o) => ORG[o]).join('+').toLowerCase() : '~~~';
      case 'proc': return c._proc.has === true ? c._proc.label.toLowerCase() : c._proc.has === false ? '~~none' : '~~~';
      case 'conf': { const i = shownConf(c); return i ? i.t : Infinity; }
      default: {
        const i = shownDeadline(c);
        if (!i) return Infinity;
        return i.t < state.now ? 1e15 + (state.now - i.t) : i.t; // passed ones after upcoming ones
      }
    }
  }

  function filtered() {
    const { key, dir } = state.sort;
    const list = state.all.filter(matches);
    list.sort((a, b) => {
      const ka = sortKey(a, key), kb = sortKey(b, key);
      if (ka === kb || (ka === Infinity && kb === Infinity)) {
        const da = sortKey(a, 'deadline'), db = sortKey(b, 'deadline');
        if (da !== db) return da < db ? -1 : 1;
        return a.name.localeCompare(b.name);
      }
      if (ka === Infinity) return 1;
      if (kb === Infinity) return -1;
      if (key === 'deadline' && (ka >= 1e15 || kb >= 1e15)) return ka < kb ? -1 : 1; // passed rows stay last
      return (ka < kb ? -1 : 1) * dir;
    });
    return list;
  }

  // ---------------------------------------------------------------- links
  function repo() {
    if (state.meta.repo) return state.meta.repo;
    const h = location.hostname;
    if (h.endsWith('.github.io')) {
      const owner = h.split('.')[0]; const name = location.pathname.split('/').filter(Boolean)[0];
      return name ? `${owner}/${name}` : `${owner}/${h}`;
    }
    return '';
  }
  const isURL = (u) => typeof u === 'string' && /^https?:\/\/[^\s/]+\S*$/.test(u);
  function sourceHTML(s) {
    const m = /^(\S+)(\s+.*)?$/.exec(String(s).trim());
    if (!m || !isURL(m[1])) return esc(s);
    return `<a href="${esc(m[1])}" target="_blank" rel="noopener">${esc(m[1])}</a>${m[2] ? esc(m[2]) : ''}`;
  }
  const gh = (path) => `https://github.com/${repo()}${path}`;
  const branch = () => state.meta.branch || 'main';
  function editUrl(c) { return gh(`/edit/${branch()}/data/conferences/${encodeURIComponent(c.id)}.yml`); }
  function reportUrl(c) {
    const p = new URLSearchParams({ template: 'update-conference.yml', title: `[Update] ${c.name}`, conference: c.id });
    return gh(`/issues/new?${p}`);
  }

  // ---------------------------------------------------------------- rendering helpers
  function tierBadge(c) { return `<span class="badge tier-${esc(c.tier)}">${esc(TIERS[c.tier] || c.tier)}</span>`; }
  function typeBadge(c) { return c.type && c.type !== 'conference' ? ` <span class="badge type-badge">${esc(TYPES[c.type] || c.type)}</span>` : ''; }
  function orgCell(c) {
    if (!c.organizer_country.length) return '<span class="rank none" title="not recorded">&middot;</span>';
    return `<span class="org" title="${esc(c.organizer || '')}">${c.organizer_country.map((o) => esc(ORG[o] || o)).join(' + ')}</span>`;
  }
  function procCell(c) {
    const p = c._proc;
    if (p.has === false) return `<span class="proc none" title="${esc(p.raw)}">${esc(p.label)}</span>`;
    if (p.has === null) return '<span class="rank none" title="not recorded">&middot;</span>';
    return `<span class="proc" title="${esc(p.raw)}">${esc(p.label)}</span>${p.refereed ? '' : '<div class="sub" title="Does not count as a formal publication: no peer review, or only preliminary proceedings">non-archival</div>'}`;
  }
  function rankCell(v, title) { return v ? `<span class="rank" title="${esc(title)}">${esc(v)}</span>` : `<span class="rank none" title="not listed">&middot;</span>`; }
  function deadlineHTML(it) {
    if (!it) return '<span class="sub">no date yet</span>';
    if (it.monthOnly) return `<span class="est">${fmtMonthOnly(it)}</span><div class="sub">estimated from usual month</div>`;
    const lbl = [KIND[it.kind], it.label, it.tentative ? 'tentative' : '', it.est ? `estimated from ${it.basedOn}` : ''].filter(Boolean).join(' \u00b7 ');
    const left = leftText(it.t);
    const aoe = it.tz ? '' : ` <span class="sub" title="${it.time ? 'No time zone stated' : 'No time stated'} in the call for papers; 23:59 AoE assumed">(AoE?)</span>`;
    return `<span class="nowrap${it.est ? ' est' : ''}" ${it.est ? `title="Estimated from the ${it.basedOn} edition"` : ''}>${it.est ? '~' : ''}${fmtDate(it.date)}</span>` +
      `<div class="sub">${esc(lbl)}</div><div><span class="left ${left.cls}" data-t="${it.t}">${left.text}</span>${aoe}</div>`;
  }
  function confHTML(it) {
    if (!it) return '<span class="sub">no date yet</span>';
    if (it.monthOnly) return `<span class="est">${fmtMonthOnly(it)}</span>`;
    const running = it.t <= state.now && it.tEnd > state.now;
    return `<span class="nowrap${it.est ? ' est' : ''}">${it.est ? '~' : ''}${fmtRange(it.date, it.end)}</span>` +
      (it.est ? `<div class="sub">estimated from ${it.basedOn}</div>` : running ? '<div class="left urgent">happening now</div>' : it.tentative ? '<div class="sub">tentative</div>' : '');
  }
  function locationHTML(c, conf) {
    const region = `<div class="sub">${esc(REGIONS[c.region] || '')}</div>`;
    if (conf && !conf.est && conf.location) return `${esc(conf.location)}${region}`;
    const last = c.editions.slice().reverse().find((e) => e.location);
    return last ? `<span class="sub">${esc(last.year)}: ${esc(last.location)}</span>${region}` : region;
  }

  function deadlineLi(d, ed) {
    const t = instant(d.date, d.time, d.tz);
    const past = t < state.now;
    const when = `${fmtDate(d.date)}${d.time ? ` ${esc(d.time)}` : ''}${d.tz ? ` ${esc(d.tz)}` : ' AoE?'}`;
    const local = `Your time: ${fmtLocal.format(t)}${d.tz ? '' : d.time ? ' (no time zone stated, AoE assumed)' : ' (no time stated, 23:59 AoE assumed)'}`;
    return `<li class="${past ? 'past' : ''}" title="${esc(local)}"><span class="kind">${esc(KIND[d.kind] || d.kind)}</span>${when}${d.label ? ` \u00b7 ${esc(d.label)}` : ''}</li>`;
  }

  function detailsHTML(c) {
    const eds = c.editions.slice().reverse();
    const estCycle = c._est.filter((i) => !i.monthOnly);
    let edRows = '';
    if (estCycle.length && state.f.est) {
      const groups = new Map();
      for (const i of estCycle) { const k = `${i.estYear}|${i.basedOn}`; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(i); }
      for (const g of [...groups.values()].sort((a, b) => b[0].estYear - a[0].estYear)) {
        const conf = g.find((i) => i.kind === 'conf');
        const dls = g.filter((i) => i.kind !== 'conf');
        edRows += `<tr class="est"><td>~${g[0].estYear}<div class="sub">estimated from ${g[0].basedOn}</div></td>` +
          `<td>${conf ? `~${fmtRange(conf.date, conf.end)}` : ''}</td><td></td>` +
          `<td><ul class="dl-list">${dls.map((i) => `<li><span class="kind">${esc(KIND[i.kind])}</span>~${fmtDate(i.date)}${i.label ? ` \u00b7 ${esc(i.label)}` : ''}</li>`).join('')}</ul></td></tr>`;
      }
    }
    for (const ed of eds) {
      edRows += `<tr><td>${isURL(ed.url) ? `<a href="${esc(ed.url)}" target="_blank" rel="noopener">${esc(ed.year)}</a>` : esc(ed.year)}` +
        `${ed.label ? `<div class="sub">${esc(ed.label)}</div>` : ''}${ed.status === 'tentative' ? '<div class="sub">tentative</div>' : ''}</td>` +
        `<td>${ed.start ? fmtRange(ed.start, ed.end) : ''}</td><td>${esc(ed.location || '')}</td>` +
        `<td><ul class="dl-list">${(ed.deadlines || []).map((d) => deadlineLi(d, ed)).join('')}</ul></td></tr>`;
    }
    const facts = [
      ['Organizer', c.organizer], ['Run by', c.organizer_country.map((o) => ORG[o] || o).join(', ')], ['Type', TYPES[c.type]], ['Region', REGIONS[c.region]], ['Language', LANG[c.language]],
      ['Held', FREQ[c.frequency]],
      ['Proceedings', c.proceedings ? `${c.proceedings}${c.archival === false && !/non-archival|not peer-reviewed|non-refereed/i.test(c.proceedings) ? ' (non-archival)' : ''}` : (c.archival === false ? 'Non-archival' : '')],
      ['Indexing', (c.indexing || []).join(', ')],
      [`CORE`, c.rank.core ? `${c.rank.core} (${c.rank.core_source || state.meta.core_edition || 'CORE'})` : ''],
      [`CCF`, c.rank.ccf ? `${c.rank.ccf} (${state.meta.ccf_edition || 'CCF'})` : ''],
      ['Acceptance', c.acceptance_rate], ['Fee', c.fee],
      ['Usual deadline', monthsText(c.typical.deadline_months)], ['Usual dates', monthsText(c.typical.conference_months)],
    ].filter(([, v]) => v);
    const links = [['Website', c.links.website], ['dblp', c.links.dblp], ['WikiCFP', c.links.wikicfp]].filter(([, v]) => isURL(v));
    const repoOk = !!repo();
    return `<div class="details">
      <div>
        <h4>Notes</h4>
        ${c.notes.length ? `<ul class="notes">${c.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>` : '<p class="sub">No notes yet.</p>'}
        ${(c.unverified || []).length ? `<p class="warn">Not yet confirmed: ${c.unverified.map(esc).join('; ')}</p>` : ''}
        <h4 style="margin-top:14px">Editions and deadlines</h4>
        ${edRows ? `<div style="overflow-x:auto"><table class="editions"><thead><tr><th>Year</th><th>Dates</th><th>Location</th><th>Deadlines (hover for your local time)</th></tr></thead><tbody>${edRows}</tbody></table></div>` : '<p class="sub">No dates recorded yet.</p>'}
      </div>
      <div>
        <h4>Facts</h4>
        <dl class="facts">${facts.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
        ${links.length ? `<h4 style="margin-top:14px">Links</h4><div class="links">${links.map(([k, v]) => `<a href="${esc(v)}" target="_blank" rel="noopener">${esc(k)}</a>`).join('')}</div>` : ''}
        ${c.sources.length ? `<h4 style="margin-top:14px">Sources</h4><ul class="sources">${c.sources.map((s) => `<li>${sourceHTML(s)}</li>`).join('')}</ul>` : ''}
        <div class="actions" style="margin-top:14px">
          ${repoOk ? `<a class="btn small" href="${esc(editUrl(c))}" target="_blank" rel="noopener">Edit on GitHub</a><a class="btn small" href="${esc(reportUrl(c))}" target="_blank" rel="noopener">Report outdated info</a>` : ''}
          <span class="sub">${c.last_verified ? `Last verified ${esc(c.last_verified)}` : 'Not verified yet'}</span>
        </div>
      </div>
    </div>`;
  }

  function openDialog(id) {
    const c = state.byId.get(id); if (!c) return;
    $('#detail-body').innerHTML = `<h2 id="detail-title">${esc(c.name)} ${tierBadge(c)}${typeBadge(c)}</h2>` +
      `<div class="sub" style="font-size:13px">${esc(c.full_name)}${c.name_local ? ` \u00b7 ${esc(c.name_local)}` : ''}</div>` +
      `<div class="tags" style="margin-top:6px">${c.areas.map((a) => `<span class="tag">${esc(AREAS[a] || a)}</span>`).join('')}</div>` + detailsHTML(c);
    const dlg = $('#detail');
    if (typeof dlg.showModal === 'function') { if (!dlg.open) dlg.showModal(); } else dlg.setAttribute('open', '');
  }

  // ---------------------------------------------------------------- table view
  function renderTable(list) {
    const rows = [];
    for (const c of list) {
      const open = state.open.has(c.id);
      const dl = shownDeadline(c), cf = shownConf(c);
      rows.push(`<tr class="row${open ? ' open' : ''}" data-id="${esc(c.id)}">
        <td class="name-cell"><button type="button" class="name-btn" aria-expanded="${open}"><span class="caret" aria-hidden="true">&#9654;</span><strong>${esc(c.name)}</strong>${typeBadge(c)}</button>
          <div class="full">${esc(c.full_name)}</div>${c.name_local ? `<div class="local">${esc(c.name_local)}</div>` : ''}</td>
        <td data-label="Tier">${tierBadge(c)}</td>
        <td data-label="Run by">${orgCell(c)}</td>
        <td class="areas-cell" data-label="Areas"><div class="tags">${c.areas.map((a) => `<span class="tag">${esc(AREAS[a] || a)}</span>`).join('')}</div></td>
        <td data-label="CORE">${rankCell(c.rank.core, c.rank.core_source || state.meta.core_edition)}</td>
        <td data-label="CCF">${rankCell(c.rank.ccf, state.meta.ccf_edition)}</td>
        <td data-label="Proceedings">${procCell(c)}</td>
        <td data-label="Deadline">${deadlineHTML(dl)}</td>
        <td data-label="Conference">${confHTML(cf)}</td>
        <td data-label="Location">${locationHTML(c, cf)}</td>
      </tr>`);
      if (open) rows.push(`<tr class="detail-row" data-for="${esc(c.id)}"><td colspan="10">${detailsHTML(c)}</td></tr>`);
    }
    $('#rows').innerHTML = rows.join('');
    $('#empty').hidden = list.length > 0;
    document.querySelectorAll('.conf-table th[data-sort]').forEach((th) => {
      if (th.dataset.sort === state.sort.key) th.setAttribute('aria-sort', state.sort.dir > 0 ? 'ascending' : 'descending');
      else th.removeAttribute('aria-sort');
    });
  }

  // ---------------------------------------------------------------- calendar view
  function calendarEvents(list) {
    const map = new Map();
    const add = (key, ev) => { if (!map.has(key)) map.set(key, []); map.get(key).push(ev); };
    for (const c of list) {
      for (const it of subItems(c)) {
        if (it.monthOnly) continue;
        if (isSub(it.kind) && state.calShow.dl) add(it.date, { it, cls: 'dl', text: `${c.name} ${KIND[it.kind].toLowerCase()}` });
        else if (it.kind === 'notification' && state.calShow.nt) add(it.date, { it, cls: 'nt', text: `${c.name} notification` });
        else if (it.kind === 'conf' && state.calShow.cf) {
          let d = it.date; let n = 0;
          while (d <= it.end && n < 21) { add(d, { it, cls: 'cf', text: c.name }); d = addDaysISO(d, 1); n++; }
        }
      }
    }
    const rank = { dl: 0, nt: 1, cf: 2 };
    for (const evs of map.values()) evs.sort((a, b) => rank[a.cls] - rank[b.cls] || (TIER_ORDER[a.it.c.tier] - TIER_ORDER[b.it.c.tier]) || a.text.localeCompare(b.text));
    return map;
  }

  function evButton(ev) {
    const it = ev.it;
    const title = it.kind === 'conf'
      ? `${it.c.name}${it.est ? ' (estimated)' : ''}${it.tentative ? ' (tentative)' : ''}: ${fmtRange(it.date, it.end)}${it.location ? `, ${it.location}` : ''}`
      : `${it.c.name} ${KIND[it.kind]}${it.label ? ` (${it.label})` : ''}${it.est ? ' (estimated)' : ''}${it.tentative ? ' (tentative)' : ''}: ${fmtDate(it.date)}${it.time ? ` ${it.time}` : ''} ${it.tz || 'AoE?'}`;
    const past = (it.kind === 'conf' ? it.tEnd : it.t) < state.now;
    return `<button type="button" class="ev ${ev.cls}${it.est ? ' est' : ''}${past ? ' past' : ''}" data-id="${esc(it.c.id)}" title="${esc(title)}${past ? ' (past)' : ''}">${it.est ? '~' : ''}${esc(ev.text)}</button>`;
  }

  function renderCalendar(list) {
    const { y, m } = state.cal;
    $('#cal-title').textContent = `${MONTHS_LONG[m]} ${y}`;
    const events = calendarEvents(list);
    const first = new Date(Date.UTC(y, m, 1));
    const offset = (first.getUTCDay() + 6) % 7; // Monday first
    const start = new Date(first.getTime() - offset * DAY);
    const lastDay = new Date(Date.UTC(y, m + 1, 0));
    const cells = Math.ceil((offset + lastDay.getUTCDate()) / 7) * 7;
    const html = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => `<div class="cal-head">${d}</div>`);
    for (let i = 0; i < cells; i++) {
      const d = new Date(start.getTime() + i * DAY);
      const iso = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
      const evs = events.get(iso) || [];
      const cls = ['cal-day'];
      if (d.getUTCMonth() !== m) cls.push('other');
      if (iso === state.today) cls.push('today');
      if (iso === state.calSelected) cls.push('selected');
      const shown = evs.slice(0, 4).map(evButton).join('');
      const more = evs.length > 4 ? `<span class="more">+${evs.length - 4} more</span>` : '';
      html.push(`<div class="${cls.join(' ')}" data-date="${iso}"><button type="button" class="num" aria-pressed="${iso === state.calSelected}" aria-label="${esc(fmtDate(iso))}, ${evs.length} ${evs.length === 1 ? 'item' : 'items'}">${d.getUTCDate()}</button>${shown}${more}</div>`);
    }
    $('#cal-grid').innerHTML = html.join('');
    state.calEvents = events;
    renderAgenda(events);
  }

  function renderAgenda(events) {
    const box = $('#cal-agenda');
    const sel = state.calSelected;
    if (!sel) {
      // Default: list everything in the visible month.
      const { y, m } = state.cal; const prefix = `${y}-${pad(m + 1)}-`;
      const days = [...events.keys()].filter((k) => k.startsWith(prefix)).sort();
      const dls = [];
      for (const k of days) for (const ev of events.get(k)) if (ev.cls !== 'cf') dls.push(ev);
      box.innerHTML = dls.length
        ? `<h3>Deadlines and notifications in ${MONTHS_LONG[m]} ${y} (${dls.length})</h3><ul>${dls.map((ev) => `<li><span class="sub nowrap">${fmtDate(ev.it.date)}</span>${evButton(ev).replace('class="ev', 'style="width:auto" class="ev')}${ev.it.label ? `<span class="sub">${esc(ev.it.label)}</span>` : ''}</li>`).join('')}</ul>`
        : `<p class="sub">No deadlines in ${MONTHS_LONG[m]} ${y} for the current filters.</p>`;
      return;
    }
    const evs = events.get(sel) || [];
    box.innerHTML = `<h3>${fmtDate(sel)} (${evs.length})</h3>` +
      (evs.length ? `<ul>${evs.map((ev) => `<li>${evButton(ev).replace('class="ev', 'style="width:auto" class="ev')}${ev.it.label ? `<span class="sub">${esc(ev.it.label)}</span>` : ''}${ev.it.kind === 'conf' && ev.it.location ? `<span class="sub">${esc(ev.it.location)}</span>` : ''}</li>`).join('')}</ul>` : '<p class="sub">Nothing on this day.</p>');
  }

  // ---------------------------------------------------------------- timeline view
  function renderTimeline(list) {
    const { y, m } = state.tl;
    const start = Date.UTC(y, m, 1), end = Date.UTC(y, m + 12, 1), span = end - start;
    $('#tl-title').textContent = `${MONTHS[m]} ${y} to ${MONTHS[(m + 11) % 12]} ${y + Math.floor((m + 11) / 12)}`;
    const cols = []; const heads = []; const grid = [];
    for (let i = 0; i < 12; i++) {
      const a = Date.UTC(y, m + i, 1), b = Date.UTC(y, m + i + 1, 1);
      const d = new Date(a);
      cols.push(`${(b - a) / DAY}fr`);
      if (i) grid.push(`linear-gradient(var(--border), var(--border)) ${(((a - start) / span) * 100).toFixed(3)}% 0 / 1px 100% no-repeat`);
      heads.push(`<span>${MONTHS[d.getUTCMonth()]}${d.getUTCMonth() === 0 || i === 0 ? ` ${d.getUTCFullYear()}` : ''}</span>`);
    }
    const pct = (t) => ((Math.min(Math.max(t, start), end) - start) / span) * 100;
    $('#timeline').style.setProperty('--grid', grid.join(', '));
    const rows = [];
    const scored = [];
    for (const c of list) {
      const its = subItems(c).filter((i) => !i.monthOnly && (isSub(i.kind) || i.kind === 'conf'));
      const vis = its.filter((i) => (i.kind === 'conf' ? i.tEnd > start && i.t < end : i.t >= start && i.t < end));
      if (!vis.length) continue;
      // Upcoming deadlines first (soonest on top), then venues with only a conference or past items.
      const nextDl = vis.find((i) => isSub(i.kind) && i.t >= state.now);
      const nextAny = vis.find((i) => (i.kind === 'conf' ? i.tEnd : i.t) >= state.now);
      scored.push({ c, vis, key: nextDl ? nextDl.t : nextAny ? 1e15 + nextAny.t : 2e15 + vis[0].t });
    }
    scored.sort((a, b) => a.key - b.key);
    for (const { c, vis } of scored) {
      const marks = vis.map((i) => {
        if (i.kind === 'conf') {
          const l = pct(i.t), r = pct(i.tEnd);
          return `<button type="button" class="tl-cf${i.est ? ' est' : ''}" data-id="${esc(c.id)}" style="left:${l}%;width:${Math.max(r - l, 0.4)}%" title="${esc(`${c.name}${i.est ? ' (estimated)' : ''}: ${fmtRange(i.date, i.end)}${i.location ? `, ${i.location}` : ''}`)}"></button>`;
        }
        return `<button type="button" class="tl-dl${i.est ? ' est' : ''}" data-id="${esc(c.id)}" style="left:${pct(i.t)}%" title="${esc(`${c.name} ${KIND[i.kind]}${i.label ? ` (${i.label})` : ''}${i.est ? ' (estimated)' : ''}${i.tentative ? ' (tentative)' : ''}: ${fmtDate(i.date)}`)}"></button>`;
      }).join('');
      rows.push(`<div class="tl-row"><div class="tl-label"><button type="button" data-id="${esc(c.id)}" title="${esc(c.full_name)}">${esc(c.name)}</button></div><div class="tl-track">${marks}</div></div>`);
    }
    const nowLine = state.now >= start && state.now < end ? `<div class="tl-now" style="left:${pct(state.now)}%"></div>` : '';
    $('#timeline').innerHTML =
      `<div class="tl-row tl-head"><div class="tl-label">${scored.length} conferences</div><div class="tl-track" style="grid-template-columns:${cols.join(' ')}">${heads.join('')}</div></div>` +
      (rows.length ? rows.join('').replace(/<div class="tl-track">/g, `<div class="tl-track">${nowLine}`) : '<p class="empty">Nothing in this period for the current filters.</p>');
  }

  // ---------------------------------------------------------------- ics export
  function icsExport(list) {
    const stamp = new Date(state.now).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    const fmt = (t) => new Date(t).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    const escT = (s) => String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
    const fold = (line) => { const out = []; let s = line; while (s.length > 74) { out.push(s.slice(0, 74)); s = ' ' + s.slice(74); } out.push(s); return out.join('\r\n'); };
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Conference Radar//EN', 'CALSCALE:GREGORIAN', 'X-WR-CALNAME:Conference deadlines'];
    let n = 0;
    for (const c of list) {
      for (const it of c._items) {
        if (!isSub(it.kind) || it.t < state.now) continue;
        n++;
        const year = it.ed ? it.ed.year : '';
        const summary = `${c.name} ${year} ${KIND[it.kind].toLowerCase()} deadline${it.label ? ` (${it.label})` : ''}${it.tentative ? ' (tentative)' : ''}`;
        const slug = String(it.label || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        const desc = `${c.full_name}\n${fmtDate(it.date)} ${it.time || '23:59'} ${it.tz || 'AoE'}${it.ed && it.ed.url ? `\n${it.ed.url}` : ''}`;
        lines.push('BEGIN:VEVENT', fold(`UID:${c.id}-${year}-${it.kind}-${it.date}-${slug}-${(it.time || '').replace(':', '')}@conference-radar`), `DTSTAMP:${stamp}`,
          `DTSTART:${fmt(it.t)}`, `DTEND:${fmt(it.t)}`, fold(`SUMMARY:${escT(summary)}`), fold(`DESCRIPTION:${escT(desc)}`));
        if (it.tentative) lines.push('STATUS:TENTATIVE');
        if (it.ed && it.ed.url) lines.push(fold(`URL:${it.ed.url}`));
        lines.push('END:VEVENT');
      }
    }
    lines.push('END:VCALENDAR');
    if (!n) { alert('No upcoming announced deadlines (estimates are not exported) in the current selection.'); return; }
    const blob = new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/calendar' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'conference-deadlines.ics';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  // ---------------------------------------------------------------- URL state
  function writeURL() {
    const f = state.f; const p = new URLSearchParams();
    if (state.view !== 'table') p.set('view', state.view);
    if (f.q) p.set('q', f.q);
    if (f.areas.size) p.set('area', [...f.areas].join(','));
    if (f.tiers.size) p.set('tier', [...f.tiers].join(','));
    if (f.types.size) p.set('type', [...f.types].join(','));
    for (const [k, v] of [['region', f.region], ['org', f.org], ['core', f.core], ['ccf', f.ccf], ['proc', f.proc], ['dlf', f.dlFrom], ['dlt', f.dlTo], ['cff', f.cfFrom], ['cft', f.cfTo]]) if (v) p.set(k, v);
    if (f.within) p.set('within', String(f.within));
    if (!f.est) p.set('est', '0');
    if (f.upcoming) p.set('up', '1');
    if (state.sort.key !== 'deadline' || state.sort.dir !== 1) p.set('sort', `${state.sort.key}${state.sort.dir < 0 ? '-' : ''}`);
    const qs = p.toString();
    try { history.replaceState(null, '', qs ? `?${qs}` : location.pathname); } catch (e) { /* file:// */ }
  }
  function readURL() {
    const p = new URLSearchParams(location.search); const f = state.f;
    const set = (s) => new Set((s || '').split(',').filter(Boolean));
    f.q = p.get('q') || ''; f.areas = set(p.get('area')); f.tiers = set(p.get('tier')); f.types = set(p.get('type'));
    f.region = p.get('region') || ''; f.org = p.get('org') || ''; f.core = p.get('core') || ''; f.ccf = p.get('ccf') || ''; f.proc = p.get('proc') || '';
    f.dlFrom = p.get('dlf') || ''; f.dlTo = p.get('dlt') || ''; f.cfFrom = p.get('cff') || ''; f.cfTo = p.get('cft') || '';
    f.within = [30, 90, 180].includes(Number(p.get('within'))) ? Number(p.get('within')) : 0;
    f.est = p.get('est') !== '0'; f.upcoming = p.get('up') === '1';
    const s = p.get('sort');
    if (s) state.sort = { key: s.replace(/-$/, ''), dir: s.endsWith('-') ? -1 : 1 };
    const v = p.get('view') || (location.hash === '#contribute' ? 'contribute' : '');
    if (['table', 'calendar', 'timeline', 'resources', 'contribute'].includes(v)) state.view = v;
    if (location.hash) { try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { /* file:// */ } }
  }

  // ---------------------------------------------------------------- controls
  function chip(group, key, label, n) {
    return `<button type="button" class="chip" data-group="${group}" data-key="${esc(key)}" aria-pressed="false" aria-label="${esc(label)}, ${n}">${esc(label)}<span class="n" aria-hidden="true">${n}</span></button>`;
  }
  function buildControls() {
    const count = (fn) => { const m = new Map(); for (const c of state.all) for (const k of fn(c)) m.set(k, (m.get(k) || 0) + 1); return m; };
    const ac = count((c) => c.areas), tc = count((c) => [c.tier]), yc = count((c) => [c.type]), rc = count((c) => [c.region]);
    $('#f-area').innerHTML = '<span class="label">Area</span>' + Object.keys(AREAS).filter((k) => ac.get(k)).map((k) => chip('areas', k, AREAS[k], ac.get(k))).join('');
    $('#f-tier').innerHTML = '<span class="label">Tier</span>' + Object.keys(TIERS).filter((k) => tc.get(k)).map((k) => chip('tiers', k, TIERS[k], tc.get(k))).join('');
    $('#f-type').innerHTML = '<span class="label">Type</span>' + Object.keys(TYPES).filter((k) => yc.get(k)).map((k) => chip('types', k, TYPES[k], yc.get(k))).join('');
    const asiaN = state.all.filter((c) => ASIA.has(c.region)).length;
    const regionOpts = [['', 'All regions'], ['asia', `Asia (all) (${asiaN})`]]
      .concat(Object.keys(REGIONS).filter((k) => rc.get(k)).map((k) => [k, `${REGIONS[k]} (${rc.get(k)})`]));
    $('#f-region').innerHTML = regionOpts.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('');
    $('#f-core').innerHTML = [['', 'Any'], ['A*', 'A*'], ['A', 'A'], ['B', 'B'], ['C', 'C'], ['A+', 'A or better'], ['B+', 'B or better'], ['C+', 'C or better'], ['none', 'Unranked / not listed']]
      .map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('');
    $('#f-ccf').innerHTML = [['', 'Any'], ['A', 'A'], ['B', 'B'], ['C', 'C'], ['listed', 'Listed (A/B/C)'], ['none', 'Not listed']]
      .map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('');
    const oc = count((c) => c.organizer_country);
    const asiaOrgN = state.all.filter((c) => c.organizer_country.some((o) => ASIA_ORG.has(o))).length;
    $('#f-org').innerHTML = [['', 'Any'], ['asia', `Asian institutions (${asiaOrgN})`]]
      .concat(Object.keys(ORG).filter((k) => oc.get(k)).map((k) => [k, `${ORG[k]} (${oc.get(k)})`]))
      .map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('');
    const pc = (fn) => state.all.filter((c) => fn(c._proc)).length;
    const pubCount = new Map();
    for (const c of state.all) if (c._proc.has) for (const k of c._proc.keys) pubCount.set(k, (pubCount.get(k) || 0) + 1);
    const pubName = new Map(PUBS.map(([k, name]) => [k, name]));
    pubName.set('korea', 'Korean society proceedings'); pubName.set('other', 'Other outlets');
    const pubOpts = [...pubCount.entries()].sort((a, b) => (a[0] === 'other') - (b[0] === 'other') || b[1] - a[1])
      .flatMap(([k, n]) => {
        const row = [[k, `${pubName.get(k) || k} (${n})`]];
        if (k === 'springer') row.push(['lncs', `Springer LNCS only (${pc((p) => p.lncs)})`]);
        return row;
      });
    $('#f-proc').innerHTML = [['', 'Any'], ['yes', `Published proceedings (${pc((p) => p.has === true)})`],
      ['refereed', `Archival proceedings (${pc((p) => p.has === true && p.refereed)})`],
      ['nonref', `Published, non-archival (${pc((p) => p.has === true && !p.refereed)})`],
      ['no', `No public proceedings (${pc((p) => p.has === false)})`]]
      .map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('') +
      `<optgroup label="Published by">${pubOpts.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</optgroup>`;
    $('#th-core').title = `CORE rank (${state.meta.core_edition || ''})`;
    $('#th-ccf').title = `CCF rank (${state.meta.ccf_edition || ''})`;
  }
  function syncControls() {
    const f = state.f;
    const q = $('#q'); if (document.activeElement !== q && q.value.trim() !== f.q) q.value = f.q;
    $('#f-region').value = f.region; $('#f-proc').value = f.proc; $('#f-org').value = f.org; $('#f-core').value = f.core; $('#f-ccf').value = f.ccf;
    $('#dl-from').value = f.dlFrom; $('#dl-to').value = f.dlTo; $('#cf-from').value = f.cfFrom; $('#cf-to').value = f.cfTo;
    $('#opt-est').checked = f.est; $('#opt-upcoming').checked = f.upcoming;
    document.querySelectorAll('#dl-quick button').forEach((b) => b.setAttribute('aria-pressed', String(Number(b.dataset.days) === f.within)));
    const sortSel = $('#sort-sel'); const sv = `${state.sort.key}${state.sort.dir < 0 ? '-' : ''}`;
    sortSel.value = [...sortSel.options].some((o) => o.value === sv) ? sv : '';
    const active = f.areas.size + f.tiers.size + f.types.size + [f.region, f.org, f.core, f.ccf, f.proc, f.dlFrom || f.dlTo || f.within, f.cfFrom || f.cfTo, f.upcoming, !f.est].filter(Boolean).length;
    $('#filters-toggle').innerHTML = `Filters${active ? ` <span class="n">${active}</span>` : ''}`;
    document.querySelectorAll('.chip').forEach((b) => b.setAttribute('aria-pressed', String(f[b.dataset.group].has(b.dataset.key))));
    document.querySelectorAll('.tabs button').forEach((b) => { if (b.dataset.view === state.view) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
    for (const v of ['table', 'calendar', 'timeline', 'resources', 'contribute']) $(`#view-${v}`).hidden = v !== state.view;
    $('#filters').hidden = state.view === 'resources' || state.view === 'contribute';
  }

  function render() {
    syncControls();
    const list = filtered();
    $('#count').textContent = `Showing ${list.length} of ${state.all.length}`;
    if (state.view === 'table') renderTable(list);
    else if (state.view === 'calendar') renderCalendar(list);
    else if (state.view === 'timeline') renderTimeline(list);
    writeURL();
  }
  let timer = null;
  const renderSoon = () => { clearTimeout(timer); timer = setTimeout(render, 120); };

  function bind() {
    $('#q').addEventListener('input', (e) => { state.f.q = e.target.value.trim(); renderSoon(); });
    for (const [id, key] of [['#f-region', 'region'], ['#f-org', 'org'], ['#f-core', 'core'], ['#f-ccf', 'ccf'], ['#f-proc', 'proc'], ['#dl-from', 'dlFrom'], ['#dl-to', 'dlTo'], ['#cf-from', 'cfFrom'], ['#cf-to', 'cfTo']]) {
      $(id).addEventListener('change', (e) => {
        state.f[key] = e.target.value;
        if (key === 'dlFrom' || key === 'dlTo') state.f.within = 0;
        render();
      });
    }
    $('#sort-sel').addEventListener('change', (e) => {
      const v = e.target.value || 'deadline';
      state.sort = { key: v.replace(/-$/, ''), dir: v.endsWith('-') ? -1 : 1 };
      render();
    });
    $('#opt-est').addEventListener('change', (e) => { state.f.est = e.target.checked; render(); });
    $('#opt-upcoming').addEventListener('change', (e) => { state.f.upcoming = e.target.checked; render(); });
    $('#dl-quick').addEventListener('click', (e) => {
      const b = e.target.closest('button[data-days]'); if (!b) return;
      const days = Number(b.dataset.days);
      state.f.within = state.f.within === days ? 0 : days;
      state.f.dlFrom = ''; state.f.dlTo = '';
      if (state.f.within && state.sort.key !== 'deadline') state.sort = { key: 'deadline', dir: 1 };
      render();
    });
    document.querySelectorAll('.chip-group').forEach((g) => g.addEventListener('click', (e) => {
      const b = e.target.closest('.chip'); if (!b) return;
      const set = state.f[b.dataset.group];
      if (set.has(b.dataset.key)) set.delete(b.dataset.key); else set.add(b.dataset.key);
      render();
    }));
    $('#filters-toggle').addEventListener('click', () => {
      const open = $('#filters').classList.toggle('open');
      $('#filters-toggle').setAttribute('aria-expanded', String(open));
    });
    $('#reset-btn').addEventListener('click', () => { state.f = DEFAULT_FILTERS(); state.sort = { key: 'deadline', dir: 1 }; render(); });
    $('#ics-btn').addEventListener('click', () => icsExport(filtered()));
    window.addEventListener('hashchange', () => { if (location.hash === '#contribute') { state.view = 'contribute'; history.replaceState(null, '', location.pathname + location.search); render(); } });
    document.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => {
      state.view = b.dataset.view; render(); window.scrollTo({ top: 0 });
    }));
    document.querySelectorAll('.conf-table th[data-sort]').forEach((th) => th.addEventListener('click', () => {
      const key = th.dataset.sort;
      state.sort = state.sort.key === key ? { key, dir: -state.sort.dir } : { key, dir: 1 };
      render();
    }));
    $('#rows').addEventListener('click', (e) => {
      if (e.target.closest('a, .detail-row')) return;
      const tr = e.target.closest('tr.row'); if (!tr) return;
      const id = tr.dataset.id;
      if (state.open.has(id)) state.open.delete(id); else state.open.add(id);
      render();
      const btn = document.querySelector(`tr.row[data-id="${CSS.escape(id)}"] .name-btn`);
      if (btn && e.target.closest('.name-btn')) btn.focus();
    });
    // Calendar
    $('#cal-prev').addEventListener('click', () => { moveCal(-1); });
    $('#cal-next').addEventListener('click', () => { moveCal(1); });
    $('#cal-today').addEventListener('click', () => { const d = new Date(state.now); state.cal = { y: d.getFullYear(), m: d.getMonth() }; state.calSelected = null; render(); });
    for (const [id, key] of [['#cal-dl', 'dl'], ['#cal-conf', 'cf'], ['#cal-notif', 'nt']]) {
      $(id).addEventListener('change', (e) => { state.calShow[key] = e.target.checked; render(); });
    }
    $('#cal-grid').addEventListener('click', (e) => {
      const ev = e.target.closest('.ev'); if (ev) { openDialog(ev.dataset.id); return; }
      const day = e.target.closest('.cal-day'); if (!day) return;
      state.calSelected = state.calSelected === day.dataset.date ? null : day.dataset.date;
      // Update the selection in place so keyboard focus stays on the day button.
      document.querySelectorAll('#cal-grid .cal-day').forEach((el) => {
        const on = el.dataset.date === state.calSelected;
        el.classList.toggle('selected', on);
        el.querySelector('.num').setAttribute('aria-pressed', String(on));
      });
      renderAgenda(state.calEvents || new Map());
    });
    $('#cal-agenda').addEventListener('click', (e) => { const ev = e.target.closest('.ev'); if (ev) openDialog(ev.dataset.id); });
    // Timeline
    $('#tl-prev').addEventListener('click', () => moveTl(-3));
    $('#tl-next').addEventListener('click', () => moveTl(3));
    $('#tl-today').addEventListener('click', () => { const d = new Date(state.now); state.tl = { y: d.getFullYear(), m: d.getMonth() }; render(); });
    $('#timeline').addEventListener('click', (e) => { const b = e.target.closest('[data-id]'); if (b) openDialog(b.dataset.id); });
    // Dialog: close only when both press and release happen outside the dialog box (on the backdrop).
    const dlg = $('#detail');
    const outside = (e) => { const r = dlg.getBoundingClientRect(); return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom; };
    let downOutside = false;
    dlg.addEventListener('pointerdown', (e) => { downOutside = e.target === dlg && outside(e); });
    dlg.addEventListener('click', (e) => { if (downOutside && e.target === dlg && outside(e)) dlg.close(); downOutside = false; });
    // Theme
    $('#theme-toggle').addEventListener('click', () => {
      const root = document.documentElement;
      const dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('cr-theme', root.dataset.theme); } catch (e) { /* storage blocked */ }
    });
    // Every minute: refresh countdowns; re-derive "next" dates when the day changes or one of them passes.
    setInterval(() => {
      state.now = Date.now();
      const stale = localISO(state.now) !== state.today || state.all.some((c) =>
        [c._nextSub, c._nextSubEst].some((i) => i && i.t < state.now) || [c._nextConf, c._nextConfEst].some((i) => i && i.tEnd <= state.now));
      if (stale) {
        state.today = localISO(state.now);
        for (const c of state.all) prepare(c);
        render();
        return;
      }
      document.querySelectorAll('.left[data-t]').forEach((el) => { const l = leftText(Number(el.dataset.t)); el.textContent = l.text; el.className = `left ${l.cls}`; });
    }, 60000);
  }
  function moveCal(n) { let { y, m } = state.cal; m += n; y += Math.floor(m / 12); m = ((m % 12) + 12) % 12; state.cal = { y, m }; state.calSelected = null; render(); }
  function moveTl(n) { let { y, m } = state.tl; m += n; y += Math.floor(m / 12); m = ((m % 12) + 12) % 12; state.tl = { y, m }; render(); }

  function staticContent() {
    const meta = state.meta;
    if (meta.title) { $('#site-title').textContent = meta.title; document.title = meta.title; }
    if (meta.subtitle) $('#site-subtitle').textContent = meta.subtitle;
    const r = repo();
    if (r) {
      $('#repo-link').href = gh(''); $('#repo-link').hidden = false;
      $('#add-link').href = gh('/issues/new?template=add-conference.yml');
      $('#add-link').target = '_blank'; $('#add-link').rel = 'noopener';
      $('#c-issue-add').href = gh('/issues/new?template=add-conference.yml');
      $('#c-new-file').href = gh(`/new/${branch()}/data/conferences?filename=new-conference.yml&value=${encodeURIComponent(TEMPLATE_HINT)}`);
      $('#c-guide').href = gh(`/blob/${branch()}/CONTRIBUTING.md`);
      $('#c-clone').textContent = `https://github.com/${r}.git`;
    }
    document.querySelectorAll('.core-ed').forEach((el) => { el.textContent = meta.core_edition || 'ICORE2026'; });
    document.querySelectorAll('.ccf-ed').forEach((el) => { el.textContent = meta.ccf_edition || 'CCF'; });
    $('#res-grid').innerHTML = RESOURCES.map((x) => `<div class="res"><h3><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.name)}</a></h3><p>${esc(x.desc)}</p><span class="tag">${esc(x.tag)}</span></div>`).join('');
    const built = meta.generated_at ? meta.generated_at.slice(0, 10) : '';
    $('#footer-meta').innerHTML = `${state.all.length} venues${built ? ` \u00b7 data built ${esc(built)}` : ''} \u00b7 CORE: ${esc(meta.core_edition || '')}, CCF: ${esc(meta.ccf_edition || '')} \u00b7 ` +
      'Dates marked ~ are estimated from the previous edition. Always confirm on the official site before planning travel.' +
      (r ? ` \u00b7 <a href="${esc(gh(''))}" target="_blank" rel="noopener">Source and data on GitHub</a>` : '');
  }
  const TEMPLATE_HINT = [
    'id: new-conference   # rename the file to <id>.yml and use the same id here',
    'name: ACRONYM', 'full_name: Full Conference Name', 'type: conference   # conference | workshop | industry',
    'tier: minor        # top | major | minor | domestic', 'areas: [security]  # security crypto ai nlp data vision networking communications systems software general',
    'region: japan      # japan korea taiwan china southeast-asia south-asia asia-pacific oceania europe north-america worldwide ...',
    'organizer: ', 'proceedings: ', 'rank:', '  core:   # A*, A, B, C, Unranked', '  ccf:    # A, B, C',
    'links:', '  website: https://', 'notes:', '  - ', 'editions:', '  - year: 2027', '    start: 2027-01-01', '    end: 2027-01-03',
    '    location: City, Country', '    url: https://', '    deadlines:', '      - kind: submission', '        date: 2026-10-01', '        tz: AoE',
    'sources:', '  - https://', 'last_verified: ' + localISO(Date.now()), '',
  ].join('\n');

  // ---------------------------------------------------------------- boot
  async function boot() {
    readURL();
    let data;
    try {
      const res = await fetch('conferences.json', { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      data = await res.json();
    } catch (err) {
      $('#rows').innerHTML = `<tr><td colspan="10" class="empty">Could not load conferences.json (${esc(err.message)}). Run <code>python3 scripts/build.py --serve</code>.</td></tr>`;
      return;
    }
    state.meta = data.meta || {};
    state.all = data.conferences || [];
    for (const c of state.all) { prepare(c); state.byId.set(c.id, c); }
    buildControls();
    staticContent();
    bind();
    const setHeaderH = () => document.documentElement.style.setProperty('--header-h', `${$('.site-header').offsetHeight}px`);
    setHeaderH(); window.addEventListener('resize', setHeaderH);
    render();
  }
  boot();
})();
