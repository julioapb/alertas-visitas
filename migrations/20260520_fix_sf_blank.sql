ALTER TABLE visitas_programadas
    MODIFY COLUMN sf TINYINT(1) NULL DEFAULT NULL;

ALTER TABLE historial_alertas
    MODIFY COLUMN sf TINYINT(1) NULL DEFAULT NULL;

UPDATE visitas_programadas
SET sf = NULL
WHERE sf = 0;

UPDATE historial_alertas
SET sf = NULL
WHERE sf = 0;
