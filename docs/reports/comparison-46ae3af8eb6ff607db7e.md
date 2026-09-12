# Same-day block-to-village versus district-to-village comparison

Snapshot: `comparison-46ae3af8eb6ff607db7e`. Prepared from the local IMD bulletin downloaded 2026-09-12T08:16:47.488886+00:00.

## What is being compared

Block issue **2026-09-10** versus district issue **2026-09-11**. Shared forecast dates: **2026-09-12, 2026-09-13, 2026-09-14, 2026-09-15**.

Each date pairs 1,916 villages by exact ID, parent and valid date. Across 4 dates there are 7,664 village-date pairs. These are repeated forecasts, not independent observations.

Block-only dates: 2026-09-11. District-only dates: 2026-09-16. Dates outside the intersection are excluded; none are shifted or interpolated.

This report focuses on rainfall. The all-weather section pairs available temperature, humidity and wind fields. Qualitative cloud wording is not converted to numeric oktas. The unit is mm for the source-labelled day; identical accumulation hours are not verified.

The geography consists of village polygons, not verified gram-panchayat boundaries. All 15 mapped blocks are represented. The 37 unresolved Central features are excluded from numerical pairs; no missing parent is guessed.

## Main findings

Across all pairs, mean absolute disagreement is **14.70 mm**, root-mean-square disagreement is **17.92 mm**, and the largest absolute gap is **40.44 mm**.

Block-derived forecasts are higher in 784 pairs; district-derived forecasts are higher in 6,880; 0 agree within 0.0001 mm. 6,927 pairs (90.4%) differ by more than 5 mm, and 4,279 (55.8%) differ by more than 10 mm.

These numbers measure disagreement, not forecast error. Neither route can be declared more accurate without independent observed rainfall.

## Date-by-date results

All means in the first table give each village equal weight. Difference = block-derived minus district-derived; a negative value means the district route is wetter.

| Valid date | District source | Block local mean | District local mean | Signed mean gap | Mean absolute gap | RMS gap | Median absolute gap | P90 absolute gap | Maximum absolute gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-12 | 9.00 | 2.48 | 9.06 | -6.58 | 6.58 | 6.70 | 6.76 | 8.14 | 8.82 |
| 2026-09-13 | 35.00 | 32.41 | 35.24 | -2.82 | 10.65 | 13.31 | 9.10 | 15.05 | 34.16 |
| 2026-09-14 | 50.00 | 28.60 | 50.34 | -21.73 | 29.02 | 29.80 | 31.42 | 37.70 | 40.44 |
| 2026-09-15 | 20.00 | 8.73 | 20.13 | -11.40 | 12.57 | 13.20 | 13.37 | 16.81 | 18.28 |

### Area-weighted view

Large villages contribute more here. Weights are geodesic areas of the same matched footprints, not population or crop area. District means conserve the district source only across its full modeled footprint; missing pairs would invalidate that equality.

| Date | Area-weighted block | Area-weighted district | Signed gap | Mean absolute gap |
|---|---:|---:|---:|---:|
| 2026-09-12 | 2.62 | 9.00 | -6.38 | 6.38 |
| 2026-09-13 | 31.11 | 35.00 | -3.89 | 9.67 |
| 2026-09-14 | 24.91 | 50.00 | -25.09 | 29.22 |
| 2026-09-15 | 7.66 | 20.00 | -12.34 | 13.00 |

## Why identical terrain and dates do not imply identical forecasts

### 1. The parent inputs differ

The block path starts with a forecast specific to each block, while the district path starts with one district-wide number. The local adjustment does not replace this input. Different inputs therefore produce different village outputs even with an unchanged model and terrain.

### 2. The forecasts were issued on different days

The district issue is 1 calendar day later. For example, for 13 September the block issue is three calendar days earlier and the district issue is two days earlier. Exact lead hours are unknown. The comparison combines source-resolution differences with a forecast-update difference; those two influences cannot be separated from this pair of bulletins.

