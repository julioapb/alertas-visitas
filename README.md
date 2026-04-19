# Sistema de Alertas de Visitas - Flask

Aplicación web desarrollada con **Python (Flask)** para la gestión de clientes, visitas programadas y alertas automáticas.

Pensada para servicios recurrentes como:
- Control de plagas
- Mantenimiento técnico
- Inspecciones periódicas

---

## Funcionalidades principales

- Gestión de clientes
- Generación automática de visitas
- Alertas previas a visitas (2 días antes)
- Alertas de renovación de servicios
- Gestión de visitas:
  - Realizada
  - No realizada
  - Reprogramada
- Historial completo de alertas
- Registro de certificado generado
- Reprogramación de visitas

---

## Lógica del sistema

- Cada cliente puede tener una planificación de visitas
- Las visitas generan automáticamente alertas
- Las alertas se gestionan desde el dashboard
- Todas las acciones quedan registradas en historial

---

## Tecnologías utilizadas

- Python 3
- Flask
- MySQL / MariaDB
- Bootstrap 5
- Jinja2

---

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/tuusuario/tu-repo.git
