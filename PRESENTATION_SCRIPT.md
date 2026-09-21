# ACECQA Service Quality, Accessibility & Operations Analysis — Presentation Script

Target length: ~9:30, inside the assignment's hard 5–10 minute window
(content beyond 10 minutes isn't marked, so there's no benefit to
running long). `[SHOW ...]` marks when to bring up each chart; keep your
face visible in a corner the whole time per the assignment requirement.

With 13 charts across three streams, this script keeps each chart to
2–3 sentences. If you're running over on a practice read, see **"If
you need to cut time"** at the end — some charts can be shown without
being individually narrated and it still satisfies the assignment's
minimum (4+ visualisations, one spatial).

---

### Opening (0:00–0:30)

[Face to camera, no slide yet, or title slide]

"Hi, I'm [YOUR NAME], and I work for government to improve education and
care services across Australia. Today I want to walk you through an
analysis of the national register of approved education and care
services — over seventeen thousand services across every state and
territory — covering three things: where quality is falling short and
why, where families are genuinely underserved, and what the operational
data tells us about how the sector actually runs. Every finding here
points to something ACECQA, a state regulator, or a transport planner
could act on."

### Data & method, briefly (0:30–1:00)

[SHOW a slide with the dataset summary, or talk over the title slide]

"Quickly on the data: this is the NQA ITS extract — every approved
service, its ratings across seven quality areas, and location data
enriched with distance to the nearest train and bus station. Before
trusting any of it, I checked it for problems. Ten services had no
address at all, and had all been geocoded to the exact same point — in
Myanmar. I dropped those. Everything else checked out, including some
genuinely extreme values, like services on Torres Strait islands nine
hundred kilometres from the nearest train station — real, not errors,
but flagged so they don't distort the charts where they'd otherwise
dominate."

---

## Stream 1: Service Quality (1:00–3:15)

### Chart 1 — Rating by state (1:00–1:40)

[SHOW 01_rating_by_state.png]

"First: how does quality vary by state? All states apply the same
National Law, so we'd hope for similar outcomes. We don't see that. The
ACT has the highest share of services rated Exceeding NQS or above —
forty-four percent. Western Australia has the lowest, at four percent.
That's roughly a ten-times gap between two jurisdictions running the
same regulatory framework."

### Chart 2 — Rating by service type (1:40–2:05)

[SHOW 02_rating_by_service_type.png]

"Quality also splits by service type. Standalone and school-based
preschools lead, at fifty and forty-six percent Exceeding. Long Day Care
and Outside School Hours Care trail at eighteen and eleven percent — and
Long Day Care is the largest category in the whole dataset, so that's
where the biggest improvement opportunity sits."

### Chart 3 — Which Quality Area drags states down (2:05–2:35)

[SHOW 03_quality_area_heatmap.png]

"Breaking the overall score into its seven components, Quality Area
2 — children's health and safety — is the weakest area nationally, and
especially weak in WA and the Northern Territory, the same two
jurisdictions from the first chart. That's a concrete, area-specific
lever, not a vague 'improve quality' message."

### Chart 4 — Spatial map of ratings (2:35–2:55)

[SHOW 04_spatial_ratings_map.png]

"Mapping every service by rating shows where issues cluster
geographically — concentrations of orange, Working Towards NQS, around
Perth, Adelaide, and pockets of the eastern seaboard. That's local
enough to target a support team at, rather than spreading resources
across an entire state."

### Chart 5 — Transport proximity vs. quality (2:55–3:35)

[SHOW 05_transport_vs_quality.png]

"One hypothesis: does being close to public transport correlate with
better quality? I tested it with a Spearman correlation, excluding the
extreme remote outliers. The answer is no — the correlation is
essentially zero. It's technically significant only because we have
sixteen thousand data points; the effect size is negligible. That's a
useful finding on its own: don't treat transport proximity as a quality
signal. It isn't one."

---

## Stream 2: Accessibility & Coverage (3:35–5:45)

"So transport doesn't predict quality directly. But it might still
matter for whether families can reach a service at all — which is the
second half of this analysis. I classified every service urban or rural
using the ABS's Section of State boundaries, spatially joined against
each service's own coordinates."

### Chart 6 — Transport access, urban vs rural (3:45–4:15)

[SHOW 06_transport_by_urban_rural.png]

"Here the story flips. Rural services sit a median of nineteen
kilometres from the nearest train station, against two-point-three
kilometres for urban services — eight times further. For a family
without a car in a rural area, that's a real barrier to using the
service, not a statistic."

### Chart 7 — Quality, urban vs rural (4:15–4:40)

[SHOW 07_rating_by_urban_rural.png]

"And unlike raw distance, urban-versus-rural classification does track
with quality — twenty-two percent of urban services rated Exceeding or
above, against seventeen percent rural. Smaller than the state-level
gap, but real."

