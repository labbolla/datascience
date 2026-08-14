USE `projeto_fbd`;

-- Demonstrates the date-validation trigger.
-- Replace city/trip IDs with values that exist in your local database if needed.
-- The trigger should reject the row because data_origem > data_destino.
INSERT INTO trecho (
    seq_trecho,
    meio_trasporte,
    num_diarias,
    missao,
    data_origem,
    data_destino,
    cidade_origem,
    cidade_destino,
    viagem_id_viagem
) VALUES (
    999,
    'Aereo',
    3,
    'V',
    '2025-06-10',
    '2025-06-05',
    1,
    2,
    101
);
