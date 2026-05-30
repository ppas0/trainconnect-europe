/**
 * Statische Daten: Bahnhöfe, Betreiber, Streckenberechnung, Polylinien
 */
const { v4: uuidv4 } = require('uuid');

const STATIONS = [
  // Deutschland
  { id:'BER', name:'Berlin Hbf',            city:'Berlin',        country:'DE', lat:52.5251, lon:13.3694 },
  { id:'MUC', name:'München Hbf',           city:'München',       country:'DE', lat:48.1402, lon:11.5602 },
  { id:'HAM', name:'Hamburg Hbf',           city:'Hamburg',       country:'DE', lat:53.5530, lon:10.0061 },
  { id:'FRA', name:'Frankfurt Hbf',         city:'Frankfurt',     country:'DE', lat:50.1072, lon:8.6637  },
  { id:'KOL', name:'Köln Hbf',              city:'Köln',          country:'DE', lat:50.9430, lon:6.9590  },
  { id:'STU', name:'Stuttgart Hbf',         city:'Stuttgart',     country:'DE', lat:48.7840, lon:9.1827  },
  { id:'DUS', name:'Düsseldorf Hbf',        city:'Düsseldorf',    country:'DE', lat:51.2199, lon:6.7942  },
  { id:'NUR', name:'Nürnberg Hbf',          city:'Nürnberg',      country:'DE', lat:49.4454, lon:11.0820 },
  { id:'DRE', name:'Dresden Hbf',           city:'Dresden',       country:'DE', lat:51.0407, lon:13.7326 },
  // Schweiz
  { id:'ZRH', name:'Zürich HB',             city:'Zürich',        country:'CH', lat:47.3783, lon:8.5404  },
  { id:'BSL', name:'Basel SBB',             city:'Basel',         country:'CH', lat:47.5476, lon:7.5899  },
  { id:'GEN', name:'Genf Cornavin',         city:'Genf',          country:'CH', lat:46.2104, lon:6.1422  },
  { id:'BRN', name:'Bern Hbf',              city:'Bern',          country:'CH', lat:46.9488, lon:7.4393  },
  { id:'LUZ', name:'Luzern',               city:'Luzern',        country:'CH', lat:47.0502, lon:8.3093  },
  // Österreich
  { id:'VIE', name:'Wien Hbf',              city:'Wien',          country:'AT', lat:48.1848, lon:16.3762 },
  { id:'SZG', name:'Salzburg Hbf',          city:'Salzburg',      country:'AT', lat:47.8126, lon:13.0454 },
  { id:'IBK', name:'Innsbruck Hbf',         city:'Innsbruck',     country:'AT', lat:47.2639, lon:11.4014 },
  { id:'GRZ', name:'Graz Hbf',              city:'Graz',          country:'AT', lat:47.0707, lon:15.3913 },
  // Frankreich
  { id:'CDG', name:'Paris Gare du Nord',    city:'Paris',         country:'FR', lat:48.8809, lon:2.3553  },
  { id:'PGL', name:'Paris Gare de Lyon',    city:'Paris',         country:'FR', lat:48.8450, lon:2.3735  },
  { id:'LYO', name:'Lyon Part-Dieu',        city:'Lyon',          country:'FR', lat:45.7606, lon:4.8598  },
  { id:'MRS', name:'Marseille St-Charles',  city:'Marseille',     country:'FR', lat:43.3026, lon:5.3808  },
  { id:'BDX', name:'Bordeaux St-Jean',      city:'Bordeaux',      country:'FR', lat:44.8255, lon:-0.5561 },
  // Niederlande
  { id:'AMS', name:'Amsterdam Centraal',    city:'Amsterdam',     country:'NL', lat:52.3791, lon:4.9003  },
  { id:'RTD', name:'Rotterdam Centraal',    city:'Rotterdam',     country:'NL', lat:51.9248, lon:4.4687  },
  // Belgien
  { id:'BRU', name:'Brüssel Midi',          city:'Brüssel',       country:'BE', lat:50.8354, lon:4.3363  },
  // Italien
  { id:'ROM', name:'Roma Termini',          city:'Rom',           country:'IT', lat:41.9009, lon:12.5012 },
  { id:'MIL', name:'Milano Centrale',       city:'Mailand',       country:'IT', lat:45.4860, lon:9.2045  },
  { id:'VEN', name:'Venezia Santa Lucia',   city:'Venedig',       country:'IT', lat:45.4414, lon:12.3209 },
  { id:'FLR', name:'Firenze SMN',           city:'Florenz',       country:'IT', lat:43.7746, lon:11.2480 },
  { id:'NAP', name:'Napoli Centrale',       city:'Neapel',        country:'IT', lat:40.8536, lon:14.2700 },
  // Spanien
  { id:'MAD', name:'Madrid Atocha',         city:'Madrid',        country:'ES', lat:40.4065, lon:-3.6892 },
  { id:'BCN', name:'Barcelona Sants',       city:'Barcelona',     country:'ES', lat:41.3795, lon:2.1404  },
  // UK
  { id:'LON', name:'London St Pancras',     city:'London',        country:'GB', lat:51.5308, lon:-0.1233 },
  { id:'EDI', name:'Edinburgh Waverley',    city:'Edinburgh',     country:'GB', lat:55.9521, lon:-3.1897 },
  { id:'MAN', name:'Manchester Piccadilly', city:'Manchester',    country:'GB', lat:53.4771, lon:-2.2309 },
  // Irland
  { id:'DUB', name:'Dublin Heuston',        city:'Dublin',        country:'IE', lat:53.3461, lon:-6.2931 },
  // Osteuropa
  { id:'PRG', name:'Praha hl. n.',          city:'Prag',          country:'CZ', lat:50.0831, lon:14.4356 },
  { id:'WAW', name:'Warszawa Centralna',    city:'Warschau',      country:'PL', lat:52.2288, lon:21.0031 },
  { id:'BUD', name:'Budapest Keleti',       city:'Budapest',      country:'HU', lat:47.5001, lon:19.0836 },
  { id:'KRK', name:'Kraków Główny',         city:'Krakau',        country:'PL', lat:50.0670, lon:19.9450 },
  // Skandinavien
  { id:'CPH', name:'København H',           city:'Kopenhagen',    country:'DK', lat:55.6727, lon:12.5644 },
  { id:'STO', name:'Stockholm C',           city:'Stockholm',     country:'SE', lat:59.3299, lon:18.0575 },
  { id:'OSL', name:'Oslo S',               city:'Oslo',          country:'NO', lat:59.9110, lon:10.7526 },
];

