# ACECQA Education & Care Services — Full Analysis (Quality, Accessibility, Operations)

Python code for the ACECQA data analysis assignment. Analyses the national
register of approved education and care services (17,663 rows, NQA ITS
extract) enriched with spatial/transport-access fields, across all three
suggested streams:

**1. Service Quality**
- How NQS ratings vary by state and by service type
- Which of the seven Quality Areas is dragging each state's rating down
- Whether proximity to public transport correlates with quality

**2. Accessibility & Coverage** — four charts, each answering one of the
assignment's four requirements directly, plus one bridging chart:
- The geographical distribution of services, and the scale of the
  urban/rural disparity in provision
- Which specific regions need additional services most, ranked by
  distance to the nearest alternative service
- *(bridge)* Whether a state's transport-connectivity problem is just a
  function of how rural it is, or concentrated in a specific pocket
- Whether services are well-connected to public transport infrastructure
- Where the transport-underserved services are, mapped directly

**3. Operational Trends**
- Whether service size (capacity) predicts whether a service meets the
  NQS standard
- Whether the sector's approval trend reflects genuine growth or a
  regulatory artifact, and whether approval cohort predicts compliance
- Whether opening hours — or transport accessibility — predict
  non-compliance

## Run in Google Colab

Open directly from GitHub (bookmark this — it always loads the current
version, no upload needed):

```
https://colab.research.google.com/github/martvanhoorn2003-svg/Mart/blob/claude/acecqa-services-analysis-olfr4o/ACECQA_Service_Quality_Analysis.ipynb
```

Or manually: open a new Colab notebook, run

```python
!git clone -b claude/acecqa-services-analysis-olfr4o https://github.com/martvanhoorn2003-svg/Mart.git
%cd Mart
!pip install -q geopandas scipy pyarrow
```

then upload/open `ACECQA_Service_Quality_Analysis.ipynb` and run top to
bottom — it's self-contained and produces all 13 figures inline.

## Run locally

```bash
pip install -r requirements.txt
python src/quality_analysis.py
python src/accessibility_analysis.py
python src/operational_analysis.py
```

The raw dataset lives at `data/education_services.csv`. `src/clean.py`,
`src/urban_rural.py`, `src/quality_analysis.py`,
`src/accessibility_analysis.py` and `src/operational_analysis.py` are the
source-of-truth scripts; `ACECQA_Service_Quality_Analysis.ipynb` is the
same analysis as an annotated, Colab-ready notebook for
presentation/walkthrough use.

`quality_analysis.py` writes figures 01-05 (Service Quality);
`accessibility_analysis.py` writes figures 06-10 (Accessibility &
Coverage); `operational_analysis.py` writes figures 11-13 (Operational
Trends). All three append to the same `outputs/summary_stats.json`.

**Notebook design note:** every chart's headline stats are written into
the running `summary` dict immediately after that chart is drawn, not
recomputed later from leftover variables. An earlier version had a bug
where a later cell's reused variable name (`worst`) silently overwrote an
earlier cell's value before the final summary was written, corrupting
`worst_state` in the saved JSON — caught by re-reading the committed
output rather than trusting the "notebook ran with no errors" signal
alone. Fixed by making each section self-contained.

## Data cleaning decisions

- **10 rows dropped**: no State, Postcode or address at all, and all
  geocoded to the identical point `(97.49, 23.15)` — Myanmar, not
  Australia. This is a clear geocoder fallback/placeholder, not a real
  location, so these rows are excluded rather than imputed (they carry no
  recoverable spatial or regional information). All other duplicate
  coordinates checked (e.g. 4 services sharing one address in Ashfield,
  NSW) are genuine co-located services and were kept.
- **`Provisional – Not Yet Assessed`** is kept as its own category, not
  dropped and not treated as missing — it means the service is newly
  approved and hasn't had a first assessment visit yet, which is itself
  a meaningful operational fact, not a quality tier. It's excluded from
  ordinal quality comparisons via `clean.rated_only()`.
- **Missing `OverallRating`** (~7.5% of rows): left as missing rather than
  imputed, and excluded from quality comparisons — imputing a rating
  would fabricate a regulatory outcome.
- **Extreme transport distances** (e.g. 922km to the nearest train
  station for Torres Strait Island campuses of Tagai State College) are
  genuine, not data errors, and are flagged (`train_dist_outlier`,
  `bus_dist_outlier`, threshold >100km) rather than deleted. They are
  excluded from the transport-vs-quality and transport-vs-operations
  charts only, since at national scale they'd compress every other
  distance bin onto a single pixel; they remain visible on the spatial
  map.
- **`NumberOfApprovedPlaces` is missing for 415 of 417 Family Day Care
  services** — structurally, not by omission: FDC capacity is recorded
  per individually-registered educator across a scheme, not as a single
  site limit. FDC is excluded from the capacity-by-type chart rather
  than reported on 2 data points.