Weather forecasts depend on atmospheric conditions, not just terrain. New observations can alter initial conditions and subsequent forecasts. This is a general explanation, not evidence identifying the exact change in these IMD bulletins. [ECMWF: data assimilation](https://www.ecmwf.int/en/research/data-assimilation).

IMD describes separate district and block five-day forecast products. The supplied exports do not identify their precise upstream model configuration or establish identical spatial averaging. We must not assume that a district forecast equals an area-weighted average of the separately published block forecasts. [IMD: Agromet services](https://internal.imd.gov.in/press_release/20220824_pr_1790.pdf).

### 3. The reference area changes inside our model

Let c(v) be the learned seasonal rainfall climatology for village v; Cb and Cd are its block and district area-weighted reference climatologies. Let Sb and Sd be the official block and district inputs for the date.

```text
Block factor fb = c(v) / Cb
District factor fd = c(v) / Cd
Block local B = Sb × fb
District local D = Sd × fd
B / D = (Sb / Sd) × (Cd / Cb)  [when denominators are nonzero]
```

The same village numerator cancels in the ratio. Within a block and date, the two unrounded local fields are therefore proportional. Their spatial patterns are not independent evidence of agreement: both reuse the same learned field. Absolute gaps can still grow with the village factor. Coincidentally equal outputs can arise through cancellation.

There is no fresh terrain change, random ensemble noise or day-specific local storm model in this implementation. Rainfall factors are fixed across these dates; most day-to-day variation comes from the parent inputs. Real precipitation can vary with atmospheric moisture, circulation and storm placement, which this static local transfer does not explicitly model.

### 4. Exact algebraic separation

We use a symmetric split so neither route is privileged as the reference. These are mathematical contributions, not causal estimates or percentages of accuracy:

```text
Source component = (Sb − Sd) × (fb + fd) / 2
Reference component = (Sb + Sd) × (fb − fd) / 2
Source component + Reference component = B − D
```

Output rounding leaves a residual below 0.0001 mm. Signed contributions may oppose each other; absolute contributions do not add to the absolute final gap when cancellation occurs.

| Date | Mean signed source component | Mean signed reference component | Mean absolute source component | Mean absolute reference component |
|---|---:|---:|---:|---:|
| 2026-09-12 | -6.56 | -0.02 | 6.56 | 0.21 |
| 2026-09-13 | -2.55 | -0.27 | 10.84 | 1.23 |
| 2026-09-14 | -21.40 | -0.34 | 29.04 | 1.47 |
| 2026-09-15 | -11.28 | -0.12 | 12.56 | 0.55 |

## Every block on every shared date

Source columns are official parent values. Local columns are equal-village means. The factor column is the mean block factor / mean district factor; its ratio reflects changing reference areas.

| Date | Block | N | Block source | District source | Block local mean | District local mean | Mean signed gap | Mean absolute gap | Mean factors B / D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-12 | Baglan | 170 | 3.10 | 9.00 | 3.10 | 8.38 | -5.28 | 5.28 | 1.0000 / 0.9313 |
| 2026-09-12 | Chandwad | 111 | 3.90 | 9.00 | 3.90 | 8.74 | -4.84 | 4.84 | 1.0002 / 0.9708 |
| 2026-09-12 | Deola | 50 | 3.40 | 9.00 | 3.40 | 8.76 | -5.36 | 5.36 | 0.9998 / 0.9734 |
| 2026-09-12 | Dindori | 157 | 2.30 | 9.00 | 2.30 | 8.98 | -6.68 | 6.68 | 0.9984 / 0.9974 |
| 2026-09-12 | Igatpuri | 117 | 1.60 | 9.00 | 1.60 | 9.60 | -8.00 | 8.00 | 1.0016 / 1.0665 |
| 2026-09-12 | Kalwan | 151 | 3.20 | 9.00 | 3.21 | 8.60 | -5.39 | 5.39 | 1.0043 / 0.9555 |
| 2026-09-12 | Malegaon | 142 | 3.60 | 9.00 | 3.61 | 8.76 | -5.15 | 5.15 | 1.0033 / 0.9735 |
| 2026-09-12 | Nandgaon | 100 | 2.20 | 9.00 | 2.20 | 8.82 | -6.62 | 6.62 | 0.9995 / 0.9795 |
| 2026-09-12 | Nashik | 73 | 2.30 | 9.00 | 2.30 | 9.36 | -7.06 | 7.06 | 1.0016 / 1.0400 |
| 2026-09-12 | Niphad | 133 | 1.00 | 9.00 | 1.00 | 9.20 | -8.21 | 8.21 | 0.9998 / 1.0228 |
| 2026-09-12 | Peth | 145 | 1.90 | 9.00 | 1.90 | 9.60 | -7.70 | 7.70 | 0.9987 / 1.0664 |
| 2026-09-12 | Sinnar | 129 | 2.20 | 9.00 | 2.20 | 9.29 | -7.08 | 7.08 | 1.0015 / 1.0319 |
| 2026-09-12 | Surgana | 189 | 1.20 | 9.00 | 1.20 | 9.26 | -8.06 | 8.06 | 1.0032 / 1.0290 |
| 2026-09-12 | Trimbak | 125 | 2.10 | 9.00 | 2.10 | 9.69 | -7.58 | 7.58 | 1.0022 / 1.0763 |
| 2026-09-12 | Yeola | 124 | 4.10 | 9.00 | 4.11 | 8.97 | -4.87 | 4.87 | 1.0021 / 0.9971 |
| 2026-09-13 | Baglan | 170 | 20.70 | 35.00 | 20.70 | 32.60 | -11.90 | 11.90 | 1.0000 / 0.9313 |
| 2026-09-13 | Chandwad | 111 | 26.60 | 35.00 | 26.61 | 33.98 | -7.37 | 7.37 | 1.0002 / 0.9708 |
| 2026-09-13 | Deola | 50 | 24.40 | 35.00 | 24.39 | 34.07 | -9.68 | 9.68 | 0.9998 / 0.9734 |
| 2026-09-13 | Dindori | 157 | 27.00 | 35.00 | 26.96 | 34.91 | -7.95 | 7.95 | 0.9984 / 0.9974 |
| 2026-09-13 | Igatpuri | 117 | 38.20 | 35.00 | 38.26 | 37.33 | 0.93 | 0.93 | 1.0016 / 1.0665 |
| 2026-09-13 | Kalwan | 151 | 22.80 | 35.00 | 22.90 | 33.44 | -10.55 | 10.55 | 1.0043 / 0.9555 |
| 2026-09-13 | Malegaon | 142 | 28.00 | 35.00 | 28.09 | 34.07 | -5.98 | 5.98 | 1.0033 / 0.9735 |
| 2026-09-13 | Nandgaon | 100 | 49.20 | 35.00 | 49.18 | 34.28 | 14.89 | 14.89 | 0.9995 / 0.9795 |
| 2026-09-13 | Nashik | 73 | 27.30 | 35.00 | 27.34 | 36.40 | -9.06 | 9.06 | 1.0016 / 1.0400 |
| 2026-09-13 | Niphad | 133 | 33.80 | 35.00 | 33.79 | 35.80 | -2.00 | 2.00 | 0.9998 / 1.0228 |
| 2026-09-13 | Peth | 145 | 23.70 | 35.00 | 23.67 | 37.32 | -13.65 | 13.65 | 0.9987 / 1.0664 |
| 2026-09-13 | Sinnar | 129 | 21.50 | 35.00 | 21.53 | 36.11 | -14.58 | 14.58 | 1.0015 / 1.0319 |
| 2026-09-13 | Surgana | 189 | 67.00 | 35.00 | 67.21 | 36.01 | 31.20 | 31.20 | 1.0032 / 1.0290 |
| 2026-09-13 | Trimbak | 125 | 34.10 | 35.00 | 34.18 | 37.67 | -3.49 | 3.49 | 1.0022 / 1.0763 |
| 2026-09-13 | Yeola | 124 | 29.50 | 35.00 | 29.56 | 34.90 | -5.34 | 5.34 | 1.0021 / 0.9971 |
| 2026-09-14 | Baglan | 170 | 23.80 | 50.00 | 23.80 | 46.57 | -22.77 | 22.77 | 1.0000 / 0.9313 |
| 2026-09-14 | Chandwad | 111 | 15.50 | 50.00 | 15.50 | 48.54 | -33.04 | 33.04 | 1.0002 / 0.9708 |
| 2026-09-14 | Deola | 50 | 17.50 | 50.00 | 17.50 | 48.67 | -31.17 | 31.17 | 0.9998 / 0.9734 |
| 2026-09-14 | Dindori | 157 | 27.60 | 50.00 | 27.55 | 49.87 | -22.31 | 22.31 | 0.9984 / 0.9974 |
| 2026-09-14 | Igatpuri | 117 | 33.10 | 50.00 | 33.15 | 53.32 | -20.17 | 20.17 | 1.0016 / 1.0665 |
| 2026-09-14 | Kalwan | 151 | 25.80 | 50.00 | 25.91 | 47.78 | -21.87 | 21.87 | 1.0043 / 0.9555 |
| 2026-09-14 | Malegaon | 142 | 13.80 | 50.00 | 13.85 | 48.67 | -34.83 | 34.83 | 1.0033 / 0.9735 |
| 2026-09-14 | Nandgaon | 100 | 15.80 | 50.00 | 15.79 | 48.97 | -33.18 | 33.18 | 0.9995 / 0.9795 |
| 2026-09-14 | Nashik | 73 | 28.30 | 50.00 | 28.35 | 52.00 | -23.66 | 23.66 | 1.0016 / 1.0400 |
| 2026-09-14 | Niphad | 133 | 25.20 | 50.00 | 25.20 | 51.14 | -25.94 | 25.94 | 0.9998 / 1.0228 |
| 2026-09-14 | Peth | 145 | 20.20 | 50.00 | 20.17 | 53.32 | -33.14 | 33.14 | 0.9987 / 1.0664 |
| 2026-09-14 | Sinnar | 129 | 14.20 | 50.00 | 14.22 | 51.59 | -37.37 | 37.37 | 1.0015 / 1.0319 |
| 2026-09-14 | Surgana | 189 | 88.10 | 50.00 | 88.38 | 51.45 | 36.93 | 36.93 | 1.0032 / 1.0290 |
| 2026-09-14 | Trimbak | 125 | 33.50 | 50.00 | 33.57 | 53.81 | -20.24 | 20.24 | 1.0022 / 1.0763 |
| 2026-09-14 | Yeola | 124 | 11.40 | 50.00 | 11.42 | 49.85 | -38.43 | 38.43 | 1.0021 / 0.9971 |
| 2026-09-15 | Baglan | 170 | 8.10 | 20.00 | 8.10 | 18.63 | -10.53 | 10.53 | 1.0000 / 0.9313 |
| 2026-09-15 | Chandwad | 111 | 4.50 | 20.00 | 4.50 | 19.42 | -14.91 | 14.91 | 1.0002 / 0.9708 |
| 2026-09-15 | Deola | 50 | 4.50 | 20.00 | 4.50 | 19.47 | -14.97 | 14.97 | 0.9998 / 0.9734 |
| 2026-09-15 | Dindori | 157 | 6.60 | 20.00 | 6.59 | 19.95 | -13.36 | 13.36 | 0.9984 / 0.9974 |
| 2026-09-15 | Igatpuri | 117 | 16.80 | 20.00 | 16.83 | 21.33 | -4.50 | 4.50 | 1.0016 / 1.0665 |
| 2026-09-15 | Kalwan | 151 | 7.40 | 20.00 | 7.43 | 19.11 | -11.68 | 11.68 | 1.0043 / 0.9555 |
| 2026-09-15 | Malegaon | 142 | 3.70 | 20.00 | 3.71 | 19.47 | -15.76 | 15.76 | 1.0033 / 0.9735 |
| 2026-09-15 | Nandgaon | 100 | 7.70 | 20.00 | 7.70 | 19.59 | -11.89 | 11.89 | 0.9995 / 0.9795 |
| 2026-09-15 | Nashik | 73 | 7.40 | 20.00 | 7.41 | 20.80 | -13.39 | 13.39 | 1.0016 / 1.0400 |
| 2026-09-15 | Niphad | 133 | 4.10 | 20.00 | 4.10 | 20.46 | -16.36 | 16.36 | 0.9998 / 1.0228 |
| 2026-09-15 | Peth | 145 | 4.50 | 20.00 | 4.49 | 21.33 | -16.83 | 16.83 | 0.9987 / 1.0664 |
| 2026-09-15 | Sinnar | 129 | 2.80 | 20.00 | 2.80 | 20.64 | -17.83 | 17.83 | 1.0015 / 1.0319 |
| 2026-09-15 | Surgana | 189 | 26.40 | 20.00 | 26.48 | 20.58 | 5.91 | 5.91 | 1.0032 / 1.0290 |
| 2026-09-15 | Trimbak | 125 | 13.00 | 20.00 | 13.03 | 21.53 | -8.50 | 8.50 | 1.0022 / 1.0763 |
| 2026-09-15 | Yeola | 124 | 3.80 | 20.00 | 3.81 | 19.94 | -16.13 | 16.13 | 1.0021 / 0.9971 |

## Largest village disagreements

| Date | Village | Block | Block local | District local | Gap | % vs district |
|---|---|---|---:|---:|---:|---:|
| 2026-09-12 | Bhati (MH_487_549760) | Surgana | 1.32 | 10.14 | -8.82 | -87.00% |
| 2026-09-12 | Kahandolpada (MH_487_549759) | Surgana | 1.31 | 10.07 | -8.76 | -87.00% |
| 2026-09-12 | Khobale Digar (MH_487_549758) | Surgana | 1.30 | 9.97 | -8.68 | -87.00% |
| 2026-09-12 | Khirdi (MH_487_549761) | Surgana | 1.28 | 9.85 | -8.57 | -87.00% |
| 2026-09-12 | Chinchale Khair (MH_487_551083) | Igatpuri | 1.71 | 10.27 | -8.56 | -83.30% |
| 2026-09-12 | Karanjul (MH_487_549724) | Surgana | 1.28 | 9.83 | -8.55 | -87.00% |
| 2026-09-12 | Rakshasbhuvan (MH_487_549723) | Surgana | 1.28 | 9.82 | -8.54 | -87.00% |
| 2026-09-12 | Mandha (MH_487_549617) | Surgana | 1.28 | 9.81 | -8.54 | -87.00% |
| 2026-09-12 | Bhenshet (MH_487_549757) | Surgana | 1.27 | 9.78 | -8.51 | -87.00% |
| 2026-09-12 | Amdabarhe (MH_487_549725) | Surgana | 1.27 | 9.75 | -8.49 | -87.00% |
| 2026-09-13 | Bhati (MH_487_549760) | Surgana | 73.59 | 39.43 | 34.16 | 86.64% |
| 2026-09-13 | Kahandolpada (MH_487_549759) | Surgana | 73.09 | 39.16 | 33.93 | 86.64% |
| 2026-09-13 | Khobale Digar (MH_487_549758) | Surgana | 72.39 | 38.79 | 33.60 | 86.64% |
| 2026-09-13 | Khirdi (MH_487_549761) | Surgana | 71.51 | 38.31 | 33.19 | 86.64% |
| 2026-09-13 | Karanjul (MH_487_549724) | Surgana | 71.32 | 38.21 | 33.11 | 86.64% |
| 2026-09-13 | Rakshasbhuvan (MH_487_549723) | Surgana | 71.28 | 38.19 | 33.09 | 86.64% |
| 2026-09-13 | Mandha (MH_487_549617) | Surgana | 71.23 | 38.16 | 33.06 | 86.64% |
| 2026-09-13 | Bhenshet (MH_487_549757) | Surgana | 70.97 | 38.03 | 32.94 | 86.64% |
| 2026-09-13 | Amdabarhe (MH_487_549725) | Surgana | 70.80 | 37.93 | 32.86 | 86.64% |
| 2026-09-13 | Bardipada (MH_487_549593) | Surgana | 70.52 | 37.79 | 32.74 | 86.64% |
| 2026-09-14 | Bhati (MH_487_549760) | Surgana | 96.77 | 56.33 | 40.44 | 71.79% |
| 2026-09-14 | Kahandolpada (MH_487_549759) | Surgana | 96.11 | 55.95 | 40.16 | 71.79% |
| 2026-09-14 | Khobale Digar (MH_487_549758) | Surgana | 95.19 | 55.41 | 39.78 | 71.79% |
| 2026-09-14 | Satyagaon (MH_487_551437) | Yeola | 11.77 | 51.37 | -39.60 | -77.09% |
| 2026-09-14 | Mahalkhede Chandvad (MH_487_551491) | Yeola | 11.77 | 51.34 | -39.58 | -77.09% |
| 2026-09-14 | Mahalkhede Patoda (MH_487_551490) | Yeola | 11.74 | 51.23 | -39.49 | -77.09% |
| 2026-09-14 | Mukhed (MH_487_551436) | Yeola | 11.74 | 51.21 | -39.48 | -77.09% |
| 2026-09-14 | Bhingare (MH_487_551489) | Yeola | 11.72 | 51.13 | -39.41 | -77.09% |
| 2026-09-14 | Nimgaon Madh (MH_487_551492) | Yeola | 11.70 | 51.05 | -39.35 | -77.09% |
| 2026-09-14 | Neurgaon (MH_487_551435) | Yeola | 11.69 | 51.01 | -39.32 | -77.09% |
| 2026-09-15 | Pandhurli (MH_487_551204) | Sinnar | 2.87 | 21.15 | -18.28 | -86.41% |
| 2026-09-15 | Belu (MH_487_551213) | Sinnar | 2.87 | 21.12 | -18.25 | -86.41% |
| 2026-09-15 | Vinchur Dalvi (MH_487_551198) | Sinnar | 2.86 | 21.05 | -18.19 | -86.41% |
| 2026-09-15 | Agas Khind (MH_487_551212) | Sinnar | 2.86 | 21.03 | -18.17 | -86.41% |
| 2026-09-15 | Jogaltembhi (MH_487_551140) | Sinnar | 2.85 | 20.95 | -18.11 | -86.41% |
| 2026-09-15 | Sawatamalinagar (MH_487_551203) | Sinnar | 2.85 | 20.94 | -18.10 | -86.41% |
| 2026-09-15 | Borpada (MH_487_550763) | Peth | 4.83 | 22.92 | -18.09 | -78.93% |
| 2026-09-15 | Bramhan Wade (MH_487_551143) | Sinnar | 2.84 | 20.93 | -18.08 | -86.41% |
| 2026-09-15 | Songiri (MH_487_551142) | Sinnar | 2.84 | 20.89 | -18.05 | -86.41% |
| 2026-09-15 | Phanaspada (MH_487_550787) | Peth | 4.82 | 22.87 | -18.05 | -78.93% |

## Practical implications

The routes fall on opposite sides of the application's ≥20 mm advisory trigger in 1,620 village-date pairs. This is an app-rule sensitivity check, not an official hazard category, measured agricultural impact or evidence that either advisory is correct.

Do not silently average the routes, choose the larger number as truth, or treat their spread as a calibrated confidence interval. The same local model makes their errors correlated, and their different issue times confound a direct skill comparison. Retain both source labels and dates; use disagreement to identify cases for review.

For a fair model evaluation, collect block and district forecasts from the same issue cycle for identical accumulation hours and lead times, retain their original files, and pair both with independent village/rain-gauge observations. Evaluate wet/dry cases, rainfall thresholds, bias, MAE/RMSE and event skill by lead time and geography using withheld periods. Compare against unchanged-parent forecasts as well as these adjusted paths. Only then assess whether selecting or blending improves performance.

## Limits and reproducibility

The terrain model was fitted to coarse NASA POWER seasonal proxies, with only five distinct historic profiles in Nashik. Local factors and footprint-mean assumptions are experimental; neither within-block accuracy nor prediction intervals are validated. A date match does not verify identical accumulation intervals. Source authenticity is not cryptographically attested. The comparison does not repair those limitations.

Model: `terrain-631e5f007f8d4bca7a85`. Block run: `block-8ed619637d1bb7d52fa99ed6`. District run: `district-1e048cdee85e5629cf475d7a`.

The adjacent [comparison-46ae3af8eb6ff607db7e.json](comparison-46ae3af8eb6ff607db7e.json) contains the frozen district source bulletin, every paired village row, factor, component and summary. Block raw-source provenance remains in the named immutable run and imported dataset. Regenerate with `.venv\Scripts\python scripts/report_forecast_comparison.py`; this reads the current local district cache without a network request and creates a different snapshot if either run changes.

The UI comparison view pins both runs while changing dates and blocks. Compare latest sources explicitly starts a new pairing. A missing overlap, mismatched model, unresolved village or unavailable variable is never replaced with a fabricated value.

## All-weather comparisons

| Date | Variable | Pairs | Block mean | District mean | Mean absolute gap | Maximum gap |
|---|---|---|---|---|---|---|
| 2026-09-12 | rainfall_mm | 1916 | 2.48 | 9.06 | 6.58 | 8.82 |
| 2026-09-12 | temp_max_c | 1916 | 29.21 | 30.03 | 1.72 | 3.91 |
| 2026-09-12 | temp_min_c | 1916 | 21.30 | 21.03 | 0.61 | 1.34 |
| 2026-09-12 | relative_humidity_max_pct | 1916 | 94.23 | 87.00 | 7.23 | 11.00 |
| 2026-09-12 | relative_humidity_min_pct | 1916 | 60.17 | 68.00 | 10.27 | 29.00 |
| 2026-09-12 | wind_speed_kmph | 1916 | 11.18 | 11.00 | 2.73 | 8.20 |
| 2026-09-13 | rainfall_mm | 1916 | 32.41 | 35.24 | 10.65 | 34.16 |
| 2026-09-13 | temp_max_c | 1916 | 25.91 | 29.03 | 3.12 | 4.61 |
| 2026-09-13 | temp_min_c | 1916 | 21.33 | 20.03 | 1.37 | 2.84 |
| 2026-09-13 | relative_humidity_max_pct | 1916 | 93.13 | 86.00 | 7.13 | 12.00 |
| 2026-09-13 | relative_humidity_min_pct | 1916 | 77.96 | 85.00 | 7.37 | 17.00 |
| 2026-09-13 | wind_speed_kmph | 1916 | 13.71 | 14.00 | 3.25 | 9.50 |
| 2026-09-14 | rainfall_mm | 1916 | 28.60 | 50.34 | 29.02 | 40.44 |
| 2026-09-14 | temp_max_c | 1916 | 23.96 | 27.03 | 3.07 | 4.61 |
| 2026-09-14 | temp_min_c | 1916 | 21.35 | 18.03 | 3.31 | 4.15 |
| 2026-09-14 | relative_humidity_max_pct | 1916 | 93.55 | 93.00 | 2.56 | 6.00 |
| 2026-09-14 | relative_humidity_min_pct | 1916 | 86.75 | 86.00 | 3.98 | 8.00 |
| 2026-09-14 | wind_speed_kmph | 1916 | 16.26 | 16.00 | 3.09 | 7.20 |
| 2026-09-15 | rainfall_mm | 1916 | 8.73 | 20.13 | 12.57 | 18.28 |
| 2026-09-15 | temp_max_c | 1916 | 24.58 | 28.03 | 3.46 | 5.11 |
| 2026-09-15 | temp_min_c | 1916 | 21.22 | 19.03 | 2.19 | 3.05 |
| 2026-09-15 | relative_humidity_max_pct | 1916 | 93.71 | 87.00 | 6.71 | 11.00 |
| 2026-09-15 | relative_humidity_min_pct | 1916 | 81.45 | 86.00 | 6.74 | 16.00 |
| 2026-09-15 | wind_speed_kmph | 1916 | 16.36 | 16.00 | 1.94 | 5.50 |