const OPERATORS = {
  DE: 'DB (Deutsche Bahn)', CH: 'SBB CFF FFS', AT: 'ÖBB',
  FR: 'SNCF', NL: 'NS', BE: 'NMBS/SNCB', IT: 'Trenitalia',
  ES: 'Renfe', GB: 'Eurostar', IE: 'Irish Rail',
  CZ: 'RegioJet', PL: 'PKP Intercity', HU: 'MÁV-Start',
  DK: 'DSB', SE: 'SJ', NO: 'Vy',
};

const OPERATOR_URLS = {
  'DB (Deutsche Bahn)':  'https://www.bahn.de',
  'SBB CFF FFS':         'https://www.sbb.ch',
  'ÖBB':                 'https://www.oebb.at',
  'SNCF':                'https://www.sncf-connect.com',
  'NS':                  'https://www.ns.nl',
  'NMBS/SNCB':           'https://www.belgiantrain.be',
  'Trenitalia':          'https://www.trenitalia.com',
  'Renfe':               'https://www.renfe.com',
  'Eurostar':            'https://www.eurostar.com',
  'Irish Rail':          'https://www.irishrail.ie',
  'RegioJet':            'https://www.regiojet.de',
  'PKP Intercity':       'https://www.pkpintercity.pl',
  'MÁV-Start':           'https://www.mavcsoport.hu',
  'DSB':                 'https://www.dsb.dk',
  'SJ':                  'https://www.sj.se',
  'Vy':                  'https://www.vy.no',
};

