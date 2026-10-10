# KhetSathi Agronomic Parameter Sources

This document records the agronomic parameter sources and benchmarks used in KhetSathi, in compliance with Section 26 of the TRD and Environmental Hacks 2026 track requirements.

## 1. Crop Coefficients and Growth Stages (FAO Irrigation and Drainage Paper No. 56)

### Maize (Grain/Sweet Corn)
- **Reference:** Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56, Rome, Italy.
  - Table 11: Lengths of crop development stages (Sub-humid to semi-arid tropical / sub-tropical):
    - Initial stage ($L_{\text{ini}}$): 20 days
    - Crop development stage ($L_{\text{dev}}$): 35 days
    - Mid-season stage ($L_{\text{mid}}$): 40 days
    - Late season stage ($L_{\text{late}}$): 30 days
    - Total season: 125 days
  - Table 12: Single crop coefficient ($K_c$):
    - $K_{c,\text{ini}}$: 0.30 (soil surface wetted periodically)
    - $K_{c,\text{mid}}$: 1.20
    - $K_{c,\text{end}}$: 0.50 (dry harvest)
  - Table 22: Maximum rooting depth ($Z_r$) and allowable depletion fraction ($p$):
    - Rooting depth ($Z_r$): 0.3 m (initial) to 1.0 m (mature)
    - Allowable depletion fraction ($p$): 0.55 (at $ET_c \approx 5\text{ mm/day}$)

### Tomato
- **Reference:** FAO-56:
  - Table 11: Stages: $L_{\text{ini}} = 30\text{ d}$, $L_{\text{dev}} = 40\text{ d}$, $L_{\text{mid}} = 45\text{ d}$, $L_{\text{late}} = 30\text{ d}$
  - Table 12: $K_{c,\text{ini}} = 0.60$, $K_{c,\text{mid}} = 1.15$, $K_{c,\text{end}} = 0.80$
  - Table 22: $Z_r = 0.25\text{ m}$ to $0.70\text{ m}$, $p = 0.40$

## 2. Soil Water Parameters
- **Reference:** FAO-56 Table 19 (Available water capacity for different soil textures):
  - **Loam:** Field Capacity ($\text{FC}$) = 0.27 m³/m³, Wilting Point ($\text{WP}$) = 0.12 m³/m³, Available Water ($\text{AWC}$) = 150 mm/m.
  - **Clay Loam:** $\text{FC} = 0.32$, $\text{WP} = 0.15$, $\text{AWC} = 170\text{ mm/m}$.
  - **Sandy Loam:** $\text{FC} = 0.18$, $\text{WP} = 0.08$, $\text{AWC} = 100\text{ mm/m}$.
  - **Clay:** $\text{FC} = 0.36$, $\text{WP} = 0.21$, $\text{AWC} = 150\text{ mm/m}$.
  - **Sand:** $\text{FC} = 0.10$, $\text{WP} = 0.04$, $\text{AWC} = 60\text{ mm/m}$.

## 3. Solar Pump & Application Defaults
- **Reference:** Bureau of Energy Efficiency (BEE) India / PM-KUSUM guidelines for solar pumps:
  - Flow rate: 100–160 L/min for 2–3 HP surface / submersible DC solar pump sets.
  - Default pump discharge rate: 120 L/min (7.2 m³/h).
  - Rated pump power: 0.75 kW (1 HP) to 2.2 kW (3 HP).
  - Default surface/basin irrigation application efficiency: 70–80% (0.75).
  - Default drip/micro irrigation application efficiency: 85–90% (0.90).