- **Weekly operating hours are undefined for Family Day Care schemes**:
  the "Annual" opening-hours columns record round-the-clock availability
  across the whole educator network (median ~168h/week — i.e. "always
  open"), which isn't a comparable figure to a single centre's opening
  hours, so FDC is excluded from the hours-vs-quality analysis.
- **The 2012 spike in approvals (4,706 services in one year) is a
  regulatory artifact, not organic growth**: the National Quality
  Framework commenced in January 2012 and every already-operating
  service was bulk-transferred onto new approval numbers that year. The
  approval-trend chart flags this explicitly rather than presenting it
  as a genuine sector expansion.

## Service-type categorisation

The dataset carries both a coarse `ServiceType` column (Centre-Based Care
/ Family Day Care) and seven non-exclusive detailed flags (a service can
be "Yes" on more than one, e.g. Long Day Care + Vacation Care). For the
by-type comparisons, `quality_analysis.primary_service_type()` assigns
each service exactly one label using a fixed priority order (Family Day
Care > Long Day Care > Preschool standalone > Preschool school-based >
Outside School Hours Care > Other) so services aren't double-counted.
This is stated explicitly here per the assignment brief.

## Urban/rural classification

Per the assignment brief, **Option A (spatial join)** is used:
`src/urban_rural.py` matches each service's own lon/lat against the ABS
**Section of State (SOS) 2021** boundary polygons via `geopandas.sjoin`.

SOS was chosen over the coarser Remoteness Areas file because its
population-based categories (Major Urban / Other Urban / Bounded
Locality / Rural Balance) collapse naturally into an urban/rural binary,
and a direct point-in-polygon join on coordinates the dataset already has
avoids the many-to-many postcode-to-SA1 ambiguity that Option B (the
allocation-file approach) would require.

Non-spatial SOS categories in the source file (Migratory, No usual
address — census-collection concepts that don't apply to a point
location) are dropped before the join. A handful of coastal/island
points fall just outside every polygon due to coastline generalisation
in the boundary file; those get a nearest-polygon fallback rather than
being left unclassified (only 1 of 17,653 services needed it — sanity
checked against known cities and remote towns: Sydney/Melbourne/Perth
CBDs → Major Urban, Fitzroy Crossing → Other Urban, Boigu Island (Torres
Strait) → Bounded Locality).

## External data

- `data/external/au_states.geojson` — simplified Australian state
  boundary polygons, used only as basemap context for the spatial
  scatter maps (not for any statistical join). Source:
  [rowanhogan/australian-states](https://github.com/rowanhogan/australian-states)
  (public GitHub repo, GeoJSON derived from ABS boundaries).
- `data/external/sos_2021/SOS_2021_AUST_GDA2020.*` — ABS Section of State
  2021 digital boundary file (GDA2020), used for the urban/rural spatial
  join above. Source: [ABS Digital Boundary Files](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files),
  © Australian Bureau of Statistics.

## Headline findings (see `outputs/summary_stats.json`)

**Service Quality**
- **State spread is large, and it's a compliance gap, not just an
  excellence gap**: Chart 1 ranks states by non-compliance (Working
  Towards NQS or Significant Improvement Required), worst first — the
  Northern Territory is worst (21.9% of services non-compliant),
  Victoria best (4.4%) — a ~5x gap between neighbouring regulatory
  jurisdictions applying the same National Law.
- **Overall-rating non-compliance and component-level non-compliance
  don't rank states identically**: Chart 3 averages non-compliance
  across the seven Quality Area sub-ratings rather than the single
  overall rating, and by that finer-grained measure WA and SA join NT
  and Tasmania near the top of the list (up to 14% non-compliant in a
  single Quality Area) even though WA ranks only 4th on the
  overall-rating measure in Chart 1 — a service's overall rating isn't
  a simple average of its seven component scores, so the two views can
  legitimately disagree about which state looks worst.
- **Weakest quality area nationally by non-compliance**: QA1
  (Educational program). **Strongest**: QA6 (Collaborative
  partnerships).
- **Ranked by non-compliance, Family Day Care is the worst-performing
  service type** (Chart 2): 22.3% non-compliant, roughly double Outside
  School Hours Care (11.0%) and Long Day Care (9.6%), and well above
  standalone Preschools, the best-performing type at 1.6%.
- **Distance from transport has a small but real negative effect on
  quality**: the share of services falling below the NQS standard
  (Working Towards NQS or Significant Improvement Required) rises from
  7.6% for the closest services to 10.3% for the furthest (Spearman
  ρ ≈ 0.026, p < 0.01, n=16,031) — a modest risk factor, not a dominant
  one, but not nothing either.

**Accessibility & Coverage — four requirements, four proofs**
- **Geographical distribution (Chart 6)**: services are **~12,000x more
  concentrated per km²** in Major Urban areas (954.4 services per
  1,000km²) than in Rural Balance areas (0.08 per 1,000km²) — a gap
  orders of magnitude larger than any reasonable population-driven
  demand ratio, not just a smaller population being served by fewer
  services proportionally.
- **Regions where additional services are needed most (Chart 7)**: **WA's
  Bounded Localities** are the single most underserved combination in
  the country — a median **41.0km** to the nearest alternative service —
  followed by **NT's Bounded Localities** at 30.5km. Two region ×
  area-type combinations sit above the 20km mark, where a family whose
  usual centre is full or closed has no realistic backup option.
- **Is a state's connectivity problem just how rural it is? (Chart 8,
  bridge)**: mostly, but not for WA. The Northern Territory and Tasmania
  are bad on both fronts — high rural share (21.7% and 11.7% of their
  services respectively) *and* poor statewide connectivity (45.0% and
  39.1% poorly connected) — a uniform, statewide problem. WA is the
  exact opposite: despite having the single biggest coverage gap in the
  country (Chart 7), only **4.0%** of its services sit in a rural area
  type, so its statewide connectivity average is the **best in the
  country** (9.6% poorly connected). WA's problem is a concentrated
  pocket, not a statewide gap — a different fix than NT's or Tasmania's
  (Spearman ρ ≈ 0.57, p = 0.14, n=8 states — descriptive given the small
  sample, not a statistically conclusive test).
- **Transport connectivity (Chart 9)**: **83.4%** of services nationally
  are well-connected to public transport (within a generous, drivable
  5km of a train station or 10km of a bus stop — deliberately set so the
  national majority clears it, rather than an unrealistically strict
  walking-distance bar that would make nearly everywhere look
  "underserved"). Against that generous bar, connectivity still
  **collapses in the country**: 91.3% well-connected in Major Urban vs
  just **21.4%** in Bounded Localities and **33.5%** in Rural Balance —
  a 70-point and 58-point gap respectively. This is a genuine rural
  transport gap, not a threshold artefact.
- **Spatially identifying underserved areas (Chart 10)**: mapping all
  2,688 poorly-connected services (against 13,511 well-connected) shows
  them concentrated in small towns and rural stretches away from the
  main rail corridors, consistent with Chart 9's area-type breakdown.

**Operational Trends — do these factors actually predict whether a service meets the standard?**
- **Capacity does not predict non-compliance** (Spearman ρ ≈ -0.007,
  p = 0.38, not statistically significant, n=15,967) — the smallest
  capacity quintile is 9.3% non-compliant, the largest 8.6%, essentially
  flat across a 5x range in size, despite capacity itself declining
  sharply from Major Urban (66 places median) to Bounded Locality (27).
- **Approval cohort is the strongest operational signal found**: services
  approved 2019 or later are **11.0% non-compliant**, against **8.4%**
  for pre-2012 established services — newer services haven't had time
  to embed practice yet. (2012 itself is excluded from this reading —
  it's the National Quality Framework's bulk-transfer cohort, which is
  why raw approval counts spike there without a matching signal: 7.6%
  non-compliant, in line with the other established, pre-existing
  cohorts, not with genuinely new services.)
- **Longer opening hours are a real, visible compliance risk**:
  non-compliance more than doubles from **7.3%** for the shortest-hours
  band (under 45h/week) to **19.0%** for the longest (60h+) — the
  largest operational-factor effect found, even though the Spearman rank
  correlation itself is small (ρ ≈ 0.031, p < 0.01, n=9,490).
- **Transport accessibility does not meaningfully move capacity or
  opening hours** (ρ ≈ -0.06 and ρ ≈ 0.02 respectively — both negligible
  in size, even where the latter is technically significant at p < .05).
  So while the Service Quality stream found a small direct effect of
  transport distance on compliance, that effect isn't operating through
  capacity or hours — it's a standalone, modest risk factor.
- **Bottom line**: of three operational factors tested directly against
  non-compliance (capacity, opening hours, approval cohort), two show a
  real, actionable signal — opening hours, and especially service age —
  and one doesn't: capacity is not a meaningful compliance driver.

## Repo layout

```
data/education_services.csv                    raw dataset (as supplied)
data/external/au_states.geojson                 AU state boundaries (basemap only)
data/external/sos_2021/SOS_2021_AUST_GDA2020.*  ABS Section of State boundaries (urban/rural join)
src/clean.py                                    loading + cleaning
src/urban_rural.py                              ABS SOS spatial join
src/quality_analysis.py                         figures 01-05 (Service Quality)
src/accessibility_analysis.py                   figures 06-10 (Accessibility & Coverage)
src/operational_analysis.py                     figures 11-13 (Operational Trends)
outputs/figures/                                generated PNGs
outputs/summary_stats.json                      headline numbers for slides
ACECQA_Service_Quality_Analysis.ipynb           Colab-ready notebook, all three streams
```