const TRAIN_TYPES = ['ICE','TGV','EC','IC','RJ','NJ','Railjet','EuroCity','Frecciarossa','AVE'];
const PLATFORMS = ['1','2','3','4','5','6','7','8','9','10','11','12'];

const POPULAR_PAIRS = [
  { from:'ZRH', to:'BER' }, { from:'VIE', to:'MUC' }, { from:'BRU', to:'LON' },
  { from:'CDG', to:'MIL' }, { from:'BER', to:'WAW' }, { from:'ZRH', to:'AMS' },
  { from:'BCN', to:'MAD' }, { from:'ROM', to:'MIL' }, { from:'HAM', to:'MUC' },
  { from:'FRA', to:'CDG' }, { from:'BRN', to:'ZRH' }, { from:'PRG', to:'VIE' },
  { from:'CPH', to:'STO' }, { from:'MIL', to:'VEN' }, { from:'MRS', to:'PGL' },
];

function stationById(id) {
  return STATIONS.find(s => s.id === id) || null;
}

function searchStations(q) {
  const l = q.toLowerCase();
  return STATIONS.filter(s =>
    s.name.toLowerCase().includes(l) || s.city.toLowerCase().includes(l) ||
    s.id.toLowerCase() === l || s.country.toLowerCase().includes(l)
  ).slice(0, 12);
}

function calcDistance(a, b) {
  const dx = a.lon - b.lon, dy = a.lat - b.lat;
  return Math.sqrt(dx*dx + dy*dy) * 111;
}

function generatePolyline(from, to, n = 10) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const lat = from.lat + (to.lat - from.lat) * t;
    const lon = from.lon + (to.lon - from.lon) * t;
    const curve = Math.sin(Math.PI * t) * 0.6;
    const perpLat = -(to.lon - from.lon) * 0.012 * curve;
    const perpLon =  (to.lat - from.lat) * 0.012 * curve;
    pts.push([+(lat + perpLat).toFixed(5), +(lon + perpLon).toFixed(5)]);
  }
  return pts;
}

function findMidStation(from, to) {
  const midLat = (from.lat + to.lat) / 2;
  const midLon = (from.lon + to.lon) / 2;
  let best = null, bestDist = Infinity;
  for (const s of STATIONS) {
    if (s.id === from.id || s.id === to.id) continue;
    const d = Math.abs(s.lat - midLat) + Math.abs(s.lon - midLon);
    if (d < bestDist) { bestDist = d; best = s; }
  }
  return best;
}

