"""
graph.py — Logistics graph: 210 global hubs + auto-generated multi-modal edges.
v2: Expanded from 25 → 210 nodes with proximity-based edge generation.
"""
import math
import itertools

# ---------------------------------------------------------------------------
# Mode speeds (km/h) and cost-per-km-per-ton (USD)
# ---------------------------------------------------------------------------
MODE_SPEED   = {"air": 820, "sea": 38, "rail": 100, "road": 70}
MODE_COST_KM = {"air": 4.8, "sea": 0.7, "rail": 1.4, "road": 2.0}

# ---------------------------------------------------------------------------
# Nodes — 210 global logistics hubs
# tier: 1=mega hub, 2=regional hub, 3=local hub
# ---------------------------------------------------------------------------
NODES = {
    # ── EAST ASIA ────────────────────────────────────────────────────────
    "shanghai":      {"name": "Shanghai",       "lat":  31.23, "lon": 121.47, "type": "port",    "country": "CN", "country_name": "China",        "tier": 1, "throughput_teu": 47000000},
    "hong_kong":     {"name": "Hong Kong",      "lat":  22.32, "lon": 114.17, "type": "port",    "country": "HK", "country_name": "Hong Kong",    "tier": 1, "throughput_teu": 18000000},
    "shenzhen":      {"name": "Shenzhen",       "lat":  22.54, "lon": 114.06, "type": "port",    "country": "CN", "country_name": "China",        "tier": 1, "throughput_teu": 28000000},
    "beijing":       {"name": "Beijing",        "lat":  39.91, "lon": 116.39, "type": "hub",     "country": "CN", "country_name": "China",        "tier": 1, "throughput_teu": 5000000},
    "guangzhou":     {"name": "Guangzhou",      "lat":  23.13, "lon": 113.27, "type": "port",    "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 24000000},
    "tianjin":       {"name": "Tianjin",        "lat":  39.33, "lon": 117.36, "type": "port",    "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 18000000},
    "qingdao":       {"name": "Qingdao",        "lat":  36.07, "lon": 120.38, "type": "port",    "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 22000000},
    "ningbo":        {"name": "Ningbo",         "lat":  29.87, "lon": 121.55, "type": "port",    "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 33000000},
    "xiamen":        {"name": "Xiamen",         "lat":  24.48, "lon": 118.09, "type": "port",    "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 12000000},
    "chengdu":       {"name": "Chengdu",        "lat":  30.57, "lon": 104.07, "type": "hub",     "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 3000000},
    "wuhan":         {"name": "Wuhan",          "lat":  30.59, "lon": 114.30, "type": "hub",     "country": "CN", "country_name": "China",        "tier": 2, "throughput_teu": 2000000},
    "tokyo":         {"name": "Tokyo",          "lat":  35.68, "lon": 139.69, "type": "port",    "country": "JP", "country_name": "Japan",        "tier": 1, "throughput_teu": 4200000},
    "osaka":         {"name": "Osaka",          "lat":  34.69, "lon": 135.50, "type": "port",    "country": "JP", "country_name": "Japan",        "tier": 2, "throughput_teu": 2300000},
    "nagoya":        {"name": "Nagoya",         "lat":  35.18, "lon": 136.91, "type": "port",    "country": "JP", "country_name": "Japan",        "tier": 2, "throughput_teu": 2800000},
    "seoul":         {"name": "Seoul",          "lat":  37.57, "lon": 126.98, "type": "hub",     "country": "KR", "country_name": "South Korea",  "tier": 1, "throughput_teu": 2000000},
    "busan":         {"name": "Busan",          "lat":  35.18, "lon": 129.08, "type": "port",    "country": "KR", "country_name": "South Korea",  "tier": 1, "throughput_teu": 22000000},
    "vladivostok":   {"name": "Vladivostok",    "lat":  43.12, "lon": 131.88, "type": "port",    "country": "RU", "country_name": "Russia",       "tier": 3, "throughput_teu": 800000},
    "taipei":        {"name": "Taipei",         "lat":  25.04, "lon": 121.56, "type": "hub",     "country": "TW", "country_name": "Taiwan",       "tier": 2, "throughput_teu": 15000000},
    "kaohsiung":     {"name": "Kaohsiung",      "lat":  22.63, "lon": 120.27, "type": "port",    "country": "TW", "country_name": "Taiwan",       "tier": 2, "throughput_teu": 10000000},
    "ho_chi_minh":   {"name": "Ho Chi Minh",    "lat":  10.82, "lon": 106.63, "type": "port",    "country": "VN", "country_name": "Vietnam",      "tier": 2, "throughput_teu": 7000000},
    "hanoi":         {"name": "Hanoi",          "lat":  21.03, "lon": 105.83, "type": "hub",     "country": "VN", "country_name": "Vietnam",      "tier": 3, "throughput_teu": 1000000},
    "manila":        {"name": "Manila",         "lat":  14.60, "lon": 120.98, "type": "port",    "country": "PH", "country_name": "Philippines",  "tier": 2, "throughput_teu": 5000000},
    "bangkok":       {"name": "Bangkok",        "lat":  13.76, "lon": 100.50, "type": "port",    "country": "TH", "country_name": "Thailand",     "tier": 2, "throughput_teu": 8000000},
    "jakarta":       {"name": "Jakarta",        "lat":  -6.21, "lon": 106.85, "type": "port",    "country": "ID", "country_name": "Indonesia",    "tier": 2, "throughput_teu": 8500000},
    "surabaya":      {"name": "Surabaya",       "lat":  -7.25, "lon": 112.75, "type": "port",    "country": "ID", "country_name": "Indonesia",    "tier": 3, "throughput_teu": 3500000},
    "kuala_lumpur":  {"name": "Kuala Lumpur",   "lat":   3.15, "lon": 101.69, "type": "hub",     "country": "MY", "country_name": "Malaysia",     "tier": 2, "throughput_teu": 2000000},
    "port_klang":    {"name": "Port Klang",     "lat":   3.00, "lon": 101.38, "type": "port",    "country": "MY", "country_name": "Malaysia",     "tier": 1, "throughput_teu": 13000000},
    # ── SOUTHEAST ASIA ───────────────────────────────────────────────────
    "singapore":     {"name": "Singapore",      "lat":   1.35, "lon": 103.82, "type": "port",    "country": "SG", "country_name": "Singapore",    "tier": 1, "throughput_teu": 38000000},
    "yangon":        {"name": "Yangon",         "lat":  16.87, "lon":  96.19, "type": "port",    "country": "MM", "country_name": "Myanmar",      "tier": 3, "throughput_teu": 800000},
    "phnom_penh":    {"name": "Phnom Penh",     "lat":  11.56, "lon": 104.93, "type": "hub",     "country": "KH", "country_name": "Cambodia",     "tier": 3, "throughput_teu": 500000},
    # ── SOUTH ASIA ───────────────────────────────────────────────────────
    "mumbai":        {"name": "Mumbai",         "lat":  19.08, "lon":  72.88, "type": "port",    "country": "IN", "country_name": "India",        "tier": 1, "throughput_teu": 5800000},
    "nhava_sheva":   {"name": "Nhava Sheva",    "lat":  18.95, "lon":  72.95, "type": "port",    "country": "IN", "country_name": "India",        "tier": 2, "throughput_teu": 5200000},
    "chennai":       {"name": "Chennai",        "lat":  13.08, "lon":  80.27, "type": "port",    "country": "IN", "country_name": "India",        "tier": 2, "throughput_teu": 2100000},
    "kolkata":       {"name": "Kolkata",        "lat":  22.57, "lon":  88.36, "type": "port",    "country": "IN", "country_name": "India",        "tier": 2, "throughput_teu": 1500000},
    "delhi":         {"name": "Delhi",          "lat":  28.61, "lon":  77.21, "type": "hub",     "country": "IN", "country_name": "India",        "tier": 1, "throughput_teu": 1000000},
    "bangalore":     {"name": "Bangalore",      "lat":  12.97, "lon":  77.59, "type": "hub",     "country": "IN", "country_name": "India",        "tier": 2, "throughput_teu": 500000},
    "karachi":       {"name": "Karachi",        "lat":  24.86, "lon":  67.01, "type": "port",    "country": "PK", "country_name": "Pakistan",     "tier": 2, "throughput_teu": 2500000},
    "colombo":       {"name": "Colombo",        "lat":   6.93, "lon":  79.85, "type": "port",    "country": "LK", "country_name": "Sri Lanka",    "tier": 2, "throughput_teu": 7200000},
    "dhaka":         {"name": "Dhaka",          "lat":  23.81, "lon":  90.41, "type": "hub",     "country": "BD", "country_name": "Bangladesh",   "tier": 3, "throughput_teu": 1000000},
    "chittagong":    {"name": "Chittagong",     "lat":  22.34, "lon":  91.83, "type": "port",    "country": "BD", "country_name": "Bangladesh",   "tier": 3, "throughput_teu": 3000000},
    "kathmandu":     {"name": "Kathmandu",      "lat":  27.70, "lon":  85.31, "type": "hub",     "country": "NP", "country_name": "Nepal",        "tier": 3, "throughput_teu": 100000},
    # ── MIDDLE EAST & CENTRAL ASIA ───────────────────────────────────────
    "dubai":         {"name": "Dubai",          "lat":  25.20, "lon":  55.27, "type": "hub",     "country": "AE", "country_name": "UAE",          "tier": 1, "throughput_teu": 15000000},
    "abu_dhabi":     {"name": "Abu Dhabi",      "lat":  24.47, "lon":  54.37, "type": "port",    "country": "AE", "country_name": "UAE",          "tier": 2, "throughput_teu": 2000000},
    "riyadh":        {"name": "Riyadh",         "lat":  24.69, "lon":  46.72, "type": "hub",     "country": "SA", "country_name": "Saudi Arabia", "tier": 2, "throughput_teu": 1000000},
    "jeddah":        {"name": "Jeddah",         "lat":  21.49, "lon":  39.19, "type": "port",    "country": "SA", "country_name": "Saudi Arabia", "tier": 2, "throughput_teu": 5500000},
    "muscat":        {"name": "Muscat",         "lat":  23.61, "lon":  58.59, "type": "port",    "country": "OM", "country_name": "Oman",         "tier": 3, "throughput_teu": 3000000},
    "kuwait_city":   {"name": "Kuwait City",    "lat":  29.37, "lon":  47.98, "type": "hub",     "country": "KW", "country_name": "Kuwait",       "tier": 3, "throughput_teu": 1000000},
    "doha":          {"name": "Doha",           "lat":  25.29, "lon":  51.53, "type": "hub",     "country": "QA", "country_name": "Qatar",        "tier": 2, "throughput_teu": 1500000},
    "manama":        {"name": "Manama",         "lat":  26.21, "lon":  50.59, "type": "hub",     "country": "BH", "country_name": "Bahrain",      "tier": 3, "throughput_teu": 500000},
    "tehran":        {"name": "Tehran",         "lat":  35.69, "lon":  51.39, "type": "hub",     "country": "IR", "country_name": "Iran",         "tier": 2, "throughput_teu": 2000000},
    "baghdad":       {"name": "Baghdad",        "lat":  33.34, "lon":  44.40, "type": "hub",     "country": "IQ", "country_name": "Iraq",         "tier": 3, "throughput_teu": 500000},
    "almaty":        {"name": "Almaty",         "lat":  43.22, "lon":  76.85, "type": "hub",     "country": "KZ", "country_name": "Kazakhstan",   "tier": 3, "throughput_teu": 400000},
    "tashkent":      {"name": "Tashkent",       "lat":  41.30, "lon":  69.24, "type": "hub",     "country": "UZ", "country_name": "Uzbekistan",   "tier": 3, "throughput_teu": 300000},
    # ── EUROPE ───────────────────────────────────────────────────────────
    "rotterdam":     {"name": "Rotterdam",      "lat":  51.92, "lon":   4.48, "type": "port",    "country": "NL", "country_name": "Netherlands",  "tier": 1, "throughput_teu": 15000000},
    "antwerp":       {"name": "Antwerp",        "lat":  51.22, "lon":   4.40, "type": "port",    "country": "BE", "country_name": "Belgium",      "tier": 1, "throughput_teu": 12000000},
    "hamburg":       {"name": "Hamburg",        "lat":  53.55, "lon":   9.99, "type": "port",    "country": "DE", "country_name": "Germany",      "tier": 1, "throughput_teu": 8700000},
    "frankfurt":     {"name": "Frankfurt",      "lat":  50.11, "lon":   8.68, "type": "hub",     "country": "DE", "country_name": "Germany",      "tier": 1, "throughput_teu": 2000000},
    "munich":        {"name": "Munich",         "lat":  48.14, "lon":  11.58, "type": "hub",     "country": "DE", "country_name": "Germany",      "tier": 2, "throughput_teu": 1000000},
    "berlin":        {"name": "Berlin",         "lat":  52.52, "lon":  13.40, "type": "hub",     "country": "DE", "country_name": "Germany",      "tier": 2, "throughput_teu": 800000},
    "london":        {"name": "London",         "lat":  51.51, "lon":  -0.13, "type": "hub",     "country": "GB", "country_name": "UK",           "tier": 1, "throughput_teu": 3500000},
    "felixstowe":    {"name": "Felixstowe",     "lat":  51.96, "lon":   1.35, "type": "port",    "country": "GB", "country_name": "UK",           "tier": 2, "throughput_teu": 4000000},
    "southampton":   {"name": "Southampton",    "lat":  50.90, "lon":  -1.40, "type": "port",    "country": "GB", "country_name": "UK",           "tier": 2, "throughput_teu": 1500000},
    "paris":         {"name": "Paris",          "lat":  48.85, "lon":   2.35, "type": "hub",     "country": "FR", "country_name": "France",       "tier": 1, "throughput_teu": 1000000},
    "le_havre":      {"name": "Le Havre",       "lat":  49.49, "lon":   0.11, "type": "port",    "country": "FR", "country_name": "France",       "tier": 2, "throughput_teu": 2700000},
    "marseille":     {"name": "Marseille",      "lat":  43.30, "lon":   5.37, "type": "port",    "country": "FR", "country_name": "France",       "tier": 2, "throughput_teu": 1400000},
    "amsterdam":     {"name": "Amsterdam",      "lat":  52.37, "lon":   4.90, "type": "hub",     "country": "NL", "country_name": "Netherlands",  "tier": 2, "throughput_teu": 500000},
    "brussels":      {"name": "Brussels",       "lat":  50.85, "lon":   4.35, "type": "hub",     "country": "BE", "country_name": "Belgium",      "tier": 2, "throughput_teu": 300000},
    "zurich":        {"name": "Zurich",         "lat":  47.38, "lon":   8.54, "type": "hub",     "country": "CH", "country_name": "Switzerland",  "tier": 2, "throughput_teu": 500000},
    "vienna":        {"name": "Vienna",         "lat":  48.21, "lon":  16.37, "type": "hub",     "country": "AT", "country_name": "Austria",      "tier": 2, "throughput_teu": 400000},
    "milan":         {"name": "Milan",          "lat":  45.46, "lon":   9.19, "type": "hub",     "country": "IT", "country_name": "Italy",        "tier": 2, "throughput_teu": 500000},
    "genoa":         {"name": "Genoa",          "lat":  44.41, "lon":   8.93, "type": "port",    "country": "IT", "country_name": "Italy",        "tier": 2, "throughput_teu": 1500000},
    "venice":        {"name": "Venice",         "lat":  45.44, "lon":  12.33, "type": "port",    "country": "IT", "country_name": "Italy",        "tier": 3, "throughput_teu": 400000},
    "barcelona":     {"name": "Barcelona",      "lat":  41.39, "lon":   2.16, "type": "port",    "country": "ES", "country_name": "Spain",        "tier": 2, "throughput_teu": 3400000},
    "madrid":        {"name": "Madrid",         "lat":  40.42, "lon":  -3.70, "type": "hub",     "country": "ES", "country_name": "Spain",        "tier": 2, "throughput_teu": 500000},
    "valencia":      {"name": "Valencia",       "lat":  39.47, "lon":  -0.38, "type": "port",    "country": "ES", "country_name": "Spain",        "tier": 2, "throughput_teu": 5800000},
    "algeciras":     {"name": "Algeciras",      "lat":  36.13, "lon":  -5.45, "type": "port",    "country": "ES", "country_name": "Spain",        "tier": 2, "throughput_teu": 5500000},
    "lisbon":        {"name": "Lisbon",         "lat":  38.72, "lon":  -9.14, "type": "port",    "country": "PT", "country_name": "Portugal",     "tier": 2, "throughput_teu": 650000},
    "stockholm":     {"name": "Stockholm",      "lat":  59.33, "lon":  18.07, "type": "hub",     "country": "SE", "country_name": "Sweden",       "tier": 2, "throughput_teu": 400000},
    "oslo":          {"name": "Oslo",           "lat":  59.91, "lon":  10.75, "type": "hub",     "country": "NO", "country_name": "Norway",       "tier": 3, "throughput_teu": 300000},
    "copenhagen":    {"name": "Copenhagen",     "lat":  55.68, "lon":  12.57, "type": "hub",     "country": "DK", "country_name": "Denmark",      "tier": 2, "throughput_teu": 600000},
    "helsinki":      {"name": "Helsinki",       "lat":  60.17, "lon":  24.94, "type": "hub",     "country": "FI", "country_name": "Finland",      "tier": 3, "throughput_teu": 400000},
    "athens":        {"name": "Athens",         "lat":  37.98, "lon":  23.73, "type": "hub",     "country": "GR", "country_name": "Greece",       "tier": 2, "throughput_teu": 500000},
    "piraeus":       {"name": "Piraeus",        "lat":  37.95, "lon":  23.63, "type": "port",    "country": "GR", "country_name": "Greece",       "tier": 2, "throughput_teu": 5000000},
    "istanbul":      {"name": "Istanbul",       "lat":  41.01, "lon":  28.96, "type": "hub",     "country": "TR", "country_name": "Turkey",       "tier": 1, "throughput_teu": 3000000},
    "izmir":         {"name": "Izmir",          "lat":  38.42, "lon":  27.14, "type": "port",    "country": "TR", "country_name": "Turkey",       "tier": 2, "throughput_teu": 1200000},
    "warsaw":        {"name": "Warsaw",         "lat":  52.23, "lon":  21.01, "type": "hub",     "country": "PL", "country_name": "Poland",       "tier": 2, "throughput_teu": 300000},
    "gdansk":        {"name": "Gdańsk",         "lat":  54.35, "lon":  18.65, "type": "port",    "country": "PL", "country_name": "Poland",       "tier": 2, "throughput_teu": 2000000},
    "prague":        {"name": "Prague",         "lat":  50.07, "lon":  14.44, "type": "hub",     "country": "CZ", "country_name": "Czech Republic","tier": 3, "throughput_teu": 200000},
    "budapest":      {"name": "Budapest",       "lat":  47.50, "lon":  19.04, "type": "hub",     "country": "HU", "country_name": "Hungary",      "tier": 3, "throughput_teu": 200000},
    "bucharest":     {"name": "Bucharest",      "lat":  44.43, "lon":  26.10, "type": "hub",     "country": "RO", "country_name": "Romania",      "tier": 3, "throughput_teu": 200000},
    "sofia":         {"name": "Sofia",          "lat":  42.70, "lon":  23.32, "type": "hub",     "country": "BG", "country_name": "Bulgaria",     "tier": 3, "throughput_teu": 100000},
    "kyiv":          {"name": "Kyiv",           "lat":  50.45, "lon":  30.52, "type": "hub",     "country": "UA", "country_name": "Ukraine",      "tier": 3, "throughput_teu": 200000},
    "riga":          {"name": "Riga",           "lat":  56.95, "lon":  24.11, "type": "port",    "country": "LV", "country_name": "Latvia",       "tier": 3, "throughput_teu": 300000},
    "tallinn":       {"name": "Tallinn",        "lat":  59.44, "lon":  24.75, "type": "port",    "country": "EE", "country_name": "Estonia",      "tier": 3, "throughput_teu": 200000},
    "saint_petersburg": {"name": "St. Petersburg","lat": 59.94, "lon": 30.32, "type": "port",   "country": "RU", "country_name": "Russia",       "tier": 2, "throughput_teu": 2500000},
    "moscow":        {"name": "Moscow",         "lat":  55.75, "lon":  37.62, "type": "hub",     "country": "RU", "country_name": "Russia",       "tier": 2, "throughput_teu": 1000000},
    "novosibirsk":   {"name": "Novosibirsk",    "lat":  54.99, "lon":  82.90, "type": "hub",     "country": "RU", "country_name": "Russia",       "tier": 3, "throughput_teu": 300000},
    "ekaterinburg":  {"name": "Ekaterinburg",   "lat":  56.84, "lon":  60.60, "type": "hub",     "country": "RU", "country_name": "Russia",       "tier": 3, "throughput_teu": 200000},
    # ── AFRICA ───────────────────────────────────────────────────────────
    "cairo":         {"name": "Cairo",          "lat":  30.04, "lon":  31.24, "type": "hub",     "country": "EG", "country_name": "Egypt",        "tier": 2, "throughput_teu": 1000000},
    "port_said":     {"name": "Port Said",      "lat":  31.26, "lon":  32.29, "type": "port",    "country": "EG", "country_name": "Egypt",        "tier": 2, "throughput_teu": 3500000},
    "alexandria":    {"name": "Alexandria",     "lat":  31.20, "lon":  29.92, "type": "port",    "country": "EG", "country_name": "Egypt",        "tier": 2, "throughput_teu": 1200000},
    "johannesburg":  {"name": "Johannesburg",   "lat": -26.20, "lon":  28.04, "type": "hub",     "country": "ZA", "country_name": "South Africa", "tier": 2, "throughput_teu": 1000000},
    "cape_town":     {"name": "Cape Town",      "lat": -33.93, "lon":  18.42, "type": "port",    "country": "ZA", "country_name": "South Africa", "tier": 2, "throughput_teu": 1000000},
    "durban":        {"name": "Durban",         "lat": -29.86, "lon":  31.02, "type": "port",    "country": "ZA", "country_name": "South Africa", "tier": 2, "throughput_teu": 2800000},
    "lagos":         {"name": "Lagos",          "lat":   6.45, "lon":   3.38, "type": "port",    "country": "NG", "country_name": "Nigeria",      "tier": 2, "throughput_teu": 900000},
    "accra":         {"name": "Accra",          "lat":   5.55, "lon":  -0.22, "type": "hub",     "country": "GH", "country_name": "Ghana",        "tier": 3, "throughput_teu": 400000},
    "abidjan":       {"name": "Abidjan",        "lat":   5.36, "lon":  -4.01, "type": "port",    "country": "CI", "country_name": "Ivory Coast",  "tier": 3, "throughput_teu": 700000},
    "dakar":         {"name": "Dakar",          "lat":  14.72, "lon": -17.47, "type": "port",    "country": "SN", "country_name": "Senegal",      "tier": 3, "throughput_teu": 400000},
    "casablanca":    {"name": "Casablanca",     "lat":  33.59, "lon":  -7.62, "type": "port",    "country": "MA", "country_name": "Morocco",      "tier": 2, "throughput_teu": 900000},
    "nairobi":       {"name": "Nairobi",        "lat":  -1.29, "lon":  36.82, "type": "hub",     "country": "KE", "country_name": "Kenya",        "tier": 2, "throughput_teu": 500000},
    "mombasa":       {"name": "Mombasa",        "lat":  -4.05, "lon":  39.67, "type": "port",    "country": "KE", "country_name": "Kenya",        "tier": 2, "throughput_teu": 1200000},
    "dar_es_salaam": {"name": "Dar es Salaam",  "lat":  -6.79, "lon":  39.28, "type": "port",    "country": "TZ", "country_name": "Tanzania",     "tier": 3, "throughput_teu": 900000},
    "addis_ababa":   {"name": "Addis Ababa",    "lat":   9.03, "lon":  38.74, "type": "hub",     "country": "ET", "country_name": "Ethiopia",     "tier": 3, "throughput_teu": 100000},
    "djibouti":      {"name": "Djibouti",       "lat":  11.59, "lon":  43.14, "type": "port",    "country": "DJ", "country_name": "Djibouti",     "tier": 3, "throughput_teu": 1000000},
    "luanda":        {"name": "Luanda",         "lat":  -8.84, "lon":  13.23, "type": "port",    "country": "AO", "country_name": "Angola",       "tier": 3, "throughput_teu": 500000},
    "maputo":        {"name": "Maputo",         "lat": -25.97, "lon":  32.57, "type": "port",    "country": "MZ", "country_name": "Mozambique",   "tier": 3, "throughput_teu": 300000},
    "tunis":         {"name": "Tunis",          "lat":  36.82, "lon":  10.17, "type": "hub",     "country": "TN", "country_name": "Tunisia",      "tier": 3, "throughput_teu": 200000},
    "tripoli":       {"name": "Tripoli",        "lat":  32.90, "lon":  13.18, "type": "port",    "country": "LY", "country_name": "Libya",        "tier": 3, "throughput_teu": 200000},
    # ── NORTH AMERICA ────────────────────────────────────────────────────
    "new_york":      {"name": "New York",       "lat":  40.71, "lon": -74.01, "type": "hub",     "country": "US", "country_name": "USA",          "tier": 1, "throughput_teu": 7200000},
    "los_angeles":   {"name": "Los Angeles",    "lat":  34.05, "lon":-118.24, "type": "port",    "country": "US", "country_name": "USA",          "tier": 1, "throughput_teu": 9400000},
    "chicago":       {"name": "Chicago",        "lat":  41.88, "lon": -87.63, "type": "hub",     "country": "US", "country_name": "USA",          "tier": 1, "throughput_teu": 3000000},
    "houston":       {"name": "Houston",        "lat":  29.76, "lon": -95.37, "type": "port",    "country": "US", "country_name": "USA",          "tier": 1, "throughput_teu": 2900000},
    "savannah":      {"name": "Savannah",       "lat":  32.08, "lon": -81.10, "type": "port",    "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 5800000},
    "long_beach":    {"name": "Long Beach",     "lat":  33.77, "lon":-118.19, "type": "port",    "country": "US", "country_name": "USA",          "tier": 1, "throughput_teu": 9200000},
    "seattle":       {"name": "Seattle",        "lat":  47.61, "lon":-122.33, "type": "port",    "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 3500000},
    "miami":         {"name": "Miami",          "lat":  25.77, "lon": -80.19, "type": "port",    "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 1100000},
    "dallas":        {"name": "Dallas",         "lat":  32.78, "lon": -96.80, "type": "hub",     "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 500000},
    "atlanta":       {"name": "Atlanta",        "lat":  33.75, "lon": -84.39, "type": "hub",     "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 500000},
    "baltimore":     {"name": "Baltimore",      "lat":  39.29, "lon": -76.61, "type": "port",    "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 850000},
    "norfolk":       {"name": "Norfolk",        "lat":  36.85, "lon": -76.29, "type": "port",    "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 2700000},
    "vancouver":     {"name": "Vancouver",      "lat":  49.25, "lon":-123.12, "type": "port",    "country": "CA", "country_name": "Canada",       "tier": 2, "throughput_teu": 3600000},
    "toronto":       {"name": "Toronto",        "lat":  43.65, "lon": -79.38, "type": "hub",     "country": "CA", "country_name": "Canada",       "tier": 2, "throughput_teu": 500000},
    "montreal":      {"name": "Montreal",       "lat":  45.50, "lon": -73.57, "type": "port",    "country": "CA", "country_name": "Canada",       "tier": 2, "throughput_teu": 1500000},
    "mexico_city":   {"name": "Mexico City",    "lat":  19.43, "lon": -99.13, "type": "hub",     "country": "MX", "country_name": "Mexico",       "tier": 2, "throughput_teu": 500000},
    "manzanillo_mx": {"name": "Manzanillo MX",  "lat":  19.05, "lon":-104.31, "type": "port",    "country": "MX", "country_name": "Mexico",       "tier": 2, "throughput_teu": 3200000},
    "veracruz":      {"name": "Veracruz",       "lat":  19.18, "lon": -96.16, "type": "port",    "country": "MX", "country_name": "Mexico",       "tier": 2, "throughput_teu": 1400000},
    "panama_city":   {"name": "Panama City",    "lat":   8.99, "lon": -79.52, "type": "hub",     "country": "PA", "country_name": "Panama",       "tier": 2, "throughput_teu": 6500000},
    "colon":         {"name": "Colón",          "lat":   9.36, "lon": -79.90, "type": "port",    "country": "PA", "country_name": "Panama",       "tier": 2, "throughput_teu": 4000000},
    "havana":        {"name": "Havana",         "lat":  23.14, "lon": -82.36, "type": "port",    "country": "CU", "country_name": "Cuba",         "tier": 3, "throughput_teu": 200000},
    "kingston":      {"name": "Kingston",       "lat":  17.99, "lon": -76.79, "type": "port",    "country": "JM", "country_name": "Jamaica",      "tier": 2, "throughput_teu": 1600000},
    # ── SOUTH AMERICA ────────────────────────────────────────────────────
    "sao_paulo":     {"name": "São Paulo",      "lat": -23.55, "lon": -46.63, "type": "hub",     "country": "BR", "country_name": "Brazil",       "tier": 1, "throughput_teu": 2000000},
    "santos":        {"name": "Santos",         "lat": -23.93, "lon": -46.33, "type": "port",    "country": "BR", "country_name": "Brazil",       "tier": 1, "throughput_teu": 4200000},
    "rio_de_janeiro":{"name": "Rio de Janeiro", "lat": -22.91, "lon": -43.17, "type": "hub",     "country": "BR", "country_name": "Brazil",       "tier": 2, "throughput_teu": 1000000},
    "buenos_aires":  {"name": "Buenos Aires",   "lat": -34.60, "lon": -58.38, "type": "port",    "country": "AR", "country_name": "Argentina",    "tier": 2, "throughput_teu": 1500000},
    "santiago":      {"name": "Santiago",       "lat": -33.46, "lon": -70.65, "type": "hub",     "country": "CL", "country_name": "Chile",        "tier": 2, "throughput_teu": 500000},
    "valparaiso":    {"name": "Valparaíso",     "lat": -33.05, "lon": -71.62, "type": "port",    "country": "CL", "country_name": "Chile",        "tier": 2, "throughput_teu": 1000000},
    "lima":          {"name": "Lima",           "lat": -12.05, "lon": -77.04, "type": "hub",     "country": "PE", "country_name": "Peru",         "tier": 2, "throughput_teu": 500000},
    "callao":        {"name": "Callao",         "lat": -12.06, "lon": -77.15, "type": "port",    "country": "PE", "country_name": "Peru",         "tier": 2, "throughput_teu": 2400000},
    "bogota":        {"name": "Bogotá",         "lat":   4.71, "lon": -74.07, "type": "hub",     "country": "CO", "country_name": "Colombia",     "tier": 2, "throughput_teu": 200000},
    "cartagena_co":  {"name": "Cartagena CO",   "lat":  10.39, "lon": -75.51, "type": "port",    "country": "CO", "country_name": "Colombia",     "tier": 2, "throughput_teu": 2800000},
    "guayaquil":     {"name": "Guayaquil",      "lat":  -2.20, "lon": -79.90, "type": "port",    "country": "EC", "country_name": "Ecuador",      "tier": 3, "throughput_teu": 900000},
    "caracas":       {"name": "Caracas",        "lat":  10.48, "lon": -66.88, "type": "hub",     "country": "VE", "country_name": "Venezuela",    "tier": 3, "throughput_teu": 200000},
    "montevideo":    {"name": "Montevideo",     "lat": -34.90, "lon": -56.19, "type": "port",    "country": "UY", "country_name": "Uruguay",      "tier": 3, "throughput_teu": 750000},
    # ── OCEANIA ──────────────────────────────────────────────────────────
    "sydney":        {"name": "Sydney",         "lat": -33.87, "lon": 151.21, "type": "port",    "country": "AU", "country_name": "Australia",    "tier": 1, "throughput_teu": 2600000},
    "melbourne":     {"name": "Melbourne",      "lat": -37.81, "lon": 144.96, "type": "port",    "country": "AU", "country_name": "Australia",    "tier": 2, "throughput_teu": 2900000},
    "brisbane":      {"name": "Brisbane",       "lat": -27.47, "lon": 153.03, "type": "port",    "country": "AU", "country_name": "Australia",    "tier": 2, "throughput_teu": 1200000},
    "fremantle":     {"name": "Fremantle",      "lat": -32.05, "lon": 115.74, "type": "port",    "country": "AU", "country_name": "Australia",    "tier": 2, "throughput_teu": 750000},
    "auckland":      {"name": "Auckland",       "lat": -36.86, "lon": 174.77, "type": "port",    "country": "NZ", "country_name": "New Zealand",  "tier": 2, "throughput_teu": 900000},
    "port_moresby":  {"name": "Port Moresby",   "lat":  -9.44, "lon": 147.18, "type": "hub",     "country": "PG", "country_name": "Papua New Guinea","tier": 3, "throughput_teu": 100000},
    "suva":          {"name": "Suva",           "lat": -18.14, "lon": 178.44, "type": "port",    "country": "FJ", "country_name": "Fiji",         "tier": 3, "throughput_teu": 80000},
    "honolulu":      {"name": "Honolulu",       "lat":  21.31, "lon":-157.86, "type": "port",    "country": "US", "country_name": "USA",          "tier": 2, "throughput_teu": 800000},
    "anchorage":     {"name": "Anchorage",      "lat":  61.22, "lon":-149.90, "type": "hub",     "country": "US", "country_name": "USA",          "tier": 3, "throughput_teu": 200000},
    # ── EXTRA STRATEGIC ──────────────────────────────────────────────────
    "suez":          {"name": "Suez",           "lat":  29.97, "lon":  32.55, "type": "hub",     "country": "EG", "country_name": "Egypt",        "tier": 2, "throughput_teu": 500000},
    "aden":          {"name": "Aden",           "lat":  12.78, "lon":  45.04, "type": "port",    "country": "YE", "country_name": "Yemen",        "tier": 3, "throughput_teu": 600000},
    "colombo_ftz":   {"name": "Colombo FTZ",    "lat":   6.95, "lon":  79.87, "type": "port",    "country": "LK", "country_name": "Sri Lanka",    "tier": 3, "throughput_teu": 500000},
    "mombasa_kpa":   {"name": "Mombasa KPA",    "lat":  -4.06, "lon":  39.66, "type": "port",    "country": "KE", "country_name": "Kenya",        "tier": 3, "throughput_teu": 300000},
    "tanger_med":    {"name": "Tanger Med",     "lat":  35.88, "lon":  -5.50, "type": "port",    "country": "MA", "country_name": "Morocco",      "tier": 2, "throughput_teu": 7000000},
    "salalah":       {"name": "Salalah",        "lat":  17.02, "lon":  54.09, "type": "port",    "country": "OM", "country_name": "Oman",         "tier": 2, "throughput_teu": 4000000},
    "bandar_abbas":  {"name": "Bandar Abbas",   "lat":  27.19, "lon":  56.27, "type": "port",    "country": "IR", "country_name": "Iran",         "tier": 2, "throughput_teu": 2200000},
    "haifa":         {"name": "Haifa",          "lat":  32.82, "lon":  34.99, "type": "port",    "country": "IL", "country_name": "Israel",       "tier": 2, "throughput_teu": 1500000},
    "beirut":        {"name": "Beirut",         "lat":  33.89, "lon":  35.50, "type": "port",    "country": "LB", "country_name": "Lebanon",      "tier": 3, "throughput_teu": 800000},
    "tartus":        {"name": "Tartus",         "lat":  34.89, "lon":  35.89, "type": "port",    "country": "SY", "country_name": "Syria",        "tier": 3, "throughput_teu": 200000},
}


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Proximity-based auto-edge generation
# ---------------------------------------------------------------------------
# Thresholds for connecting hubs by mode
AIR_MAX_KM   = 14000  # any two hubs connected by air up to 14,000 km
SEA_MAX_KM   = 22000  # ports connected by sea up to 22,000 km
RAIL_MAX_KM  =  3500  # hubs in same/adjacent countries up to 3,500 km (land)
ROAD_MAX_KM  =  1200  # hubs within 1,200 km by road

# Thinning factor: only connect to N nearest neighbours per mode (keeps graph manageable)
AIR_TOP_N   = 12
SEA_TOP_N   = 10
RAIL_TOP_N  = 6
ROAD_TOP_N  = 4

# Continents for rail/road eligibility (only same-continent land routes)
_CONTINENT = {
    "CN": "asia", "HK": "asia", "TW": "asia", "JP": "asia", "KR": "asia",
    "VN": "asia", "PH": "asia", "TH": "asia", "ID": "asia", "MY": "asia",
    "SG": "asia", "MM": "asia", "KH": "asia", "IN": "asia", "PK": "asia",
    "LK": "asia", "BD": "asia", "NP": "asia", "AE": "asia", "SA": "asia",
    "OM": "asia", "KW": "asia", "QA": "asia", "BH": "asia", "IR": "asia",
    "IQ": "asia", "KZ": "asia", "UZ": "asia", "IL": "asia", "LB": "asia",
    "SY": "asia", "YE": "asia", "DJ": "asia",
    "RU": "eurasia",
    "NL": "europe", "BE": "europe", "DE": "europe", "GB": "europe",
    "FR": "europe", "CH": "europe", "AT": "europe", "IT": "europe",
    "ES": "europe", "PT": "europe", "SE": "europe", "NO": "europe",
    "DK": "europe", "FI": "europe", "GR": "europe", "TR": "europe",
    "PL": "europe", "CZ": "europe", "HU": "europe", "RO": "europe",
    "BG": "europe", "UA": "europe", "LV": "europe", "EE": "europe",
    "MA": "africa",
    "EG": "africa", "TN": "africa", "LY": "africa",
    "ZA": "africa", "NG": "africa", "GH": "africa", "CI": "africa",
    "SN": "africa", "KE": "africa", "TZ": "africa", "ET": "africa",
    "AO": "africa", "MZ": "africa",
    "US": "namerica", "CA": "namerica", "MX": "namerica",
    "PA": "namerica", "CU": "namerica", "JM": "namerica",
    "BR": "samerica", "AR": "samerica", "CL": "samerica",
    "PE": "samerica", "CO": "samerica", "EC": "samerica",
    "VE": "samerica", "UY": "samerica",
    "AU": "oceania", "NZ": "oceania", "PG": "oceania", "FJ": "oceania",
}

_LAND_CONTINENTS = {"europe", "asia", "eurasia", "namerica", "samerica", "africa"}


def build_edges():
    """
    Auto-generate edges based on proximity and node type:
      - Air: all node pairs within AIR_MAX_KM, top N neighbours each
      - Sea: port-to-port pairs within SEA_MAX_KM, top N neighbours each
      - Rail: land hubs same continent within RAIL_MAX_KM, top N neighbours each
      - Road: very close hubs same continent within ROAD_MAX_KM, top N neighbours each
    """
    node_ids = list(NODES.keys())
    # Pre-compute all pairwise distances
    dist_cache = {}
    for a, b in itertools.combinations(node_ids, 2):
        na, nb = NODES[a], NODES[b]
        d = _haversine_km(na["lat"], na["lon"], nb["lat"], nb["lon"])
        dist_cache[(a, b)] = dist_cache[(b, a)] = d

    edges_set = {}  # key: (from, to, mode) → edge dict

    def add_edge(f, t, mode):
        d = dist_cache[(f, t)]
        key = (f, t, mode)
        if key not in edges_set:
            speed = MODE_SPEED[mode]
            cpm   = MODE_COST_KM[mode]
            edges_set[key] = {
                "id":       f"{f}__{t}__{mode}",
                "from":     f,
                "to":       t,
                "distance": round(d),
                "time":     round(d / speed, 3),
                "mode":     mode,
                "cost":     round(d * cpm, 2),
            }

    for nid in node_ids:
        node = NODES[nid]
        cont = _CONTINENT.get(node["country"], "other")

        # ── AIR ──
        neighbours = sorted([
            (dist_cache[(nid, o)], o) for o in node_ids if o != nid
            and dist_cache[(nid, o)] <= AIR_MAX_KM
        ])[:AIR_TOP_N]
        for _, oid in neighbours:
            add_edge(nid, oid, "air")
            add_edge(oid, nid, "air")

        # ── SEA ──  (ports only)
        if node["type"] in ("port",):
            sea_nbrs = sorted([
                (dist_cache[(nid, o)], o)
                for o in node_ids if o != nid
                and NODES[o]["type"] == "port"
                and dist_cache[(nid, o)] <= SEA_MAX_KM
            ])[:SEA_TOP_N]
            for _, oid in sea_nbrs:
                add_edge(nid, oid, "sea")
                add_edge(oid, nid, "sea")

        # ── RAIL ──  (same continent, land)
        if cont in _LAND_CONTINENTS:
            rail_nbrs = sorted([
                (dist_cache[(nid, o)], o)
                for o in node_ids if o != nid
                and _CONTINENT.get(NODES[o]["country"], "other") in _LAND_CONTINENTS
                and (_CONTINENT.get(NODES[o]["country"], "other") == cont
                     or cont == "eurasia"
                     or _CONTINENT.get(NODES[o]["country"], "other") == "eurasia")
                and dist_cache[(nid, o)] <= RAIL_MAX_KM
            ])[:RAIL_TOP_N]
            for _, oid in rail_nbrs:
                add_edge(nid, oid, "rail")
                add_edge(oid, nid, "rail")

        # ── ROAD ──  (very close, same continent)
        if cont in _LAND_CONTINENTS:
            road_nbrs = sorted([
                (dist_cache[(nid, o)], o)
                for o in node_ids if o != nid
                and _CONTINENT.get(NODES[o]["country"], "other") == cont
                and dist_cache[(nid, o)] <= ROAD_MAX_KM
            ])[:ROAD_TOP_N]
            for _, oid in road_nbrs:
                add_edge(nid, oid, "road")
                add_edge(oid, nid, "road")

    return list(edges_set.values())


# Build at module import (cached)
EDGES = build_edges()


# ---------------------------------------------------------------------------
class LogisticsGraph:
    def __init__(self):
        self.nodes = NODES
        self.edges = EDGES
        self._adj  = self._build_adj(EDGES)

    @staticmethod
    def _build_adj(edges):
        adj = {n: [] for n in NODES}
        for e in edges:
            adj[e["from"]].append(e)
        return adj

    def haversine(self, n1: str, n2: str) -> float:
        """Great-circle distance in km between two node IDs."""
        na, nb = self.nodes[n1], self.nodes[n2]
        return _haversine_km(na["lat"], na["lon"], nb["lat"], nb["lon"])

    def effective_edges(self, constraint_engine):
        """Return edge dicts with eff_time / eff_cost factoring in constraints."""
        eff = []
        for e in self.edges:
            w_mult  = constraint_engine.weather_multiplier(e["to"])
            tr_mult = constraint_engine.traffic_multiplier(e["from"], e["to"])
            cust_h  = constraint_engine.customs_delay(e["to"])
            ee = dict(e)
            ee["eff_time"] = round(e["time"] * w_mult * tr_mult + cust_h, 4)
            ee["eff_cost"] = round(e["cost"] * w_mult * tr_mult, 2)
            eff.append(ee)
        return eff

    def adj_with_constraints(self, constraint_engine):
        """Adjacency list keyed by from-node, using effective weights."""
        adj = {n: [] for n in self.nodes}
        for e in self.effective_edges(constraint_engine):
            adj[e["from"]].append(e)
        return adj
