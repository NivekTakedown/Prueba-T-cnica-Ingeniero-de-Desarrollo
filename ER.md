# Modelamiento de Base de Datos - Sistema SAC Rios del Desierto

## Descripción General
El modelo de datos está diseñado para soportar un sistema de consulta de clientes y generación de reportes de fidelización, cumpliendo con los requerimientos de la prueba técnica de Falabella Colombia.

## Entidades y Atributos

### 1. TIPO_DOCUMENTO
Tabla de referencia para los tipos de documentos de identificación.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único |
| `codigo` | STRING | Código corto (NIT, CC, PA) |
| `descripcion` | STRING | Descripción completa (Nit, Cédula, Pasaporte) |
| `activo` | BOOLEAN | Estado de vigencia del tipo |
| `fecha_creacion` | DATETIME | Timestamp de creación |

**Datos de ejemplo:**
- 1, "CC", "Cédula de Ciudadanía", true
- 2, "NIT", "Número de Identificación Tributaria", true
- 3, "PA", "Pasaporte", true

### 2. CLIENTE
Entidad principal que almacena la información básica de los clientes.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único del cliente |
| `tipo_documento_id` | INT (FK) | Referencia a TIPO_DOCUMENTO |
| `numero_documento` | STRING (UNIQUE) | Número de documento único |
| `nombre` | STRING | Nombre del cliente |
| `apellido` | STRING | Apellido del cliente |
| `correo` | STRING | Correo electrónico |
| `telefono` | STRING | Número telefónico |
| `activo` | BOOLEAN | Estado del cliente |
| `fecha_creacion` | DATETIME | Timestamp de creación |
| `fecha_actualizacion` | DATETIME | Timestamp de última actualización |

### 3. CATEGORIA_PRODUCTO
Clasificación de productos para mejor organización del catálogo.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único |
| `nombre` | STRING | Nombre de la categoría |
| `descripcion` | STRING | Descripción de la categoría |
| `activo` | BOOLEAN | Estado de la categoría |

### 4. PRODUCTO
Catálogo de productos disponibles para la venta.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único del producto |
| `categoria_id` | INT (FK) | Referencia a CATEGORIA_PRODUCTO |
| `nombre` | STRING | Nombre del producto |
| `descripcion` | STRING | Descripción detallada |
| `precio_base` | DECIMAL | Precio base del producto |
| `descuento_porcentaje` | DECIMAL | Porcentaje de descuento aplicable |
| `iva_porcentaje` | DECIMAL | Porcentaje de IVA |
| `stock` | INT | Cantidad disponible en inventario |
| `activo` | BOOLEAN | Estado del producto |
| `fecha_creacion` | DATETIME | Timestamp de creación |

### 5. ESTADO_COMPRA
Tabla de referencia para los estados de las compras.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único |
| `codigo` | STRING | Código corto del estado |
| `descripcion` | STRING | Descripción del estado |
| `activo` | BOOLEAN | Estado de vigencia |

**Estados posibles:**
- PENDIENTE: Compra iniciada pero no completada
- COMPLETADA: Compra finalizada exitosamente
- CANCELADA: Compra cancelada

### 6. COMPRA
Cabecera de las transacciones de compra realizadas por los clientes.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único de la compra |
| `cliente_id` | INT (FK) | Referencia al CLIENTE |
| `numero_factura` | STRING (UNIQUE) | Número único de factura |
| `subtotal` | DECIMAL | Subtotal antes de descuentos e impuestos |
| `descuento_total` | DECIMAL | Total de descuentos aplicados |
| `iva_total` | DECIMAL | Total de IVA aplicado |
| `monto_total` | DECIMAL | Monto total de la compra |
| `fecha_compra` | DATETIME | Fecha y hora de la compra |
| `estado` | STRING | Estado actual de la compra |
| `fecha_creacion` | DATETIME | Timestamp de creación |

