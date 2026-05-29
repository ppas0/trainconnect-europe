// Tiny zero-dependency i18n with React Context.
import { createContext, useContext, useEffect, useState } from "react";

export const LANGS = [
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
  { code: "en", label: "English", flag: "🇬🇧" },
  { code: "fr", label: "Français", flag: "🇫🇷" },
  { code: "it", label: "Italiano", flag: "🇮🇹" },
  { code: "es", label: "Español", flag: "🇪🇸" },
];

// Single source of truth – keys grouped by area
export const DICT = {
  // Header
  "nav.stations": { de: "Bahnhöfe", en: "Stations", fr: "Gares", it: "Stazioni", es: "Estaciones" },
  "nav.tickets": { de: "Tickets", en: "Tickets", fr: "Billets", it: "Biglietti", es: "Billetes" },
  "nav.cart": { de: "Warenkorb", en: "Cart", fr: "Panier", it: "Carrello", es: "Cesta" },
  "nav.login": { de: "Einloggen", en: "Log in", fr: "Connexion", it: "Accedi", es: "Entrar" },
  "nav.logout": { de: "Ausloggen", en: "Log out", fr: "Déconnexion", it: "Esci", es: "Salir" },

  // Home / Hero
  "home.eyebrow": { de: "Live · 200+ Bahnhöfe · 30+ Länder", en: "Live · 200+ stations · 30+ countries", fr: "Direct · 200+ gares · 30+ pays", it: "Live · 200+ stazioni · 30+ paesi", es: "En vivo · 200+ estaciones · 30+ países" },
  "home.title1": { de: "Ein Ticket.", en: "One ticket.", fr: "Un billet.", it: "Un biglietto.", es: "Un billete." },
  "home.title2": { de: "Ganz Europa.", en: "All of Europe.", fr: "Toute l'Europe.", it: "Tutta l'Europa.", es: "Toda Europa." },
  "home.lead": {
    de: "Suche, vergleiche und buche Zugverbindungen von Dublin bis Athen. Live-Position des Zugs auf der Karte. Ein Warenkorb, ein Checkout.",
    en: "Search, compare and book train connections from Dublin to Athens. Live train position on the map. One cart, one checkout.",
    fr: "Recherchez, comparez et réservez des trains de Dublin à Athènes. Position en direct sur la carte. Un panier, un paiement.",
    it: "Cerca, confronta e prenota treni da Dublino ad Atene. Posizione live sulla mappa. Un carrello, un checkout.",
    es: "Busca, compara y reserva trenes de Dublín a Atenas. Posición en vivo en el mapa. Un carrito, un pago."
  },
  "home.popular.eyebrow": { de: "Vorschläge", en: "Suggestions", fr: "Suggestions", it: "Suggerimenti", es: "Sugerencias" },
  "home.popular.title": { de: "Beliebte Verbindungen", en: "Popular Connections", fr: "Connexions Populaires", it: "Connessioni Popolari", es: "Conexiones Populares" },
  "home.all_stations": { de: "Alle Bahnhöfe →", en: "All Stations →", fr: "Toutes les gares →", it: "Tutte le stazioni →", es: "Todas las estaciones →" },
  "home.feat1.t": { de: "Pan-europäisch", en: "Pan-European", fr: "Pan-européen", it: "Pan-europeo", es: "Paneuropeo" },
  "home.feat1.d": { de: "Daten aus DB, SNCF, ÖBB, SBB, Trenitalia, Renfe, Vy, MÁV und mehr – über HAFAS und OpenRailwayMap.", en: "Data from DB, SNCF, ÖBB, SBB, Trenitalia, Renfe, Vy, MÁV and more – via HAFAS and OpenRailwayMap.", fr: "Données DB, SNCF, ÖBB, SBB, Trenitalia, Renfe, Vy, MÁV et plus – via HAFAS et OpenRailwayMap.", it: "Dati da DB, SNCF, ÖBB, SBB, Trenitalia, Renfe, Vy, MÁV e altri – via HAFAS e OpenRailwayMap.", es: "Datos de DB, SNCF, ÖBB, SBB, Trenitalia, Renfe, Vy, MÁV y más – vía HAFAS y OpenRailwayMap." },
  "home.feat2.t": { de: "Live-Karte", en: "Live Map", fr: "Carte en direct", it: "Mappa live", es: "Mapa en vivo" },
  "home.feat2.d": { de: "Sieh die aktuelle Position deines Zugs in Echtzeit auf der OpenRailwayMap-Karte.", en: "See your train's current position in real time on the OpenRailwayMap.", fr: "Voyez la position actuelle de votre train en temps réel sur la carte OpenRailwayMap.", it: "Vedi la posizione attuale del treno in tempo reale sulla OpenRailwayMap.", es: "Ve la posición actual de tu tren en tiempo real en OpenRailwayMap." },
  "home.feat3.t": { de: "Multi-Leg-Cart", en: "Multi-Leg Cart", fr: "Panier multi-étapes", it: "Carrello multi-tratta", es: "Carrito multi-tramo" },
  "home.feat3.d": { de: "Mehrere Anschlüsse in einem Checkout. Stripe-Testmodus, eine PDF pro Strecke.", en: "Multiple connections in one checkout. Stripe test mode, one PDF per route.", fr: "Plusieurs correspondances en un paiement. Mode test Stripe, un PDF par trajet.", it: "Più coincidenze in un solo checkout. Stripe test mode, un PDF per tratta.", es: "Varias conexiones en un pago. Modo prueba Stripe, un PDF por trayecto." },

  // Search form
  "form.from": { de: "Von", en: "From", fr: "De", it: "Da", es: "Desde" },
  "form.to": { de: "Nach", en: "To", fr: "À", it: "A", es: "Hasta" },
  "form.date": { de: "Datum", en: "Date", fr: "Date", it: "Data", es: "Fecha" },
  "form.time": { de: "Zeit", en: "Time", fr: "Heure", it: "Ora", es: "Hora" },
  "form.pax": { de: "Pers.", en: "Pax", fr: "Pers.", it: "Pers.", es: "Pers." },
  "form.from_ph": { de: "Stadt oder Bahnhof", en: "City or station", fr: "Ville ou gare", it: "Città o stazione", es: "Ciudad o estación" },
  "form.to_ph": { de: "z.B. Athína", en: "e.g. Athína", fr: "ex. Athína", it: "es. Athína", es: "ej. Athína" },
  "form.demo_badge": { de: "Demo · Live-Daten + Test-Payment", en: "Demo · Live data + test payment", fr: "Démo · Données live + paiement test", it: "Demo · Dati live + pagamento test", es: "Demo · Datos en vivo + pago de prueba" },
  "form.submit": { de: "Verbindungen finden", en: "Find connections", fr: "Trouver des connexions", it: "Trova connessioni", es: "Buscar conexiones" },

  // Search results
  "search.loading": { de: "Suche Verbindungen...", en: "Searching connections...", fr: "Recherche en cours...", it: "Ricerca in corso...", es: "Buscando conexiones..." },
  "search.error": { de: "Fehler bei der Suche", en: "Search failed", fr: "Erreur de recherche", it: "Errore di ricerca", es: "Error en la búsqueda" },
  "search.choose": { de: "Wähle eine Verbindung", en: "Pick a connection", fr: "Choisissez une connexion", it: "Scegli una connessione", es: "Elige una conexión" },
  "search.changes": { de: "Umstiege", en: "changes", fr: "correspondances", it: "cambi", es: "transbordos" },
  "search.on_time": { de: "Pünktlich", en: "On time", fr: "À l'heure", it: "In orario", es: "Puntual" },
  "search.from_price": { de: "ab", en: "from", fr: "dès", it: "da", es: "desde" },
  "search.view": { de: "Details + Live-Karte", en: "Details + live map", fr: "Détails + carte live", it: "Dettagli + mappa live", es: "Detalles + mapa en vivo" },
  "search.add_cart": { de: "In den Warenkorb", en: "Add to cart", fr: "Ajouter au panier", it: "Aggiungi al carrello", es: "Añadir al carrito" },
  "search.live": { de: "Live", en: "Live", fr: "Direct", it: "Live", es: "En vivo" },
  "search.curated": { de: "Kuratiert", en: "Curated", fr: "Curé", it: "Selezionato", es: "Curado" },

  // Journey detail
  "jd.heading": { de: "Verbindung", en: "Connection", fr: "Connexion", it: "Connessione", es: "Conexión" },
  "jd.duration": { de: "Dauer", en: "Duration", fr: "Durée", it: "Durata", es: "Duración" },
  "jd.leg": { de: "Etappe", en: "Leg", fr: "Étape", it: "Tratta", es: "Tramo" },
  "jd.platform": { de: "Gleis", en: "Platform", fr: "Voie", it: "Binario", es: "Andén" },
  "jd.live_progress": { de: "unterwegs", en: "en route", fr: "en route", it: "in viaggio", es: "en ruta" },
  "jd.total": { de: "Gesamtpreis", en: "Total", fr: "Total", it: "Totale", es: "Total" },
  "jd.loading": { de: "Lade Verbindung...", en: "Loading connection...", fr: "Chargement...", it: "Caricamento...", es: "Cargando..." },
  "jd.providers": { de: "Direkt beim Anbieter buchen", en: "Book directly with operator", fr: "Réserver directement", it: "Prenota direttamente", es: "Reservar directamente" },
  "jd.providers_note": { de: "Diese Plattform stellt nur Demo-Reservierungen aus. Für offizielle Tickets nutze einen der folgenden Anbieter:", en: "This platform issues demo reservations only. For official tickets use one of the following operators:", fr: "Cette plateforme délivre des réservations de démo uniquement. Pour des billets officiels, utilisez l'un des opérateurs suivants:", it: "Questa piattaforma emette solo prenotazioni demo. Per biglietti ufficiali usa uno dei seguenti operatori:", es: "Esta plataforma emite solo reservas de demostración. Para billetes oficiales usa uno de los siguientes operadores:" },

  // Stations
  "st.network": { de: "Netz", en: "Network", fr: "Réseau", it: "Rete", es: "Red" },
  "st.title": { de: "Bahnhöfe in Europa", en: "Stations in Europe", fr: "Gares en Europe", it: "Stazioni in Europa", es: "Estaciones en Europa" },
  "st.departures": { de: "Nächste Abfahrten", en: "Next departures", fr: "Prochains départs", it: "Prossime partenze", es: "Próximas salidas" },
  "st.platform_short": { de: "Gl.", en: "Pl.", fr: "V.", it: "Bin.", es: "And." },

  // Cart
  "cart.empty.title": { de: "Warenkorb leer", en: "Cart is empty", fr: "Panier vide", it: "Carrello vuoto", es: "Cesta vacía" },
  "cart.empty.lead": { de: "Suche eine Verbindung und füge sie hinzu.", en: "Search a connection and add it.", fr: "Recherchez une connexion et ajoutez-la.", it: "Cerca una connessione e aggiungila.", es: "Busca una conexión y añádela." },
  "cart.empty.cta": { de: "Verbindungen suchen", en: "Search connections", fr: "Rechercher", it: "Cerca", es: "Buscar" },
  "cart.title": { de: "Warenkorb", en: "Cart", fr: "Panier", it: "Carrello", es: "Cesta" },
  "cart.checkout_label": { de: "Checkout", en: "Checkout", fr: "Paiement", it: "Pagamento", es: "Pago" },
  "cart.demo_badge": { de: "Stripe Testmodus · Karte 4242 4242 4242 4242", en: "Stripe test mode · card 4242 4242 4242 4242", fr: "Mode test Stripe · carte 4242 4242 4242 4242", it: "Stripe test mode · carta 4242 4242 4242 4242", es: "Stripe modo prueba · tarjeta 4242 4242 4242 4242" },
  "cart.remove": { de: "Entfernen", en: "Remove", fr: "Retirer", it: "Rimuovi", es: "Quitar" },
  "cart.total": { de: "Gesamt", en: "Total", fr: "Total", it: "Totale", es: "Total" },
  "cart.clear": { de: "Leeren", en: "Clear", fr: "Vider", it: "Svuota", es: "Vaciar" },
  "cart.pay": { de: "Zur Kasse (Stripe Test)", en: "Checkout (Stripe test)", fr: "Payer (test Stripe)", it: "Paga (Stripe test)", es: "Pagar (Stripe test)" },
  "cart.paying": { de: "Weiterleiten...", en: "Redirecting...", fr: "Redirection...", it: "Reindirizzamento...", es: "Redirigiendo..." },
  "cart.login_hint": { de: "Hinweis: Logge dich ein, damit Tickets in deinem Konto erscheinen.", en: "Hint: log in so tickets appear in your account.", fr: "Astuce : connectez-vous pour retrouver vos billets.", it: "Suggerimento: accedi per salvare i biglietti.", es: "Consejo: inicia sesión para guardar los billetes." },

  // Checkout success
  "cs.paid.title": { de: "Buchung bestätigt", en: "Booking confirmed", fr: "Réservation confirmée", it: "Prenotazione confermata", es: "Reserva confirmada" },
  "cs.paid.lead": { de: "Dein Ticket ist im Konto. Lade die PDF herunter oder zeige sie am Bahnhof.", en: "Your ticket is in your account. Download the PDF or show it at the station.", fr: "Votre billet est dans votre compte. Téléchargez le PDF ou présentez-le en gare.", it: "Il biglietto è nel tuo account. Scarica il PDF o mostralo in stazione.", es: "Tu billete está en tu cuenta. Descarga el PDF o muéstralo en la estación." },
  "cs.paid.cta": { de: "Meine Tickets ansehen", en: "View my tickets", fr: "Voir mes billets", it: "Vedi i miei biglietti", es: "Ver mis billetes" },
  "cs.pending": { de: "Zahlung wird geprüft...", en: "Verifying payment...", fr: "Vérification du paiement...", it: "Verifica pagamento...", es: "Verificando pago..." },
  "cs.attempt": { de: "Versuch", en: "Attempt", fr: "Tentative", it: "Tentativo", es: "Intento" },
  "cs.failed": { de: "Zahlung nicht bestätigt", en: "Payment not confirmed", fr: "Paiement non confirmé", it: "Pagamento non confermato", es: "Pago no confirmado" },
  "cs.back": { de: "Zurück zum Warenkorb", en: "Back to cart", fr: "Retour au panier", it: "Torna al carrello", es: "Volver a la cesta" },

  // Tickets
  "tk.account": { de: "Konto", en: "Account", fr: "Compte", it: "Account", es: "Cuenta" },
  "tk.title": { de: "Meine Tickets", en: "My Tickets", fr: "Mes billets", it: "I miei biglietti", es: "Mis billetes" },
  "tk.none": { de: "Noch keine Tickets gebucht.", en: "No tickets booked yet.", fr: "Aucun billet réservé.", it: "Nessun biglietto prenotato.", es: "No hay billetes." },
  "tk.login_required": { de: "Login erforderlich", en: "Login required", fr: "Connexion requise", it: "Accesso richiesto", es: "Inicia sesión" },

  // Auth
  "auth.login": { de: "Anmeldung", en: "Sign in", fr: "Connexion", it: "Accesso", es: "Iniciar sesión" },
  "auth.register": { de: "Registrierung", en: "Sign up", fr: "Inscription", it: "Registrazione", es: "Registro" },
  "auth.login_h": { de: "Einloggen", en: "Log in", fr: "Se connecter", it: "Accedi", es: "Entrar" },
  "auth.register_h": { de: "Konto erstellen", en: "Create account", fr: "Créer un compte", it: "Crea account", es: "Crear cuenta" },
  "auth.name": { de: "Name", en: "Name", fr: "Nom", it: "Nome", es: "Nombre" },
  "auth.email": { de: "E-Mail", en: "Email", fr: "E-mail", it: "Email", es: "Correo" },
  "auth.password": { de: "Passwort", en: "Password", fr: "Mot de passe", it: "Password", es: "Contraseña" },
  "auth.no_acc": { de: "Kein Konto?", en: "No account?", fr: "Pas de compte ?", it: "Nessun account?", es: "¿Sin cuenta?" },
  "auth.has_acc": { de: "Schon registriert?", en: "Already have one?", fr: "Déjà inscrit ?", it: "Già registrato?", es: "¿Ya registrado?" },
  "auth.signup_link": { de: "Registrieren", en: "Sign up", fr: "S'inscrire", it: "Registrati", es: "Regístrate" },
  "auth.signin_link": { de: "Einloggen", en: "Sign in", fr: "Se connecter", it: "Accedi", es: "Entrar" },

  // Common
  "common.persons": { de: "Pers.", en: "pers.", fr: "pers.", it: "pers.", es: "pers." },
  "common.delay_short": { de: "min", en: "min", fr: "min", it: "min", es: "min" },
};

const LangCtx = createContext({ lang: "de", setLang: () => {}, t: (k) => k });

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem("tc_lang");
    if (saved && LANGS.find((l) => l.code === saved)) return saved;
    const nav = (navigator.language || "de").slice(0, 2);
    return LANGS.find((l) => l.code === nav) ? nav : "de";
  });

  useEffect(() => {
    localStorage.setItem("tc_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const t = (key) => DICT[key]?.[lang] || DICT[key]?.de || key;

  return <LangCtx.Provider value={{ lang, setLang: setLangState, t }}>{children}</LangCtx.Provider>;
}

export const useT = () => useContext(LangCtx);
