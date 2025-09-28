# SAC Rios del Desierto - Documentación del Sistema

## Tabla de Contenidos
- [Introducción](#introducción)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Documentación de la API](#documentación-de-la-api)
- [Endpoints Principales](#endpoints-principales)
- [Deployment](#deployment)
- [Pruebas Automatizadas](#pruebas-automatizadas)
- [Recursos Adicionales](#recursos-adicionales)

## Introducción

El Sistema de Atención al Cliente (SAC) de Rios del Desierto es una API RESTful desarrollada con Django REST Framework que proporciona funcionalidades completas para la gestión de clientes, generación de reportes y exportación de datos.

### Características Principales
- API RESTful completa con documentación OpenAPI 3.0
- Sistema de búsqueda avanzada de clientes
- Generación de reportes de fidelización
- Exportación de datos en múltiples formatos
- Documentación interactiva con Swagger UI y ReDoc

## Instalación

### Requisitos del Sistema
- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Git

### Proceso de Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/NivekTakedown/Prueba-T-cnica-Ingeniero-de-Desarrollo.git
   cd Prueba-T-cnica-Ingeniero-de-Desarrollo
   ```

2. **Crear entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Preparar la base de datos:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Iniciar el servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```

El servidor estará disponible en: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Configuración

### Variables de Entorno

El sistema utiliza un archivo `.env` para la configuración. Las principales variables son:

- `DEBUG`: Modo de depuración (True/False)
- `SECRET_KEY`: Clave secreta de Django
- `DATABASE_URL`: URL de conexión a la base de datos
- `ALLOWED_HOSTS`: Hosts permitidos separados por comas

Por defecto, el sistema está configurado para usar SQLite como base de datos, ideal para desarrollo y pruebas.

## Documentación de la API

La API cuenta con documentación completa siguiendo el estándar OpenAPI 3.0, accesible a través de múltiples interfaces:

### Interfaces de Documentación

| Interfaz | URL | Descripción |
|----------|-----|-------------|
| **Swagger UI** | `/swagger/` | Documentación interactiva con ejemplos ejecutables |
| **ReDoc** | `/redoc/` | Documentación estática optimizada para lectura |
| **Esquema OpenAPI** | `/api/schema/` | Especificación completa en formato JSON |

### Características de la Documentación

- **Descripciones detalladas** de todos los endpoints y parámetros
- **Ejemplos prácticos** de requests y responses
- **Categorización por tags**: Clientes, Referencias, Exportación, Reportes
- **Especificación completa** de códigos de respuesta HTTP
- **Componentes reutilizables** para modelos de datos comunes
- **Filtrado y búsqueda** de endpoints en la interfaz

### Personalización de Swagger UI

La interfaz Swagger ha sido personalizada con:
- Expansión automática de modelos de datos
- Persistencia de tokens de autorización
- Enlaces directos para compartir endpoints específicos
- Visualización de tiempos de respuesta
- Filtrado rápido de endpoints

## Endpoints Principales

### Gestión de Clientes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/buscar-cliente/` | Búsqueda avanzada de clientes |
| `GET` | `/api/v1/tipos-documento/` | Consulta de tipos de documento disponibles |

### Exportación de Datos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/exportar/` | Exportación de datos de clientes |

### Reportes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET/POST` | `/api/v1/reportes/fidelizacion/` | Generación de reportes de fidelización |

Para ejemplos detallados de cada endpoint, consulta la documentación Swagger UI en tu instancia local.

## Deployment

### Usando Docker (Recomendado)

1. **Construir y ejecutar el contenedor:**
   ```bash
   docker-compose up --build
   ```

2. **Configuración personalizada:**
   Edita el archivo `.env` antes de ejecutar el contenedor para personalizar la configuración.

El servicio estará disponible en el puerto `8000`.

### Deployment Manual

Para deployment en producción:

1. Sigue los pasos de instalación mencionados anteriormente
2. Configura las variables de entorno apropiadas para producción
3. Utiliza un servidor WSGI como Gunicorn
4. Configura un servidor web como Nginx como proxy reverso
5. Implementa HTTPS y otras medidas de seguridad necesarias

## Pruebas Automatizadas

### Configuración de Newman

El proyecto incluye pruebas automatizadas usando Postman y Newman:

1. **Instalar Newman:**
   ```bash
   npm install -g newman
   ```

2. **Ejecutar las colecciones de pruebas:**
   ```bash
   # Pruebas de reportes
   newman run postman/cliente_views_reportar.json
   
   # Pruebas de exportación
   newman run postman/cliente_views_exportar.json
   
   # Pruebas generales de clientes
   newman run postman/cliente_views_tests.json
   ```

### Estructura de Pruebas

Las pruebas están organizadas por funcionalidad:
- **Reportes**: Validación de generación de reportes
- **Exportación**: Verificación de funcionalidades de exportación
- **Gestión de clientes**: Pruebas completas de CRUD y búsqueda

## Buenas Prácticas para Desarrolladores

Al añadir nuevos endpoints, mantén la consistencia siguiendo estos estándares:

1. **Documentación obligatoria:**
   - Utiliza `@extend_schema` en todas las vistas
   - Incluye ejemplos de request y response
   - Documenta todos los parámetros con descripciones claras

2. **Organización:**
   - Categoriza correctamente usando tags
   - Utiliza nombres descriptivos para endpoints
   - Mantén consistencia en la nomenclatura

3. **Respuestas:**
   - Especifica todos los posibles códigos de respuesta HTTP
   - Utiliza componentes reutilizables cuando sea apropiado
   - Proporciona mensajes de error informativos

## Recursos Adicionales

### Enlaces Importantes
- [Repositorio en GitHub](https://github.com/NivekTakedown/Prueba-T-cnica-Ingeniero-de-Desarrollo.git)
- [Documentación técnica](ER.md)
- [Diagrama Entidad-Relación](Diagrama_Entidad_Relacion.svg)

### Soporte y Contribuciones

Para reportar problemas o contribuir al proyecto:
1. Crea un issue en el repositorio de GitHub
2. Sigue las convenciones de código establecidas
3. Incluye pruebas para cualquier funcionalidad nueva
4. Actualiza la documentación según sea necesario

### Contacto

Para consultas técnicas o soporte, consulta la documentación del proyecto o crea un issue en el repositorio oficial.