### 7. DETALLE_COMPRA
Tabla intermedia que implementa la relación muchos a muchos entre COMPRA y PRODUCTO.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INT (PK) | Identificador único del detalle |
| `compra_id` | INT (FK) | Referencia a COMPRA |
| `producto_id` | INT (FK) | Referencia a PRODUCTO |
| `cantidad` | INT | Cantidad del producto comprado |
| `precio_unitario` | DECIMAL | Precio unitario al momento de la compra |
| `descuento_aplicado` | DECIMAL | Descuento aplicado a este producto |
| `iva_aplicado` | DECIMAL | IVA aplicado a este producto |
| `subtotal_producto` | DECIMAL | Subtotal calculado para este producto |

## Relaciones

### Relaciones Uno a Muchos (1:N)
- **TIPO_DOCUMENTO** → **CLIENTE**: Un tipo de documento puede ser usado por múltiples clientes
- **CLIENTE** → **COMPRA**: Un cliente puede realizar múltiples compras
- **CATEGORIA_PRODUCTO** → **PRODUCTO**: Una categoría puede contener múltiples productos
- **COMPRA** → **DETALLE_COMPRA**: Una compra puede tener múltiples productos
- **PRODUCTO** → **DETALLE_COMPRA**: Un producto puede estar en múltiples compras
- **ESTADO_COMPRA** → **COMPRA**: Un estado puede ser asignado a múltiples compras

### Relaciones Muchos a Muchos (N:M)
- **COMPRA** ↔ **PRODUCTO**: Implementada a través de la tabla **DETALLE_COMPRA**

## Ventajas del Modelo

### 1. Normalización
- **Tercera Forma Normal (3NF)**: Elimina redundancias y dependencias transitivas
- **Integridad referencial**: Garantizada mediante llaves foráneas
- **Consistencia de datos**: Tablas de referencia para tipos y estados

### 2. Flexibilidad
- **Escalabilidad**: Fácil agregar nuevos tipos de documento o estados
- **Extensibilidad**: Estructura permite agregar nuevos campos sin afectar funcionalidad existente
- **Mantenibilidad**: Cambios en una entidad no afectan otras

### 3. Optimización para Reportes
- **Índices naturales**: En campos de búsqueda frecuente (numero_documento, fecha_compra)
- **Agregaciones eficientes**: Estructura optimizada para SUM, GROUP BY
- **Filtros rápidos**: Campos de fecha y estado facilitan consultas de rango

## Consultas Clave para los Requerimientos

### Búsqueda de Cliente (Punto 3)
```sql
SELECT c.*, td.descripcion as tipo_documento_desc
FROM cliente c
INNER JOIN tipo_documento td ON c.tipo_documento_id = td.id
WHERE c.numero_documento = ? AND c.activo = true
```

### Reporte de Fidelización (Punto 5)
```sql
SELECT 
    c.numero_documento,
    c.nombre,
    c.apellido,
    c.correo,
    c.telefono,
    SUM(co.monto_total) as total_ultimo_mes
FROM cliente c
INNER JOIN compra co ON c.id = co.cliente_id
WHERE co.fecha_compra >= date('now', '-1 month')
  AND co.estado = 'COMPLETADA'
  AND c.activo = true
GROUP BY c.id
HAVING total_ultimo_mes > 5000000
ORDER BY total_ultimo_mes DESC
```

### Detalle de Compras por Cliente
```sql
SELECT 
    co.numero_factura,
    co.fecha_compra,
    co.monto_total,
    COUNT(dc.id) as cantidad_productos
FROM compra co
INNER JOIN detalle_compra dc ON co.id = dc.compra_id
WHERE co.cliente_id = ?
GROUP BY co.id
ORDER BY co.fecha_compra DESC
```

## Consideraciones Técnicas

### Índices Recomendados
- `cliente.numero_documento` (UNIQUE)
- `compra.cliente_id`
- `compra.fecha_compra`
- `detalle_compra.compra_id`
- `detalle_compra.producto_id`

### Restricciones de Integridad
- **NOT NULL**: Campos obligatorios como nombres, números de documento
- **CHECK**: Validaciones de rango para porcentajes (0-100)
- **UNIQUE**: Número de documento, número de factura
- **FOREIGN KEY**: Todas las referencias entre tablas

### Auditoria
- Campos de timestamp en todas las tablas principales
- Campo `activo` para soft delete
- Histórico de estados en las compras

