# ACECQA Service Quality & Accessibility Analysis — Presentation Script

Target length: ~8 minutes (fits the 5–10 minute window with buffer for
pauses/breathing). Timings are approximate — practice once and adjust.
`[SHOW ...]` marks when to bring up each chart on screen; keep your face
visible in a corner the whole time per the assignment requirement.

---

### Opening (0:00–0:30)

[Face to camera, no slide yet, or title slide]

"Hi, I'm [YOUR NAME], and I work for government to improve education and
care services across Australia. Today I want to walk you through an
analysis of the national register of approved education and care
services — over seventeen thousand services across every state and
territory — and show you three things: where quality is falling short,
whether transport access has anything to do with it, and where families
are genuinely underserved. This isn't just a data exercise — every
finding here points to a specific decision ACECQA, state regulators, or
transport planners could act on."

---

### Data & method, briefly (0:30–1:05)

[SHOW a slide with the dataset summary or just talk over title slide]

"Quickly on the data: this is the NQA ITS extract — every approved
service, its National Quality Standard ratings across seven quality
areas, and location data enriched with distance to the nearest train and
bus station. Before trusting any of it, I checked it for problems. I
found ten services that had no address information at all, and had all
been geocoded to the exact same point — in Myanmar, not Australia. I
dropped those ten rows rather than guessing where they actually are.
Everything else checked out, including some genuinely extreme values,
like services on Torres Strait islands nine hundred kilometres from the
nearest train station — real, not errors, so I kept those but flagged
them for the charts where they'd otherwise distort the picture."

---

## Stream 1: Service Quality

### Chart 1 — Rating by state (1:05–2:00)

[SHOW 01_rating_by_state.png]

"First question: how does quality vary by state? All states apply the
same National Law, so we'd hope for similar outcomes. We don't see that.
The ACT has the highest share of services rated Exceeding NQS or
above — forty-four percent. Western Australia has the lowest, at just
four percent. That's roughly a ten-times gap between two jurisdictions
running the same regulatory framework. South Australia and Victoria sit
in the upper-middle, while WA, the Northern Territory, and Queensland
trail. That's not a criticism of any one state's services — it's a
signal that either assessment practices, resourcing, or support programs
differ significantly by jurisdiction, and that's worth ACECQA's
attention in its cross-state consistency work."

### Chart 2 — Rating by service type (2:00–2:40)

[SHOW 02_rating_by_service_type.png]

"Quality also varies by what kind of service we're looking at. Standalone
preschools and school-based preschools have the highest share of
Exceeding ratings — over fifty and forty-six percent respectively. Long
Day Care and Outside School Hours Care trail well behind, at eighteen and
eleven percent. That's useful for targeting: if ACECQA wants to lift the
national exceeding-rate, Long Day Care is where the bulk of services sit,
and where the improvement opportunity is largest."

### Chart 3 — Which Quality Area drags states down (2:40–3:25)

[SHOW 03_quality_area_heatmap.png]

"A single overall rating hides which of the seven quality areas is
actually the problem. Breaking it down, Quality Area 2 — children's
health and safety — is the weakest area nationally, and it's especially
weak in Western Australia and the Northern Territory, the same two
jurisdictions from our first chart. Quality Area 6, collaborative
partnerships with families, is consistently the strongest. This gives
regulators something concrete: WA and NT's improvement plans should
probably start with health and safety practices specifically, not a
generic 'lift your quality' message."

### Chart 4 — Spatial map of ratings (3:25–4:05)

[SHOW 04_spatial_ratings_map.png]

"Mapping every service by its rating shows where quality issues cluster
geographically. You can see concentrations of orange — Working Towards
NQS — around Perth, Adelaide, and pockets of the eastern seaboard. This
isn't just a state-level story; it's local enough that a regional support
team could be deployed to these specific clusters rather than spreading
resources evenly across an entire state."

### Chart 5 — Transport proximity vs. quality (4:05–5:00)

[SHOW 05_transport_vs_quality.png]

