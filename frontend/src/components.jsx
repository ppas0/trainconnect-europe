import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Link, useNavigate } from "react-router-dom";
import { TrainSimple, MapPin, MagnifyingGlass, Ticket, SignIn, SignOut, ListBullets, ShoppingCart, Globe, CaretDown, ShareNetwork, WhatsappLogo, EnvelopeSimple, Copy, Check } from "@phosphor-icons/react";
import { trainApi, fmtTime } from "./api";
import { useAuth, useCart } from "./store";
import { useT, LANGS } from "./i18n";

// ============== Lang Switcher ==============
function LangSwitcher() {
  const { lang, setLang } = useT();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const click = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", click);
    return () => document.removeEventListener("mousedown", click);
  }, []);
  const current = LANGS.find((l) => l.code === lang) || LANGS[0];
  return (
    <div className="relative" ref={ref}>
      <button data-testid="lang-switcher-btn" onClick={() => setOpen(!open)} className="btn btn-ghost !py-2 !px-3">
        <Globe size={16} weight="duotone" />
        <span className="hidden sm:inline">{current.flag} {current.code.toUpperCase()}</span>
        <CaretDown size={12} />
      </button>
      {open && (
        <ul className="absolute right-0 top-full mt-1 surface min-w-[160px] z-50">
          {LANGS.map((l) => (
            <li key={l.code}>
              <button
                data-testid={`lang-opt-${l.code}`}
                onClick={() => { setLang(l.code); setOpen(false); }}
                className={"w-full text-left px-4 py-2 hover:bg-[#1a2d5e] flex items-center gap-2 text-sm " + (l.code === lang ? "text-[#E63946]" : "text-white")}
              >
                <span>{l.flag}</span> <span>{l.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ============== Header ==============
export function Header() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const { t } = useT();
  return (
    <header className="glass sticky top-0 z-40">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4 gap-3">
        <Link to="/" className="flex items-center gap-3" data-testid="nav-logo">
          <TrainSimple size={26} weight="duotone" color="#E63946" />
          <div className="font-display text-lg leading-none tracking-tighter">
            TRAINCONNECT<span className="text-[#E63946]">.</span>
          </div>
        </Link>
        <nav className="hidden md:flex items-center gap-6 text-sm font-mono uppercase tracking-widest text-[#9baeca]">
          <Link to="/stations" data-testid="nav-stations" className="hover:text-white">{t("nav.stations")}</Link>
          <Link to="/tickets" data-testid="nav-tickets" className="hover:text-white">{t("nav.tickets")}</Link>
          {user && <Link to="/alerts" data-testid="nav-alerts" className="hover:text-white">{t("nav.alerts")}</Link>}
          {user && <Link to="/affiliate" data-testid="nav-affiliate" className="hover:text-white">Analytics</Link>}
        </nav>
        <div className="flex items-center gap-2">
          <LangSwitcher />
          <Link to="/cart" data-testid="nav-cart" className="relative btn btn-ghost !py-2 !px-3">
            <ShoppingCart size={16} weight="duotone" />
            <span className="hidden sm:inline">{t("nav.cart")}</span>
            {count > 0 && (
              <span className="absolute -top-2 -right-2 bg-[#E63946] text-[#FDFBF7] font-mono text-[10px] px-1.5 py-0.5">
                {count}
              </span>
            )}
          </Link>
          {user ? (
            <button data-testid="nav-logout" onClick={logout} className="btn btn-ghost !py-2 !px-3">
              <SignOut size={16} weight="duotone" />
              <span className="hidden sm:inline">{user.name?.split(" ")[0] || t("nav.logout")}</span>
            </button>
          ) : (
            <Link to="/login" data-testid="nav-login" className="btn !py-2 !px-3">
              <SignIn size={16} weight="duotone" />
              <span className="hidden sm:inline">{t("nav.login")}</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

// ============== Footer ==============
export function Footer() {
  return (
    <footer className="border-t border-white/10 mt-24">
      <div className="max-w-7xl mx-auto px-6 py-10 grid md:grid-cols-3 gap-6 text-sm font-mono uppercase tracking-widest text-[#9baeca]">
        <div>
          <div className="font-display text-xl tracking-tighter text-white">TRAINCONNECT<span className="text-[#E63946]">.</span></div>
          <div className="mt-2 text-xs normal-case tracking-normal font-body">Alle europäischen Zugverbindungen auf einer Plattform.</div>
        </div>
        <div>
          <div className="text-xs">Daten</div>
          <a className="block text-xs normal-case tracking-normal font-body mt-2 hover:text-white" href="https://www.openrailwaymap.org" target="_blank" rel="noopener noreferrer">OpenRailwayMap</a>
          <a className="block text-xs normal-case tracking-normal font-body hover:text-white" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap</a>
          <a className="block text-xs normal-case tracking-normal font-body hover:text-white" href="https://github.com/public-transport/hafas-client" target="_blank" rel="noopener noreferrer">transport.rest / HAFAS</a>
        </div>
        <div>
          <div className="text-xs">Demo-Hinweis</div>
          <div className="text-xs normal-case tracking-normal font-body mt-2">Diese Plattform befindet sich im MVP-Testmodus. Zahlungen über Stripe-Testumgebung. Buchungen sind Demo-Reservierungen.</div>
          <a
            href="/downloads/TrainConnect_Europe_v1.6.zip"
            download
            className="inline-block mt-3 text-xs normal-case tracking-normal font-body text-[#E63946] hover:text-white underline"
            data-testid="footer-download-source-zip"
          >
            ⬇ Quellcode herunterladen (ZIP)
          </a>
        </div>
      </div>
    </footer>
  );
}

// ============== Station Autocomplete ==============
export function StationInput({ label, value, onChange, placeholder, testid }) {
  const [q, setQ] = useState(value?.name || "");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => { setQ(value?.name || ""); }, [value]);

  useEffect(() => {
    if (!q || q.length < 2) { setResults([]); return; }
    const tt = setTimeout(async () => {
      const r = await trainApi.searchStations(q);
      setResults(r);
    }, 220);
    return () => clearTimeout(tt);
  }, [q]);

  useEffect(() => {
    const click = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", click);
    return () => document.removeEventListener("mousedown", click);
  }, []);

  return (
    <div className="field relative" ref={ref}>
      <label className="field-label">{label}</label>
      <input
        data-testid={testid}
        className="field-input"
        value={q}
        placeholder={placeholder}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
      />
      {open && results.length > 0 && (
        <ul className="absolute z-50 top-full left-0 right-0 mt-1 surface max-h-72 overflow-auto scrollbar-thin">
          {results.map((s) => (
            <li
              key={s.id}
              data-testid={`${testid}-option-${s.id}`}
              className="px-3 py-2 cursor-pointer hover:bg-[#1a2d5e] flex items-center justify-between gap-3"
              onClick={() => { onChange(s); setQ(s.name); setOpen(false); }}
            >
              <div>
                <div className="font-body text-sm text-white">{s.name}</div>
                <div className="eyebrow">{s.city} · {s.country}</div>
              </div>
              <MapPin size={14} color="#9baeca" />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ============== Search Widget ==============
export function SearchWidget({ initial }) {
  const navigate = useNavigate();
  const { t } = useT();
  const [from, setFrom] = useState(initial?.from || null);
  const [to, setTo] = useState(initial?.to || null);
  const [date, setDate] = useState(initial?.date || new Date().toISOString().slice(0, 10));
  const [time, setTime] = useState(initial?.time || "08:00");
  const [passengers, setPassengers] = useState(initial?.passengers || 1);

  const submit = (e) => {
    e?.preventDefault();
    if (!from || !to) return;
    const dep = new Date(`${date}T${time}:00`).toISOString();
    const qs = new URLSearchParams({ from_id: from.id, to_id: to.id, from_name: from.name, to_name: to.name, departure: dep, passengers });
    navigate(`/search?${qs.toString()}`);
  };

  return (
    <form onSubmit={submit} className="tracing-beam p-6 md:p-8 fade-up" data-testid="search-widget">
      <div className="grid md:grid-cols-12 gap-6">
        <div className="md:col-span-4"><StationInput testid="from-input" label={t("form.from")} value={from} onChange={setFrom} placeholder={t("form.from_ph")} /></div>
        <div className="md:col-span-4"><StationInput testid="to-input" label={t("form.to")} value={to} onChange={setTo} placeholder={t("form.to_ph")} /></div>
        <div className="md:col-span-2">
          <label className="field-label">{t("form.date")}</label>
          <input data-testid="date-input" className="field-input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="md:col-span-1">
          <label className="field-label">{t("form.time")}</label>
          <input data-testid="time-input" className="field-input" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
        <div className="md:col-span-1">
          <label className="field-label">{t("form.pax")}</label>
          <input data-testid="pax-input" className="field-input" type="number" min={1} max={9} value={passengers} onChange={(e) => setPassengers(parseInt(e.target.value || "1"))} />
        </div>
      </div>
      <div className="mt-6 flex items-center justify-between flex-wrap gap-3">
        <div className="demo-badge">{t("form.demo_badge")}</div>
        <button data-testid="search-trains-btn" className="btn btn-primary" type="submit">
          <MagnifyingGlass size={16} weight="bold" /> {t("form.submit")}
        </button>
      </div>
    </form>
  );
}

// ============== Route Map ==============
const trainIcon = L.divIcon({ className: "", html: '<div class="train-marker"></div>', iconSize: [18, 18], iconAnchor: [9, 9] });
const stationIcon = L.divIcon({ className: "", html: '<div class="station-marker"></div>', iconSize: [10, 10], iconAnchor: [5, 5] });

export function RouteMap({ journey, livePositions, height = "100%" }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  const layersRef = useRef({ poly: null, stations: [], trains: [] });

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = L.map(ref.current, { zoomControl: true, attributionControl: true }).setView([50, 10], 4);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '© OpenStreetMap, © CartoDB',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);
    L.tileLayer("https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png", {
      attribution: '© <a href="https://www.openrailwaymap.org">OpenRailwayMap</a>',
      maxZoom: 19,
      opacity: 0.65,
    }).addTo(map);
    mapRef.current = map;
  }, []);

  // draw polyline + station markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !journey) return;
    if (layersRef.current.poly) map.removeLayer(layersRef.current.poly);
    layersRef.current.stations.forEach((m) => map.removeLayer(m));
    layersRef.current.stations = [];

    const all = [];
    journey.legs.forEach((leg) => { leg.polyline.forEach((p) => all.push(p)); });
    const poly = L.polyline(all, { color: "#E63946", weight: 3, opacity: 0.9 }).addTo(map);
    layersRef.current.poly = poly;

    const stations = [journey.legs[0].from, ...journey.legs.map((l) => l.to)];
    stations.forEach((s) => {
      const m = L.marker([s.lat, s.lon], { icon: stationIcon })
        .addTo(map)
        .bindPopup(`<div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#0c152b"><b>${s.name}</b><br/>${s.city} · ${s.country}</div>`);
      layersRef.current.stations.push(m);
    });
    map.fitBounds(poly.getBounds(), { padding: [40, 40] });
  }, [journey]);

  // live train markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    layersRef.current.trains.forEach((m) => map.removeLayer(m));
    layersRef.current.trains = [];
    if (!livePositions || livePositions.length === 0) return;
    livePositions.forEach((leg) => {
      if (leg.status === "scheduled" || leg.status === "arrived") return;
      const [lat, lon] = leg.current_position;
      const m = L.marker([lat, lon], { icon: trainIcon })
        .addTo(map)
        .bindPopup(`<div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#0c152b"><b>${leg.train_no}</b><br/>${Math.round(leg.progress * 100)}% Fortschritt${leg.delay_min ? `<br/>+${leg.delay_min} min` : ""}</div>`);
      layersRef.current.trains.push(m);
    });
  }, [livePositions]);

  return <div ref={ref} className="w-full" style={{ height, background: "#050914" }} data-testid="route-map" />;
}

// ============== Stations Overview Map ==============
export function StationsMap({ stations, onSelect }) {
  const ref = useRef(null);
  const mapRef = useRef(null);
  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = L.map(ref.current).setView([52, 13], 4);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { subdomains: "abcd", attribution: "© OSM/CartoDB" }).addTo(map);
    L.tileLayer("https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png", { attribution: "© OpenRailwayMap", opacity: 0.65 }).addTo(map);
    mapRef.current = map;
  }, []);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !stations) return;
    stations.forEach((s) => {
      L.marker([s.lat, s.lon], { icon: stationIcon })
        .addTo(map)
        .bindPopup(`<b>${s.name}</b><br/>${s.city}, ${s.country}`)
        .on("click", () => onSelect?.(s));
    });
  }, [stations, onSelect]);
  return <div ref={ref} className="w-full h-full" data-testid="stations-map" />;
}

// ============== Journey Card ==============
export function JourneyCard({ j, onBook, onView }) {
  const { t } = useT();
  const dep = fmtTime(j.departure);
  const arr = fmtTime(j.arrival);
  const hasDelay = j.legs.some((l) => l.delay_min > 0);
  return (
    <article className="surface p-5 md:p-6 hover:border-[#E63946] transition-colors group fade-up" data-testid={`journey-card-${j.id}`}>
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex-1 min-w-[260px]">
          <div className="eyebrow flex items-center gap-3">
            <span>{j.legs[0].operator}</span>
            <span>·</span>
            <span>{j.changes} {t("search.changes")}</span>
            {hasDelay && <span className="delay-badge">+{Math.max(...j.legs.map((l) => l.delay_min))} min</span>}
            {!hasDelay && <span className="delay-ok">{t("search.on_time")}</span>}
          </div>
          <div className="mt-3 flex items-end gap-4 flex-wrap">
            <div>
              <div className="font-mono text-3xl text-white">{dep}</div>
              <div className="text-sm text-[#9baeca]">{j.from.city}</div>
            </div>
            <div className="flex-1 min-w-[80px] h-px bg-[#1a2d5e] relative">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-mono text-[#9baeca]">{Math.floor(j.duration_min/60)}h {j.duration_min%60}m</div>
            </div>
            <div>
              <div className="font-mono text-3xl text-white">{arr}</div>
              <div className="text-sm text-[#9baeca]">{j.to.city}</div>
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="eyebrow">{t("search.from_price")}</div>
          <div className="font-display text-4xl text-[#FDFBF7]">€{j.total_price.toFixed(0)}</div>
          <div className="eyebrow">{j.passengers} {t("common.persons")}</div>
        </div>
      </div>
      <div className="mt-5 flex gap-3 flex-wrap">
        <button data-testid={`view-journey-${j.id}`} onClick={() => onView(j)} className="btn btn-ghost flex-1 sm:flex-none">{t("search.view")}</button>
        <button data-testid={`book-journey-${j.id}`} onClick={() => onBook(j)} className="btn btn-primary flex-1 sm:flex-none">
          <Ticket size={16} weight="bold" /> {t("search.add_cart")}
        </button>
      </div>
    </article>
  );
}

// ============== Delay/Status pill ==============
export function DelayPill({ minutes }) {
  const { t } = useT();
  if (minutes && minutes > 0) return <span className="delay-badge">+{minutes} min</span>;
  return <span className="delay-ok">{t("search.on_time")}</span>;
}


// ============== Share Bar (Journey Detail) ==============
export function ShareBar({ journey }) {
  const { t } = useT();
  const [copied, setCopied] = useState(false);
  const url = typeof window !== "undefined" ? window.location.href : "";
  const title = `${journey.from.city} → ${journey.to.city}`;
  const text = `${t("jd.share.message")}: ${title} · TrainConnect Europe`;
  const canNative = typeof navigator !== "undefined" && !!navigator.share;

  const onNative = async () => {
    try { await navigator.share({ title, text, url }); } catch (_) { /* user cancelled */ }
  };
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (_) {
      // Fallback for older browsers / non-secure contexts
      const ta = document.createElement("textarea");
      ta.value = url; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); setCopied(true); setTimeout(() => setCopied(false), 1800); }
      finally { document.body.removeChild(ta); }
    }
  };
  const waHref = `https://wa.me/?text=${encodeURIComponent(text + " " + url)}`;
  const mailHref = `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(text + "\n\n" + url)}`;

  return (
    <div className="surface p-5" data-testid="share-bar">
      <div className="eyebrow flex items-center gap-2">
        <ShareNetwork size={12} weight="duotone" /> {t("jd.share")}
      </div>
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
        {canNative && (
          <button onClick={onNative} className="btn btn-ghost !py-2 text-xs" data-testid="share-native-btn">
            <ShareNetwork size={14} weight="bold" /> {t("jd.share.native")}
          </button>
        )}
        <a href={waHref} target="_blank" rel="noopener noreferrer" className="btn btn-ghost !py-2 text-xs" data-testid="share-whatsapp-btn">
          <WhatsappLogo size={14} weight="bold" /> {t("jd.share.whatsapp")}
        </a>
        <a href={mailHref} className="btn btn-ghost !py-2 text-xs" data-testid="share-email-btn">
          <EnvelopeSimple size={14} weight="bold" /> {t("jd.share.email")}
        </a>
        <button onClick={onCopy} className="btn btn-ghost !py-2 text-xs" data-testid="share-copy-btn">
          {copied ? <Check size={14} weight="bold" /> : <Copy size={14} weight="bold" />}
          {copied ? t("jd.share.copied") : t("jd.share.copy")}
        </button>
      </div>
    </div>
  );
}