function makeJourney(from, to, departureISO, passengers, seatClass = '2') {
  const dist     = calcDistance(from, to);
  const isCross  = from.country !== to.country;
  const changes  = dist > 900 ? (Math.random() < 0.6 ? 1 : 0) : 0;
  const operator = isCross ? OPERATORS[to.country] || 'Eurostar' : OPERATORS[from.country] || 'DB (Deutsche Bahn)';
  const trainType = TRAIN_TYPES[Math.floor(Math.random() * TRAIN_TYPES.length)];
  const baseMins  = Math.max(30, Math.round(dist / 220 * 60));
  const totalMins = baseMins + changes * 20 + Math.floor(Math.random() * 20);
  const depDate   = new Date(departureISO);
  const arrDate   = new Date(depDate.getTime() + totalMins * 60000);
  const basePrice = Math.max(19, Math.round(dist * 0.10));
  const priceVar  = (0.75 + Math.random() * 0.55);
  const price     = Math.round(basePrice * priceVar * (seatClass === '1' ? 1.65 : 1) * passengers);

  let legs;
  if (changes === 0) {
    const trainNo = `${trainType} ${100 + Math.floor(Math.random() * 900)}`;
    legs = [{
      leg_id: uuidv4(),
      from: { id: from.id, name: from.name, city: from.city, country: from.country, lat: from.lat, lon: from.lon },
      to:   { id: to.id,   name: to.name,   city: to.city,   country: to.country,   lat: to.lat,   lon: to.lon   },
      departure:    depDate.toISOString(),
      arrival:      arrDate.toISOString(),
      duration_min: totalMins,
      operator,
      train_no:     trainNo,
      platform:     PLATFORMS[Math.floor(Math.random() * PLATFORMS.length)],
      delay_min:    0,
      polyline:     generatePolyline(from, to),
    }];
  } else {
    const mid = findMidStation(from, to);
    const midMins = Math.round(totalMins * 0.5);
    const midDate = new Date(depDate.getTime() + midMins * 60000);
    const layoverMins = 15 + Math.floor(Math.random() * 15);
    const mid2Date = new Date(midDate.getTime() + layoverMins * 60000);
    const leg2Op = OPERATORS[to.country] || operator;
    legs = [
      {
        leg_id: uuidv4(),
        from: { id: from.id, name: from.name, city: from.city, country: from.country, lat: from.lat, lon: from.lon },
        to:   { id: mid.id,  name: mid.name,  city: mid.city,  country: mid.country,  lat: mid.lat,  lon: mid.lon  },
        departure:    depDate.toISOString(),
        arrival:      midDate.toISOString(),
        duration_min: midMins,
        operator,
        train_no:     `${trainType} ${100 + Math.floor(Math.random() * 900)}`,
        platform:     PLATFORMS[Math.floor(Math.random() * PLATFORMS.length)],
        delay_min:    0,
        polyline:     generatePolyline(from, mid),
      },
      {
        leg_id: uuidv4(),
        from: { id: mid.id, name: mid.name, city: mid.city, country: mid.country, lat: mid.lat, lon: mid.lon },
        to:   { id: to.id,  name: to.name,  city: to.city,  country: to.country,  lat: to.lat,  lon: to.lon  },
        departure:    mid2Date.toISOString(),
        arrival:      arrDate.toISOString(),
        duration_min: totalMins - midMins - layoverMins,
        operator:     leg2Op,
        train_no:     `${TRAIN_TYPES[Math.floor(Math.random() * TRAIN_TYPES.length)]} ${100 + Math.floor(Math.random() * 900)}`,
        platform:     PLATFORMS[Math.floor(Math.random() * PLATFORMS.length)],
        delay_min:    0,
        polyline:     generatePolyline(mid, to),
      },
    ];
  }

  const providerLinks = [];
  const uniqueOps = [...new Set(legs.map(l => l.operator))];
  uniqueOps.forEach((op, i) => {
    const leg = legs.find(l => l.operator === op);
    if (OPERATOR_URLS[op]) {
      providerLinks.push({
        name:    op,
        country: legs[i]?.to?.country || to.country,
        url:     OPERATOR_URLS[op],
        leg:     `${leg?.from?.city} → ${leg?.to?.city}`,
      });
    }
  });

  return {
    id:           uuidv4(),
    from:         { id: from.id, name: from.name, city: from.city, country: from.country, lat: from.lat, lon: from.lon },
    to:           { id: to.id,   name: to.name,   city: to.city,   country: to.country,   lat: to.lat,   lon: to.lon   },
    departure:    depDate.toISOString(),
    arrival:      arrDate.toISOString(),
    duration_min: totalMins,
    changes,
    passengers,
    total_price:  price,
    legs,
    provider_links: providerLinks,
    data_source:  'curated',
  };
}

