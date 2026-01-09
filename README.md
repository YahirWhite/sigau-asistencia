# SIGAU - Sistema de Asistencia Universitaria con QR

SIGAU es una plataforma de control académico diseñada para optimizar la gestión de asistencia en entornos universitarios. El sistema sustituye las listas físicas por un ecosistema digital blindado contra el fraude, con capacidad de interoperabilidad directa con sistemas administrativos basados en PostgreSQL.

## Propuesta de Valor y Motivación

El proyecto nace de la necesidad de resolver las vulnerabilidades del pase de lista tradicional: la lentitud del proceso, el error humano en la transcripción y el fraude por suplantación. 

Como estudiante de Ciberseguridad, enfoqué el desarrollo en la integridad de la data. SIGAU no es solo una herramienta de registro; es un sistema de auditoría en tiempo real que garantiza que el estudiante presente en el aula sea quien efectivamente registra su asistencia, permitiendo al docente recuperar el tiempo lectivo que antes se perdía en burocracia manual.

## Arquitectura y Funcionalidades Críticas

### 1. Interoperabilidad con Sistema Tepuy
El software ha sido diseñado para integrarse con el ecosistema administrativo institucional:
* **Módulo de Sincronización:** El sistema procesa la matrícula activa contra los registros de asistencia diaria.
* **Exportación Estructurada:** Genera archivos CSV/TXT con codificación específica para ser importados directamente a la base de datos central de Control de Estudios (Tepuy), eliminando la carga manual de inasistencias por parte del docente.

### 2. Protocolos de Seguridad y Anti-Fraude
* **Tokens QR Dinámicos:** El código proyectado utiliza un token encriptado que caduca automáticamente al finalizar la sesión. Esto impide el uso de fotografías o capturas de pantalla enviadas a terceros fuera del aula.
* **Validación Cruzada de Secciones:** El backend valida la identidad y la inscripción del estudiante. Si un alumno intenta registrar asistencia en una sección o asignatura no asignada en su perfil, el servidor deniega la transacción.
* **Periodos de Edición Controlados:** Implementación de un "Candado Académico" gestionado por el Administrador. Solo se permite la actualización de datos de sección durante lapsos específicos, garantizando la inmutabilidad de la data durante el semestre.

### 3. Interfaz y Experiencia de Usuario (UI/UX)
* **Enfoque Mobile-First:** Optimizado para el uso desde dispositivos móviles y tablets.
* **Sala de Situación Docente:** Panel en vivo que permite al profesor monitorear el flujo de ingresos y realizar verificaciones físicas inmediatas contra el conteo digital.
* **Personalización Avanzada (Modo Oscuro):** Implementación de una interfaz de alto contraste (Dark Mode) para mejorar la legibilidad en entornos de baja iluminación y reducir la fatiga visual durante jornadas nocturnas.
* **Protocolo de Respaldo:** Sistema de ingreso por código alfanumérico para estudiantes con fallas de hardware (cámara) o problemas de conectividad local.

## Stack Tecnológico

El sistema utiliza una arquitectura robusta preparada para alta concurrencia:
* **Motor de Base de Datos:** PostgreSQL (Manejo profesional de relaciones, índices y concurrencia).
* **Entorno de Desarrollo:** Python 3 con Framework Flask (Arquitectura modular basada en Blueprints).
* **Estilos y Maquetación:** TailwindCSS (Diseño responsivo y utilitario).
* **Gestión de Sesiones:** Flask-Login con encriptación de contraseñas mediante PBKDF2.

## Flujo de Operación Técnica

1. **Gestión de Integridad:** El Administrador habilita el periodo de actualización. Los estudiantes configuran su perfil. El Administrador bloquea la edición para asegurar la veracidad de los reportes. Esto cada que pasen 6 meses y por obvias razones varie su seccion actual.
2. **Ejecución en Aula:** El docente inicia la clase y despliega el QR Criptográfico. El servidor procesa las peticiones verificando unicidad (evita registros duplicados el mismo día) y pertenencia a la sección.
3. **Auditoría y Cierre:** El docente valida la lista, finaliza la clase y genera el reporte de inasist


---

*Desarrollado por Yahir Jose Peñate Olivo - Estudiante de Ciberseguridad - 2026*