### Chart 8 — Spatial map, urban vs rural (4:40–5:00)

[SHOW 08_spatial_urban_rural.png]

"Mapping urban and rural services together shows how concentrated
Australia's early education footprint is — the overwhelming majority
sit in a thin coastal band, with a long tail of small services scattered
across the interior and the north."

### Chart 9 — Coverage gaps: where's the nearest alternative? (5:00–5:45)

[SHOW 09_coverage_gaps.png]

"Last accessibility question: where are families most underserved? Land
density isn't useful here — most of inland Australia is uninhabited. A
better measure: for each service, how far is the *next closest* one — the
fallback if a family's usual centre is full. Western Australia's smaller
rural towns sit at a median forty-one kilometres to the next service; the
Northern Territory's equivalent, thirty-one kilometres. Every other
state-and-area combination is under fifteen. That's not a gradual
disparity, it's an order-of-magnitude gap — and it's exactly where a new
service would have the most impact."

---

## Stream 3: Operational Trends (5:45–8:15)

"Last stream: what does the operational data — capacity, hours, and
approval dates — tell us about how the sector actually runs, and whether
any of that connects back to quality or transport?"

### Chart 10 — Capacity by service type (5:55–6:20)

[SHOW 10_capacity_by_type.png]

"Long Day Care centres are the biggest, with a median of seventy-two
approved places; standalone preschools the smallest, at thirty-two.
Location matters too: urban services run at a median sixty-two places,
rural services just thirty — about half the size, which tracks with
smaller communities needing smaller centres."

### Chart 11 — Year-round vs term-time operation (6:20–6:50)

[SHOW 11_operating_pattern_by_type.png]

"Service types also split structurally in how they operate. Long Day
Care and Family Day Care run essentially year-round — ninety-eight and
eighty-eight percent. Preschools and Outside School Hours Care are
overwhelmingly term-time only, up to eighty-four percent for OSHC. That's
not a quality difference, it's a structural one worth knowing before
comparing these service types on anything operational."

### Chart 12 — Approval trend over time (6:50–7:20)

[SHOW 12_approval_trend.png]

"Here's a data-quality catch worth flagging to any policy audience: 2012
shows a huge spike in approvals — over four thousand in one year. That's
not organic growth. The National Quality Framework commenced in January
2012, and every already-operating service was bulk-transferred onto new
approval numbers that year. The real growth signal is the steadier trend
from 2013 onward — reading the raw spike as sector expansion would be a
mistake."

### Chart 13 — Operational factors, quality, and transport (7:20–8:10)

[SHOW 13_hours_vs_quality.png]

"Finally: do operational factors relate to quality? Services open under
forty-five hours a week have the highest Exceeding rate, at thirty-seven
percent; that falls as hours climb, down to about eighteen percent for
the longest-opening services. It's a modest correlation, but the largest
operational effect I found — possibly reflecting staffing strain across a
longer working week. And echoing the transport-quality result from
earlier: transport accessibility doesn't meaningfully move capacity or
opening hours either. Whatever's driving quality and operational
differences, it isn't how close a service is to a train station."

---

### Close & recommendations (8:10–8:50)

[Face to camera, optional summary slide]

"Bringing this together, three recommendations. One: ACECQA's cross-state
consistency work should prioritise Western Australia and the Northern
Territory, specifically children's health-and-safety practices, since
that's the weakest area dragging both down. Two: don't use transport
proximity as a quality or operational proxy — it isn't one — but do treat
it as an equity issue, since rural families face meaningfully worse
transport access regardless of service quality or size. And three: if
new services are being funded, Western Australia's and the Northern
Territory's rural towns are the most concrete, defensible place to
start, based on how far families there already have to travel for an
alternative. Thank you."

---

## Delivery notes

- Full script reads at roughly 140–160 words/minute, landing at about
  9:30 with normal pacing and pauses — leaves a buffer under the 10-minute
  hard cap, but practice once and trim if you're a slower reader.
- **If you need to cut time:** the safest cuts, in order, are (1) the
  "Data & method" paragraph — mention the Myanmar catch in one sentence
  instead, (2) Chart 8 (spatial urban/rural) — show it during the Chart 9
  narration instead of giving it its own beat, (3) Chart 2 (rating by
  service type) — one sentence instead of two. Don't cut Chart 5 or
  Chart 13's transport-null findings; they're your strongest "we tested
  this properly" evidence for a policy audience.
- If asked why urban/rural wasn't done with the simpler
  postcode-allocation method: you used the direct spatial join since the
  dataset already has coordinates for every service, avoiding the
  many-to-many postcode-to-SA1 mapping problem entirely.
- Keep the Family Day Care data-quality catches (capacity populated for
  only 2 of 417 services; "hours" meaning something structurally
  different for a scheme vs a single centre) in your back pocket for
  Q&A even if you don't narrate them in the timed script.