function searchJourneys({ from_id, to_id, departure, passengers = 1 }) {
  const from = stationById(from_id);
  const to   = stationById(to_id);
  if (!from || !to || from_id === to_id) return [];

  const count = 5 + Math.floor(Math.random() * 3);
  const results = [];
  const dep = new Date(departure);

  for (let i = 0; i < count; i++) {
    const offset = i * (90 + Math.floor(Math.random() * 30)) * 60000;
    const jDep = new Date(dep.getTime() + offset).toISOString();
    results.push(makeJourney(from, to, jDep, passengers));
  }
  return results.sort((a, b) => new Date(a.departure) - new Date(b.departure));
}

function generateDepartures(stationId) {
  const station = stationById(stationId);
  if (!station) return [];
  const now = new Date();
  const deps = [];
  for (let i = 0; i < 12; i++) {
    const dest = STATIONS[Math.floor(Math.random() * STATIONS.length)];
    if (dest.id === stationId) continue;
    const when = new Date(now.getTime() + (5 + i * 25 + Math.floor(Math.random() * 15)) * 60000);
    const trainType = TRAIN_TYPES[Math.floor(Math.random() * TRAIN_TYPES.length)];
    deps.push({
      when:      when.toISOString(),
      line:      `${trainType} ${100 + Math.floor(Math.random() * 900)}`,
      direction: dest.name,
      platform:  PLATFORMS[Math.floor(Math.random() * PLATFORMS.length)],
      delay_min: Math.random() < 0.15 ? Math.floor(Math.random() * 20) + 2 : 0,
    });
  }
  return deps.sort((a, b) => new Date(a.when) - new Date(b.when));
}

function generateLiveData(journey) {
  const now = new Date();
  return {
    legs: journey.legs.map((leg) => {
      const dep = new Date(leg.departure);
      const arr = new Date(leg.arrival);
      const total = arr - dep;
      const elapsed = now - dep;
      if (elapsed < 0) return { ...leg, status: 'scheduled', progress: 0, current_position: [leg.from.lat, leg.from.lon], delay_min: 0 };
      if (elapsed >= total) return { ...leg, status: 'arrived', progress: 1, current_position: [leg.to.lat, leg.to.lon], delay_min: 0 };
      const progress = Math.min(1, elapsed / total);
      const poly = leg.polyline;
      const idx = Math.floor(progress * (poly.length - 1));
      const pos = poly[Math.min(idx, poly.length - 1)] || [leg.from.lat, leg.from.lon];
      const delay = Math.random() < 0.2 ? Math.floor(Math.random() * 12) : 0;
      return { ...leg, status: 'in_transit', progress: +progress.toFixed(3), current_position: pos, delay_min: delay };
    }),
  };
}

const AFFILIATE_PROVIDERS = [
  { provider: 'db',         name: 'Deutsche Bahn',  affiliate_id: null, signup_url: 'https://www.bahn.de/service/affiliate-programm' },
  { provider: 'sbb',        name: 'SBB CFF FFS',    affiliate_id: null, signup_url: 'https://www.sbb.ch/de/meta/affiliate.html' },
  { provider: 'oebb',       name: 'ÖBB',            affiliate_id: null, signup_url: 'https://www.oebb.at/de/meta/affiliate' },
  { provider: 'sncf',       name: 'SNCF Connect',   affiliate_id: null, signup_url: 'https://www.sncf-connect.com/app/en-en/affiliate' },
  { provider: 'eurostar',   name: 'Eurostar',        affiliate_id: null, signup_url: 'https://www.eurostar.com/uk-en/about-eurostar/affiliates' },
  { provider: 'trenitalia', name: 'Trenitalia',      affiliate_id: null, signup_url: 'https://www.trenitalia.com/en/affiliate.html' },
  { provider: 'renfe',      name: 'Renfe',           affiliate_id: null, signup_url: 'https://www.renfe.com/es/en/about-renfe/affiliate' },
];

module.exports = {
  STATIONS, OPERATORS, OPERATOR_URLS, POPULAR_PAIRS, AFFILIATE_PROVIDERS,
  stationById, searchStations, searchJourneys, generateDepartures, generateLiveData,
};
