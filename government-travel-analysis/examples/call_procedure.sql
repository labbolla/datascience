USE `projeto_fbd`;

-- Multiple trip IDs are accepted as a comma-separated list.
CALL CalcularCustoViagemTemp('19192663,19586256,19557484');

-- Passing NULL returns all trips (potentially a very large result set).
-- CALL CalcularCustoViagemTemp(NULL);
