# Analytical query conventions

The original academic project stores travel costs at the `viagem` (trip) level while destinations and dates live at the `trecho` (leg) level. Joining them naively can multiply the same trip cost when a trip contains several legs.

The cleaned portfolio queries make the allocation rule explicit:

- **01_monthly_expenses.sql**: allocates each trip's costs equally across its legs, preserving the original intent of monthly analysis while avoiding duplication.
- **04_costs_by_destination_country.sql**: attributes each trip's complete cost once to the **final destination country**.
- **05_costs_by_state_transport.sql**: attributes ticket cost once to the **final destination UF**; transport rankings still use all legs ending in that UF.

These choices are documented so the aggregation semantics are auditable.
