# ACECQA Education & Care Services — Service Quality Analysis

Python code for the ACECQA data analysis assignment. Analyses the national
register of approved education and care services (17,663 rows, NQA ITS
extract) enriched with spatial/transport-access fields, focused on the
**Service Quality Analysis** stream:

- How NQS ratings vary by state and by service type
- Which of the seven Quality Areas is dragging each state's rating down
- Whether proximity to public transport correlates with quality

## Setup

```bash
pip install -r requirements.txt
```

The raw dataset lives at `data/education_services.csv`.

## Run

```bash
python src/quality_analysis.py
```

This loads and cleans the data (`src/clean.py`, cached to
`data/education_services_clean.parquet`), writes 5 figures to
`outputs/figures/`, and writes headline stats used in the presentation to
`outputs/summary_stats.json`.

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
  excluded from the transport-vs-quality chart only, since at national
  scale they'd compress every other distance bin onto a single pixel;
  they remain visible on the spatial map.

## Service-type categorisation

The dataset carries both a coarse `ServiceType` column (Centre-Based Care
/ Family Day Care) and seven non-exclusive detailed flags (a service can
be "Yes" on more than one, e.g. Long Day Care + Vacation Care). For the
by-type quality comparison, `quality_analysis.primary_service_type()`
assigns each service exactly one label using a fixed priority order
(Family Day Care > Long Day Care > Preschool standalone > Preschool
school-based > Outside School Hours Care > Other) so services aren't
double-counted. This is stated explicitly here per the assignment brief.

## External data

`data/external/au_states.geojson` — simplified Australian state boundary
polygons, used only as basemap context for the spatial scatter map (not
for any statistical join). Source: [rowanhogan/australian-states](https://github.com/rowanhogan/australian-states)
(public GitHub repo, GeoJSON derived from ABS boundaries).

Note: the ABS Remoteness Areas / Section of State boundary and allocation
files (`abs.gov.au`) needed for a rigorous urban/rural classification were
not reachable from this analysis environment's network, so that
classification is **not** attempted here — it's flagged as follow-up work
for the Accessibility & Coverage stream rather than approximated with a
weaker proxy.

## Headline findings (see `outputs/summary_stats.json`)

- **State spread is large**: ACT has the highest share of services rated
  "Exceeding NQS" or above (44.1%), WA the lowest (4.3%) — a ~10x gap
  between neighbouring regulatory jurisdictions applying the same
  National Law.
- **Weakest quality area nationally**: QA2 (Children's health & safety).
  **Strongest**: QA6 (Collaborative partnerships).
- **Transport proximity does not predict quality**: Spearman ρ ≈ -0.02
  between distance to nearest train station and rating (p < 0.01, so
  "significant" at n=16,031, but the effect size is negligible — the
  share rated "Exceeding" is ~20-22% at every distance band from <0.5km
  to 100km). This is a useful null result: ACECQA and transport agencies
  shouldn't treat transport access as a quality lever.

## Repo layout

```
data/education_services.csv        raw dataset (as supplied)
data/external/au_states.geojson    AU state boundaries (basemap only)
src/clean.py                       loading + cleaning
src/quality_analysis.py            5 visualisations + summary stats
outputs/figures/                   generated PNGs
outputs/summary_stats.json         headline numbers for slides
```
