import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Train, ArrowRight, Clock, Lightning, MapPin, Ticket, FilePdf, Warning, Lock, Globe, ArrowSquareOut, AppleLogo, CalendarPlus, Funnel } from "@phosphor-icons/react";
import { trainApi, cartApi, ticketsApi, affiliateApi, fmtTime, fmtDate, fmtDur, fmtPrice } from "./api";
import { useAuth, useCart } from "./store";
import { useT } from "./i18n";
import { SearchWidget, RouteMap, JourneyCard, StationsMap, DelayPill } from "./components";

// ============== HOME / Landing ==============
export function Home() {
  const { t } = useT();
  const { data: popular } = useQuery({ queryKey: ["popular"], queryFn: trainApi.popular });
  return (
    <div className="relative">
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 opacity-30"
             style={{ backgroundImage: 'url(https://static.prod-images.emergentagent.com/jobs/fb96d4ae-a35e-4a10-b099-625bc93fdb67/images/76b56b578b309505fcfa292b0a4fb71b34dbdc471e9cbac21b26dc2f497d781c.png)', backgroundSize: "cover", backgroundPosition: "center" }} />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-[#050914]/80 via-[#050914]/95 to-[#050914]" />
        <div className="max-w-7xl mx-auto px-6 pt-20 pb-16 md:pt-32 md:pb-28">
          <div className="eyebrow flex items-center gap-3 text-[#E63946]">
            <Lightning size={14} weight="fill" /> {t("home.eyebrow")}
          </div>
          <h1 className="font-display text-5xl sm:text-7xl lg:text-8xl uppercase mt-6 leading-[0.85]" data-testid="home-hero-title">
            {t("home.title1")}<br/>
            <span className="text-[#FDFBF7]">{t("home.title2")}</span>
          </h1>
          <p className="mt-6 max-w-xl text-[#9baeca] text-lg font-body">{t("home.lead")}</p>
          <div className="mt-12 max-w-5xl">
            <SearchWidget />
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="eyebrow">{t("home.popular.eyebrow")}</div>
            <h2 className="font-display text-3xl uppercase">{t("home.popular.title")}</h2>
          </div>
          <Link to="/stations" className="btn btn-ghost">{t("home.all_stations")}</Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {(popular || []).map((p, i) => (
            <Link key={i} to={`/search?from_id=${p.from_id}&to_id=${p.to_id}&passengers=1`}
                  className="surface p-5 hover:border-[#E63946] block" data-testid={`popular-${p.from_id}-${p.to_id}`}>
              <div className="eyebrow flex items-center gap-2"><Train size={12} weight="duotone" /> {p.from.country} → {p.to.country}</div>
              <div className="font-display text-2xl uppercase mt-3 leading-tight">{p.from.city}<br/>→ {p.to.city}</div>
              <div className="mt-4 flex justify-between items-end">
                <div className="eyebrow">{t("search.from_price")}</div>
                <div className="font-mono text-xl text-[#FDFBF7]">€{p.price.toFixed(0)}</div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 pb-24 grid md:grid-cols-3 gap-6">
        {[
          { icon: <Globe size={28} weight="duotone" />, t: t("home.feat1.t"), d: t("home.feat1.d") },
          { icon: <MapPin size={28} weight="duotone" />, t: t("home.feat2.t"), d: t("home.feat2.d") },
          { icon: <Ticket size={28} weight="duotone" />, t: t("home.feat3.t"), d: t("home.feat3.d") },
        ].map((b, i) => (
          <div key={i} className="surface p-7" data-testid={`feature-${i}`}>
            <div className="text-[#E63946]">{b.icon}</div>
            <div className="font-display text-2xl uppercase mt-4">{b.t}</div>
            <div className="mt-2 text-[#9baeca] font-body text-sm">{b.d}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

// ============== Search Results ==============
export function Search() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { add } = useCart();
  const { t } = useT();
  const from_id = params.get("from_id");
  const to_id = params.get("to_id");
  const passengers = parseInt(params.get("passengers") || "1");
  const departure = useMemo(() => params.get("departure") || new Date(Math.floor(Date.now() / 60000) * 60000).toISOString(), [params]);
  const [selectedJ, setSelectedJ] = useState(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["journeys", from_id, to_id, departure, passengers],
    queryFn: () => trainApi.searchJourneys({ from_id, to_id, departure, passengers }),
    enabled: !!from_id && !!to_id,
  });

  const from_name = data?.results?.[0]?.from?.name || params.get("from_name") || from_id;
  const to_name = data?.results?.[0]?.to?.name || params.get("to_name") || to_id;

  useEffect(() => {
    if (data?.results?.length && !selectedJ) setSelectedJ(data.results[0]);
  }, [data, selectedJ]);

  const onBook = (j) => {
    add(j.id, j.passengers, { from: j.from.name, to: j.to.name, departure: j.departure, price: j.total_price });
    navigate("/cart");
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <div className="eyebrow flex gap-3 items-center"><ArrowRight size={12} /> {from_name} → {to_name}</div>
      <h1 className="font-display text-4xl uppercase mt-2">{from_name} <span className="text-[#E63946]">→</span> {to_name}</h1>
      <div className="mt-2 eyebrow">{fmtDate(departure)} · {passengers} {t("common.persons")} · {data?.data_source === "live" ? t("search.live") : t("search.curated")}</div>

      <div className="mt-8 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-4">
          {isLoading && <div className="surface p-8 text-center text-[#9baeca]">{t("search.loading")}</div>}
          {error && <div className="surface p-8 text-center text-[#E63946]"><Warning size={20} /> {t("search.error")}</div>}
          {data?.results?.map((j) => (
            <JourneyCard key={j.id} j={j} onBook={onBook} onView={(jj) => { setSelectedJ(jj); navigate(`/journey/${jj.id}`); }} />
          ))}
        </div>
        <div className="lg:col-span-2 surface min-h-[500px] overflow-hidden" style={{ height: "calc(100vh - 200px)" }}>
          {selectedJ ? <RouteMap journey={selectedJ} /> : <div className="h-full flex items-center justify-center text-[#9baeca]">{t("search.choose")}</div>}
        </div>
      </div>
    </div>
  );
}

// ============== Journey Detail (timeline + live map + provider deep links) ==============
export function JourneyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { add } = useCart();
  const { t } = useT();
  const { data: j } = useQuery({ queryKey: ["journey", id], queryFn: () => trainApi.journey(id) });
  const { data: live } = useQuery({ queryKey: ["live", id], queryFn: () => trainApi.journeyLive(id), refetchInterval: 30000, enabled: !!j });

  if (!j) return <div className="max-w-7xl mx-auto px-6 py-20 text-center text-[#9baeca]">{t("jd.loading")}</div>;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="eyebrow">{t("jd.heading")}</div>
      <h1 className="font-display text-4xl uppercase">{j.from.city} <span className="text-[#E63946]">→</span> {j.to.city}</h1>
      <div className="eyebrow mt-2">{fmtDate(j.departure)} · {t("jd.duration")}: {fmtDur(j.duration_min)} · {j.changes} {t("search.changes")}</div>

      <div className="grid lg:grid-cols-5 gap-6 mt-8">
        <div className="lg:col-span-2 space-y-1">
          {j.legs.map((leg, idx) => {
            const liveLeg = live?.legs?.[idx];
            return (
              <div key={leg.leg_id} className="surface p-5" data-testid={`leg-${idx}`}>
                <div className="eyebrow flex justify-between">
                  <span>{t("jd.leg")} {idx + 1}</span>
                  <span>{leg.operator} · {leg.train_no}</span>
                </div>
                <div className="mt-3 flex justify-between items-start gap-4">
                  <div>
                    <div className="font-mono text-2xl">{fmtTime(leg.departure)}</div>
                    <div className="text-sm">{leg.from.name}</div>
                    <div className="eyebrow mt-1">{t("jd.platform")} {leg.platform}</div>
                  </div>
                  <div className="text-center">
                    <div className="eyebrow">{fmtDur(leg.duration_min)}</div>
                    <div className="w-20 h-px bg-[#1a2d5e] mt-2 mb-2"></div>
                    <DelayPill minutes={leg.delay_min} />
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-2xl">{fmtTime(leg.arrival)}</div>
                    <div className="text-sm">{leg.to.name}</div>
                  </div>
                </div>
                {liveLeg && liveLeg.status === "in_transit" && (
                  <div className="mt-3">
                    <div className="eyebrow text-[#E63946]">● {t("search.live")} · {Math.round(liveLeg.progress * 100)}% {t("jd.live_progress")}</div>
                    <div className="h-1 bg-[#0c152b] mt-1 relative">
                      <div className="absolute top-0 left-0 h-1 bg-[#E63946]" style={{ width: `${liveLeg.progress * 100}%` }} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          <div className="surface p-5 flex items-center justify-between">
            <div>
              <div className="eyebrow">{t("jd.total")}</div>
              <div className="font-display text-3xl">{fmtPrice(j.total_price)}</div>
            </div>
            <button data-testid="add-to-cart-btn" className="btn btn-primary" onClick={() => { add(j.id, j.passengers, { from: j.from.name, to: j.to.name, departure: j.departure, price: j.total_price }); navigate("/cart"); }}>
              <Ticket size={16} weight="bold" /> {t("search.add_cart")}
            </button>
          </div>

          {j.provider_links?.length > 0 && (
            <div className="surface p-5" data-testid="provider-links">
              <div className="eyebrow flex items-center gap-2"><Globe size={12} /> {t("jd.providers")}</div>
              <div className="text-xs text-[#9baeca] mt-2 font-body">{t("jd.providers_note")}</div>
              <div className="mt-3 grid gap-2">
                {j.provider_links.map((p, i) => (
                  <ProviderLink key={i} p={p} idx={i} journeyId={j.id} />
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="lg:col-span-3 surface overflow-hidden" style={{ height: "calc(100vh - 200px)" }}>
          <RouteMap journey={j} livePositions={live?.legs} />
        </div>
      </div>
    </div>
  );
}

// ============== Stations Overview ==============
export function Stations() {
  const { t } = useT();
  const { data: stations } = useQuery({ queryKey: ["stations"], queryFn: trainApi.allStations });
  const [selected, setSelected] = useState(null);
  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="eyebrow">{t("st.network")}</div>
      <h1 className="font-display text-4xl uppercase">{t("st.title")}</h1>
      <div className="mt-6 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 surface max-h-[70vh] overflow-auto scrollbar-thin">
          {(stations || []).map((s) => (
            <button
              key={s.id}
              onClick={() => setSelected(s)}
              data-testid={`station-row-${s.id}`}
              className={"w-full text-left px-4 py-3 border-b border-[#1a2d5e] hover:bg-[#1a2d5e] " + (selected?.id === s.id ? "bg-[#1a2d5e]" : "")}
            >
              <div className="text-sm">{s.name}</div>
              <div className="eyebrow">{s.city} · {s.country}</div>
            </button>
          ))}
        </div>
        <div className="lg:col-span-3 surface overflow-hidden" style={{ height: "70vh" }}>
          <StationsMap stations={stations || []} onSelect={setSelected} />
        </div>
      </div>
      {selected && <StationPanel station={selected} />}
    </div>
  );
}

function StationPanel({ station }) {
  const { t } = useT();
  const { data } = useQuery({ queryKey: ["dep", station.id], queryFn: () => trainApi.stationDepartures(station.id), refetchInterval: 60000 });
  return (
    <div className="mt-8 surface p-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="eyebrow">{t("st.departures")}</div>
          <h3 className="font-display text-2xl uppercase">{station.name}</h3>
        </div>
        <span className="eyebrow">{data?.data_source === "live" ? `● ${t("search.live")}` : t("search.curated")}</span>
      </div>
      <div className="mt-4 grid gap-2">
        {(data?.departures || []).map((d, i) => (
          <div key={i} className="flex items-center gap-4 py-2 border-b border-[#1a2d5e]">
            <div className="font-mono text-xl w-16">{fmtTime(d.when)}</div>
            <div className="font-mono text-xs text-[#9baeca] w-24">{d.line}</div>
            <div className="flex-1 text-sm">→ {d.direction}</div>
            <div className="eyebrow w-16 text-right">{t("st.platform_short")} {d.platform || "—"}</div>
            <DelayPill minutes={d.delay_min} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ============== Cart ==============
export function Cart() {
  const { items, remove, setPassengers, clear } = useCart();
  const { user } = useAuth();
  const { t } = useT();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const total = useMemo(() => items.reduce((s, i) => s + (i.price || 0), 0), [items]);

  const onCheckout = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const cart = await cartApi.create(items.map((i) => ({ journey_id: i.journey_id, passengers: i.passengers })));
      const session = await cartApi.checkout(cart.id);
      window.location.href = session.url;
    } catch (e) {
      setError(e?.response?.data?.detail || t("search.error"));
      setSubmitting(false);
    }
  };

  if (!items.length)
    return (
      <div className="max-w-3xl mx-auto px-6 py-20 text-center">
        <Ticket size={48} weight="duotone" className="mx-auto text-[#9baeca]" />
        <h1 className="font-display text-4xl uppercase mt-6">{t("cart.empty.title")}</h1>
        <p className="text-[#9baeca] mt-2">{t("cart.empty.lead")}</p>
        <Link to="/" className="btn btn-primary mt-6">{t("cart.empty.cta")}</Link>
      </div>
    );

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="eyebrow">{t("cart.checkout_label")}</div>
      <h1 className="font-display text-4xl uppercase">{t("cart.title")}</h1>
      <div className="mt-2 demo-badge">{t("cart.demo_badge")}</div>

      <div className="mt-8 grid gap-4">
        {items.map((it) => (
          <div key={it.journey_id} className="surface p-5 flex justify-between gap-4 items-center flex-wrap" data-testid={`cart-row-${it.journey_id}`}>
            <div className="flex-1 min-w-[200px]">
              <div className="font-display text-xl uppercase leading-tight">{it.from} → {it.to}</div>
              <div className="eyebrow mt-1">{fmtDate(it.departure)} · {fmtTime(it.departure)}</div>
            </div>
            <div className="flex items-center gap-2">
              <label className="field-label">{t("form.pax")}</label>
              <input data-testid={`cart-pax-${it.journey_id}`} type="number" min={1} max={9} value={it.passengers}
                     onChange={(e) => setPassengers(it.journey_id, parseInt(e.target.value || "1"))}
                     className="field-input w-16 text-center" />
            </div>
            <div className="font-mono text-xl w-24 text-right">{fmtPrice(it.price)}</div>
            <button data-testid={`cart-remove-${it.journey_id}`} onClick={() => remove(it.journey_id)} className="btn btn-ghost">{t("cart.remove")}</button>
          </div>
        ))}
      </div>

      <div className="mt-8 surface p-6 flex justify-between items-center flex-wrap gap-4">
        <div>
          <div className="eyebrow">{t("cart.total")}</div>
          <div className="font-display text-4xl">{fmtPrice(total)}</div>
        </div>
        <div className="flex gap-3 flex-wrap">
          <button onClick={clear} className="btn btn-ghost">{t("cart.clear")}</button>
          <button data-testid="checkout-btn" disabled={submitting} onClick={onCheckout} className="btn btn-primary">
            <Lock size={16} weight="bold" /> {submitting ? t("cart.paying") : t("cart.pay")}
          </button>
        </div>
      </div>
      {error && <div className="mt-4 surface p-4 text-[#E63946]">{error}</div>}
      {!user && <div className="mt-4 text-sm text-[#9baeca]">{t("cart.login_hint").replace("Logge dich ein", "")} <Link to="/login" className="underline">{t("nav.login")}</Link></div>}
    </div>
  );
}

// ============== Checkout Success ==============
export function CheckoutSuccess() {
  const [params] = useSearchParams();
  const session_id = params.get("session_id");
  const { clear } = useCart();
  const { t } = useT();
  const [status, setStatus] = useState("pending");
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!session_id || status === "paid") return;
    if (attempts > 8) { setStatus("timeout"); return; }
    const tt = setTimeout(async () => {
      try {
        const r = await cartApi.status(session_id);
        if (r.payment_status === "paid") { setStatus("paid"); clear(); }
        else if (r.status === "expired") setStatus("expired");
        else setAttempts((a) => a + 1);
      } catch { setAttempts((a) => a + 1); }
    }, 2000);
    return () => clearTimeout(tt);
  }, [session_id, attempts, status, clear]);

  return (
    <div className="max-w-2xl mx-auto px-6 py-20 text-center">
      {status === "paid" && (
        <>
          <Ticket size={56} weight="duotone" className="mx-auto text-[#E63946]" />
          <h1 className="font-display text-5xl uppercase mt-6" data-testid="checkout-success-title">{t("cs.paid.title")}</h1>
          <p className="text-[#9baeca] mt-3 font-body">{t("cs.paid.lead")}</p>
          <Link to="/tickets" className="btn btn-primary mt-8">{t("cs.paid.cta")}</Link>
        </>
      )}
      {status === "pending" && (
        <>
          <Clock size={56} weight="duotone" className="mx-auto text-[#9baeca]" />
          <h1 className="font-display text-3xl uppercase mt-6">{t("cs.pending")}</h1>
          <p className="text-[#9baeca] mt-2 font-body">{t("cs.attempt")} {attempts + 1} / 9</p>
        </>
      )}
      {(status === "expired" || status === "timeout") && (
        <>
          <Warning size={56} weight="duotone" className="mx-auto text-[#E63946]" />
          <h1 className="font-display text-3xl uppercase mt-6">{t("cs.failed")}</h1>
          <Link to="/cart" className="btn mt-6">{t("cs.back")}</Link>
        </>
      )}
    </div>
  );
}

// ============== Tickets ==============
export function Tickets() {
  const { user } = useAuth();
  const { t } = useT();
  const { data } = useQuery({ queryKey: ["tickets"], queryFn: ticketsApi.list, enabled: !!user });
  if (!user)
    return (
      <div className="max-w-xl mx-auto px-6 py-20 text-center">
        <Lock size={48} className="mx-auto text-[#9baeca]" />
        <h1 className="font-display text-3xl uppercase mt-4">{t("tk.login_required")}</h1>
        <Link to="/login" className="btn btn-primary mt-6">{t("nav.login")}</Link>
      </div>
    );
  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="eyebrow">{t("tk.account")}</div>
      <h1 className="font-display text-4xl uppercase">{t("tk.title")}</h1>
      <div className="mt-8 grid gap-4">
        {(data || []).length === 0 && <div className="surface p-8 text-center text-[#9baeca]">{t("tk.none")}</div>}
        {(data || []).map((tk) => {
          const tok = (localStorage.getItem("tc_token") || "");
          return (
          <div key={tk.id} className="surface p-5 flex justify-between items-center gap-4 flex-wrap" data-testid={`ticket-${tk.id}`}>
            <div className="flex-1 min-w-[200px]">
              <div className="eyebrow">{tk.pnr} · {tk.status}</div>
              <div className="font-display text-xl uppercase mt-1">{tk.from} → {tk.to}</div>
              <div className="eyebrow mt-1">{fmtDate(tk.departure)} · {fmtTime(tk.departure)} · {tk.passengers} {t("common.persons")}</div>
            </div>
            <div className="font-mono text-xl">{fmtPrice(tk.price)}</div>
            <div className="flex gap-2 flex-wrap">
              <a data-testid={`ticket-pdf-${tk.id}`} href={ticketsApi.pdfUrl(tk.id) + "?token=" + tok} className="btn btn-ghost !py-2 !px-3" target="_blank" rel="noopener noreferrer">
                <FilePdf size={14} weight="bold" /> PDF
              </a>
              <a data-testid={`ticket-ics-${tk.id}`} href={ticketsApi.icsUrl(tk.id) + "?token=" + tok} className="btn btn-ghost !py-2 !px-3" target="_blank" rel="noopener noreferrer" title="In Kalender (iOS/Google/Outlook)">
                <CalendarPlus size={14} weight="bold" /> .ics
              </a>
              <a data-testid={`ticket-pkpass-${tk.id}`} href={ticketsApi.pkpassUrl(tk.id) + "?token=" + tok} className="btn btn-ghost !py-2 !px-3" target="_blank" rel="noopener noreferrer" title="Apple Wallet (unsigned demo)">
                <AppleLogo size={14} weight="bold" /> Wallet
              </a>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}

// ============== ProviderLink (tracked affiliate click) ==============
function ProviderLink({ p, idx, journeyId }) {
  const [loading, setLoading] = useState(false);
  const onClick = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await affiliateApi.trackClick({
        provider: p.name,
        country: p.country,
        journey_id: journeyId,
        leg: p.leg,
        url: p.url,
      });
      window.open(r.redirect_url, "_blank", "noopener,noreferrer");
    } catch {
      window.open(p.url, "_blank", "noopener,noreferrer");
    } finally {
      setLoading(false);
    }
  };
  return (
    <a
      href={p.url}
      onClick={onClick}
      data-testid={`provider-link-${idx}`}
      className="flex items-center justify-between gap-3 border border-[#1a2d5e] hover:border-[#E63946] px-3 py-2 transition-colors cursor-pointer"
    >
      <div className="flex-1 min-w-0">
        <div className="font-mono text-sm uppercase tracking-wider">{p.name}</div>
        <div className="eyebrow truncate">{p.leg}</div>
      </div>
      <ArrowSquareOut size={16} color={loading ? "#E63946" : "#9baeca"} />
    </a>
  );
}

// ============== Affiliate Dashboard ==============
function FunnelStep({ label, value }) {
  return (
    <div className="border border-[#1a2d5e] p-3">
      <div className="eyebrow">{label}</div>
      <div className="font-display text-3xl mt-1">{value}</div>
    </div>
  );
}

export function AffiliateDashboard() {
  const { user } = useAuth();
  const { t } = useT();
  const { data, isLoading } = useQuery({
    queryKey: ["affiliate-stats"],
    queryFn: affiliateApi.stats,
    enabled: !!user,
    refetchInterval: 30000,
  });

  if (!user)
    return (
      <div className="max-w-xl mx-auto px-6 py-20 text-center">
        <Lock size={48} className="mx-auto text-[#9baeca]" />
        <h1 className="font-display text-3xl uppercase mt-4">{t("tk.login_required")}</h1>
        <Link to="/login" className="btn btn-primary mt-6">{t("nav.login")}</Link>
      </div>
    );

  if (isLoading || !data)
    return <div className="max-w-7xl mx-auto px-6 py-20 text-center text-[#9baeca]">Loading...</div>;

  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <div className="eyebrow">Analytics</div>
      <h1 className="font-display text-4xl uppercase">Affiliate Dashboard</h1>
      <div className="mt-1 text-sm text-[#9baeca] font-body">
        Klicks auf Partner-Anbieter (DB, SNCF, ÖBB, …) – das sind deine Verhandlungsdaten für echte Affiliate-Deals.
      </div>

      <div className="mt-8 grid sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="surface p-5" data-testid="stat-total">
          <div className="eyebrow">Gesamt-Klicks</div>
          <div className="font-display text-4xl mt-2">{data.total_clicks}</div>
        </div>
        <div className="surface p-5" data-testid="stat-7d">
          <div className="eyebrow">Letzte 7 Tage</div>
          <div className="font-display text-4xl mt-2">{data.last_7d}</div>
        </div>
        <div className="surface p-5" data-testid="stat-providers">
          <div className="eyebrow">Aktive Anbieter</div>
          <div className="font-display text-4xl mt-2">{data.by_provider.length}</div>
        </div>
        <div className="surface p-5" data-testid="stat-countries">
          <div className="eyebrow">Länder</div>
          <div className="font-display text-4xl mt-2">{data.by_country.length}</div>
        </div>
      </div>

      {data.funnel && (
        <div className="mt-10 surface p-6" data-testid="funnel">
          <h2 className="font-display text-2xl uppercase flex items-center gap-2"><Funnel size={22} weight="duotone" /> Conversion-Funnel</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <FunnelStep label="Suchen" value={data.funnel.searches} />
            <FunnelStep label="Warenkorb-Adds" value={data.funnel.cart_adds} />
            <FunnelStep label="Anbieter-Klicks" value={data.funnel.outbound_clicks} />
            <FunnelStep label="Bezahlte Checkouts" value={data.funnel.paid_checkouts} />
          </div>
          <div className="mt-5 flex flex-wrap gap-6 text-sm">
            <div>
              <div className="eyebrow">Search → Click Rate</div>
              <div className="font-mono text-2xl text-[#E63946]">{data.funnel.search_to_click_rate}%</div>
            </div>
            <div>
              <div className="eyebrow">Click → Paid Rate</div>
              <div className="font-mono text-2xl text-[#E63946]">{data.funnel.click_to_paid_rate}%</div>
            </div>
          </div>
          {data.missed_routes?.length > 0 && (
            <div className="mt-6">
              <div className="eyebrow text-[#E63946]">⚠ Verpasste Chancen (oft gesucht, nie geklickt)</div>
              <div className="mt-2 grid gap-1">
                {data.missed_routes.map((m, i) => (
                  <div key={i} className="flex justify-between text-sm border-b border-[#1a2d5e] py-1">
                    <span className="truncate">{m.route}</span>
                    <span className="font-mono text-[#9baeca]">{m.searches}x gesucht</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-10 grid md:grid-cols-3 gap-6">
        <div className="surface p-5">
          <h3 className="font-display text-xl uppercase">Top Anbieter</h3>
          <div className="mt-4 space-y-2">
            {data.by_provider.length === 0 && <div className="text-sm text-[#9baeca]">Noch keine Klicks.</div>}
            {data.by_provider.map((p, i) => (
              <div key={i} className="flex justify-between items-center border-b border-[#1a2d5e] py-2">
                <span className="text-sm">{p.name}</span>
                <span className="font-mono text-[#FDFBF7]">{p.clicks}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="surface p-5">
          <h3 className="font-display text-xl uppercase">Top Länder</h3>
          <div className="mt-4 space-y-2">
            {data.by_country.map((c, i) => (
              <div key={i} className="flex justify-between items-center border-b border-[#1a2d5e] py-2">
                <span className="text-sm">{c.country}</span>
                <span className="font-mono text-[#FDFBF7]">{c.clicks}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="surface p-5">
          <h3 className="font-display text-xl uppercase">Top Strecken</h3>
          <div className="mt-4 space-y-2">
            {data.top_routes.map((r, i) => (
              <div key={i} className="flex justify-between items-center border-b border-[#1a2d5e] py-2 gap-2">
                <span className="text-xs truncate">{r.route}</span>
                <span className="font-mono text-[#FDFBF7]">{r.clicks}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-10 surface p-5">
        <h3 className="font-display text-xl uppercase">Letzte Klicks</h3>
        <div className="mt-4 grid gap-1">
          {data.recent.map((r, i) => (
            <div key={i} className="flex items-center gap-4 py-1 border-b border-[#1a2d5e] text-xs">
              <span className="font-mono w-40 text-[#9baeca]">{new Date(r.ts).toLocaleString("de-DE")}</span>
              <span className="w-32 truncate">{r.provider}</span>
              <span className="w-12 font-mono text-[#9baeca]">{r.country || "—"}</span>
              <span className="flex-1 truncate text-[#9baeca]">{r.leg || "—"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============== Auth (Login/Register) ==============
export function AuthPage({ mode = "login" }) {
  const { login, register, user } = useAuth();
  const { t } = useT();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (user) navigate("/", { replace: true }); }, [user, navigate]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr(null); setLoading(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
      navigate("/", { replace: true });
    } catch (ex) {
      setErr(ex?.response?.data?.detail || t("search.error"));
    } finally { setLoading(false); }
  };

  return (
    <div className="max-w-md mx-auto px-6 py-20">
      <div className="eyebrow">{mode === "login" ? t("auth.login") : t("auth.register")}</div>
      <h1 className="font-display text-4xl uppercase mt-2">{mode === "login" ? t("auth.login_h") : t("auth.register_h")}</h1>
      <form onSubmit={onSubmit} className="mt-8 surface p-6 space-y-5">
        {mode === "register" && (
          <div className="field">
            <label className="field-label">{t("auth.name")}</label>
            <input data-testid="auth-name" className="field-input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
        )}
        <div className="field">
          <label className="field-label">{t("auth.email")}</label>
          <input data-testid="auth-email" type="email" required className="field-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="field">
          <label className="field-label">{t("auth.password")}</label>
          <input data-testid="auth-password" type="password" required minLength={6} className="field-input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        {err && <div className="text-[#E63946] text-sm font-mono">{err}</div>}
        <button data-testid="auth-submit" disabled={loading} className="btn btn-primary btn-block">{loading ? "..." : (mode === "login" ? t("auth.login_h") : t("auth.register_h"))}</button>
        <div className="text-center text-sm text-[#9baeca]">
          {mode === "login" ? (
            <>{t("auth.no_acc")} <Link to="/register" className="underline">{t("auth.signup_link")}</Link></>
          ) : (
            <>{t("auth.has_acc")} <Link to="/login" className="underline">{t("auth.signin_link")}</Link></>
          )}
        </div>
      </form>
    </div>
  );
}
