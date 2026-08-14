# Portfolio refactor notes

This repository is a cleaned, presentation-ready version of the original academic database project. The underlying model, research question and analytical scope are preserved, but several implementation details were made explicit or corrected before publication.

## Changes made

- Removed hard-coded MySQL credentials from the Python loader and replaced them with environment variables.
- Refactored the original data-preparation script into a readable ETL module with CLI arguments and explicit output schemas.
- Preserved the project's use of artificial traveler IDs in processed data.
- Reconstructed `schema.sql` from the final MySQL Workbench model (`projetoFBD_2.mwb`) and removed redundant indexes that duplicated primary-key indexes.
- Renamed the trigger from the accidental `BeforeInsertTrechoview_viagem_custoview_viagem_custo` to `BeforeInsertTrecho`.
- Rewrote the travel-cost view to use `COUNT(*)` for the number of legs and explicit first/last-leg joins.
- Removed the duplicate `total_viagens` alias from the employee query and renamed the net allowance metric so its components are explicit.
- Adjusted destination-country and UF cost queries to count each trip-level cost once using the trip's final destination, avoiding multiplication of costs by the number of legs.
- Added comments documenting aggregation semantics and limitations.

## Original artifacts retained

The original academic report and final MySQL Workbench model are included under `docs/` and `model/` for traceability.
