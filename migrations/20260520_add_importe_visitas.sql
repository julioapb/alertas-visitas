ALTER TABLE visitas_programadas
    ADD COLUMN importe DECIMAL(10,2) NULL AFTER estado;

ALTER TABLE historial_alertas
    ADD COLUMN importe DECIMAL(10,2) NULL AFTER tipo_plaga;
