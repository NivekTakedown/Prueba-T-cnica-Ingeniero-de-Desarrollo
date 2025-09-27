from django.db import models


class TipoDocumento(models.Model):
    """
    Tipos de documentos de identificación válidos para clientes.
    Ej: RUT, Cédula, Pasaporte, etc.
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        help_text="Código único del tipo de documento (ej: RUT, CC, PA)"
    )
    nombre = models.CharField(
        max_length=50,
        help_text="Nombre descriptivo del tipo de documento"
    )
    formato_validacion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Expresión regular para validar el formato del documento"
    )
    longitud_minima = models.PositiveSmallIntegerField(
        default=1,
        help_text="Longitud mínima del número de documento"
    )
    longitud_maxima = models.PositiveSmallIntegerField(
        default=20,
        help_text="Longitud máxima del número de documento"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el tipo de documento está activo"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tipos_documento'
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documento'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        
        if self.longitud_minima > self.longitud_maxima:
            raise ValidationError('La longitud mínima no puede ser mayor que la máxima')
        
        # Convertir código a mayúsculas
        if self.codigo:
            self.codigo = self.codigo.upper()


class EstadoCompra(models.Model):
    """
    Estados posibles de una compra en el sistema.
    Ej: Pendiente, Pagada, Cancelada, Reembolsada
    """
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único del estado (ej: PENDING, PAID, CANCELLED)"
    )
    nombre = models.CharField(
        max_length=50,
        help_text="Nombre descriptivo del estado"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del estado"
    )
    es_estado_final = models.BooleanField(
        default=False,
        help_text="Indica si es un estado final (no permite cambios posteriores)"
    )
    permite_reembolso = models.BooleanField(
        default=False,
        help_text="Indica si permite solicitar reembolso"
    )
    color_hex = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text="Color para mostrar en interfaz (formato hex: #RRGGBB)"
    )
    orden = models.PositiveSmallIntegerField(
        default=0,
        help_text="Orden para mostrar en listas"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el estado está activo"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'estados_compra'
        verbose_name = 'Estado de Compra'
        verbose_name_plural = 'Estados de Compra'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        import re
        
        # Convertir código a mayúsculas
        if self.codigo:
            self.codigo = self.codigo.upper()
        
        # Validar formato de color hex
        if self.color_hex and not re.match(r'^#[0-9A-Fa-f]{6}$', self.color_hex):
            raise ValidationError('El color debe estar en formato hexadecimal (#RRGGBB)')


class CategoriaProducto(models.Model):
    """
    Categorías de productos para clasificación y reportes.
    Ej: Electrónicos, Ropa, Hogar, etc.
    """
    codigo = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único de la categoría"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre de la categoría"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción de la categoría"
    )
    categoria_padre = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='subcategorias',
        help_text="Categoría padre (para jerarquías)"
    )
    imagen_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL de imagen representativa de la categoría"
    )
    comision_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Porcentaje de comisión para esta categoría"
    )
    requiere_garantia = models.BooleanField(
        default=False,
        help_text="Indica si los productos de esta categoría requieren garantía"
    )
    dias_garantia_defecto = models.PositiveIntegerField(
        default=30,
        help_text="Días de garantía por defecto para productos de esta categoría"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si la categoría está activa"
    )
    orden = models.PositiveSmallIntegerField(
        default=0,
        help_text="Orden para mostrar en listas"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categorias_producto'
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Producto'
        ordering = ['orden', 'nombre']
        indexes = [
            models.Index(fields=['categoria_padre']),
            models.Index(fields=['activo', 'orden']),
        ]

    def __str__(self):
        if self.categoria_padre:
            return f"{self.categoria_padre.nombre} > {self.nombre}"
        return self.nombre

    def clean(self):
        """Validaciones personalizadas del modelo"""
        from django.core.exceptions import ValidationError
        
        # Convertir código a mayúsculas
        if self.codigo:
            self.codigo = self.codigo.upper()
        
        # Validar que no se asigne como padre a sí misma
        if self.categoria_padre == self:
            raise ValidationError('Una categoría no puede ser padre de sí misma')
        
        # Validar porcentaje de comisión
        if self.comision_porcentaje < 0 or self.comision_porcentaje > 100:
            raise ValidationError('El porcentaje de comisión debe estar entre 0 y 100')

    def get_ruta_completa(self):
        """Retorna la ruta completa de la categoría incluyendo padres"""
        ruta = [self.nombre]
        categoria_actual = self.categoria_padre
        
        while categoria_actual:
            ruta.insert(0, categoria_actual.nombre)
            categoria_actual = categoria_actual.categoria_padre
        
        return ' > '.join(ruta)

    def get_subcategorias_activas(self):
        """Retorna todas las subcategorías activas"""
        return self.subcategorias.filter(activo=True).order_by('orden', 'nombre')

    def es_categoria_raiz(self):
        """Indica si es una categoría raíz (sin padre)"""
        return self.categoria_padre is None

    @property
    def nivel_jerarquia(self):
        """Retorna el nivel en la jerarquía (0 para raíz)"""
        nivel = 0
        categoria_actual = self.categoria_padre
        
        while categoria_actual:
            nivel += 1
            categoria_actual = categoria_actual.categoria_padre
            
        return nivel