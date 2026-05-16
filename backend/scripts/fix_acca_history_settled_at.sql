-- Idempotente: alinea acca_history con la migración Alembic 20260217_003
-- (misma semántica que SQLAlchemy DateTime(timezone=True) → TIMESTAMPTZ).
--
-- 1) Confirmá que psql / el cliente apunta a la MISMA base que DATABASE_URL del backend.
-- 2) Preferí: desde la carpeta backend/, con venv activado:
--      alembic upgrade head
-- 3) Si Alembic dice "already at head" pero la columna no existe, ejecutá este script
--    contra esa base. Luego verificá:
--      SELECT settled_at FROM acca_history LIMIT 1;
--
-- Si aplicaste el SQL a mano y alembic_version no tiene 20260217_003, podés alinear con:
--   INSERT INTO alembic_version (version_num) VALUES ('20260217_003')
--   ON CONFLICT DO NOTHING;  -- o revisar/stamp según tu estado real

ALTER TABLE acca_history
    ADD COLUMN IF NOT EXISTS settled_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS ix_acca_history_settled_at
    ON acca_history (settled_at);

-- Verificación rápida
SELECT settled_at FROM acca_history LIMIT 1;