"One hypothesis worth testing: does being close to public transport
correlate with better quality — maybe because well-connected services
attract more staff or families, creating pressure to perform? I tested
this with a Spearman correlation between distance to the nearest train
station and rating, excluding the handful of extremely remote outliers
so they don't distort the result. The answer is no. The correlation is
essentially zero — the share of services rated Exceeding sits at roughly
twenty to twenty-two percent whether a service is fifty metres or fifty
kilometres from a station. It is technically statistically significant,
because we have sixteen thousand data points, but the effect size is
negligible. That's actually a useful finding: ACECQA and transport
planners shouldn't treat proximity to transport as a quality signal —
it isn't one. Whatever's driving the quality gaps we just saw, it's not
transport access."

---

## Stream 2: Accessibility & Coverage

"So transport doesn't predict quality directly. But it might still matter
for a different reason: whether families can physically reach a service
at all. That's the second half of this analysis. To dig into this
properly, I classified every service as urban or rural using the
Australian Bureau of Statistics' Section of State boundaries — spatially
joining each service's coordinates against the ABS's own polygons."

### Chart 6 — Transport access, urban vs rural (5:00–5:40)

[SHOW 06_transport_by_urban_rural.png]

"And here the story flips. While raw distance-to-station didn't predict
quality, the urban/rural split is stark on its own terms. Rural services
sit a median of nineteen kilometres from the nearest train station,
against two point three kilometres for urban services — roughly eight
times further. Bus access shows the same pattern, roughly four times
further. For a family without a car in a rural area, that's not a
statistic, that's a real barrier to using the service at all."

### Chart 7 — Quality, urban vs rural (5:40–6:15)

[SHOW 07_rating_by_urban_rural.png]

"And unlike raw distance, urban versus rural classification does track
with quality. Twenty-two percent of urban services are rated Exceeding
or above, against seventeen percent of rural services. It's a smaller
gap than the state-level differences we saw earlier, but it's real, and
it suggests rural services may be working with less access to
professional development, relief staff, or peer networks — all harder
to access outside major population centres."

### Chart 8 — Spatial map, urban vs rural (6:15–6:45)

[SHOW 08_spatial_urban_rural.png]

"Mapping urban and rural services together shows how concentrated
Australia's early education footprint really is — the overwhelming
majority of services sit in a thin band along the coast, with a long
tail of small rural and remote services scattered across the interior
and the north."

### Chart 9 — Coverage gaps: where's the nearest alternative? (6:45–7:40)

[SHOW 09_coverage_gaps.png]

"Last question: where are families most underserved? Land-area density
isn't a useful measure here — most of inland Australia is uninhabited, so
of course it has few services per square kilometre. A more meaningful
measure is: for each service, how far away is the *next closest*
service — the fallback if a family's usual centre is full or closes.
Breaking that down by state and by area type, two results jump out.
Western Australia's smaller rural towns — what the ABS calls 'Bounded
Localities' — have a median of forty-one kilometres to the next nearest
service. The Northern Territory's equivalent areas sit at thirty-one
kilometres. Every other state-and-area combination is under fifteen
kilometres, most under five. That's not a gradual disparity — it's an
order-of-magnitude gap, and it points to exactly where a new service
would have the most impact if ACECQA or a state government were choosing
where to invest."

---

### Close & recommendations (7:40–8:15)

[Face to camera, optional summary slide]

"To bring this together: three recommendations. One, ACECQA's
cross-state consistency work should prioritise Western Australia and the
Northern Territory, and specifically their children's health-and-safety
practices, since that's the weakest quality area dragging both down.
Two, don't use transport proximity as a quality proxy — it isn't one —
but do treat it as an equity issue, since rural families face
meaningfully worse transport access regardless of service quality.
And three, if new services are being funded, Western Australia's and the
Northern Territory's rural towns are the most concrete, defensible place
to start, based on how far families there already have to travel for an
alternative. Thank you."

---

## Delivery notes

- Full script reads at roughly 130–150 words/minute, comfortably inside
  8 minutes; if you're running long, the "Data & method" section and the
  transport-proximity null result are the easiest to trim without losing
  the throughline.
- If you're asked (or want to pre-empt a question) about why urban/rural
  wasn't done with the simpler postcode-allocation method: mention you
  used the direct spatial join since the dataset already has coordinates
  for every service, avoiding the many-to-many postcode-to-SA1 mapping
  problem entirely.
- Keep the Myanmar-geocode data-quality story in your back pocket even if
  you cut it from the timed script — it's a strong, concrete example if
  asked "how did you handle data quality" in Q&A.
