from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.core.exceptions import ValidationError
import re
from .reference_models import TipoDocumento


class Cliente(models.Model):
    """
    Modelo principal para almacenar información de clientes.
    Cada cliente está identificado únicamente por su tipo y número de documento.
    """
    
    # Relación con tipo de documento
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,  # No permitir eliminar tipos de documento en uso
        related_name='clientes',
        help_text="Tipo de documento de identificación del cliente"
    )
    
    numero_documento = models.CharField(
        max_length=50,
        help_text="Número de documento de identificación"
    )
    
    # Información personal básica
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre(s) del cliente"
    )
    
    apellido = models.CharField(
        max_length=100,
        help_text="Apellido(s) del cliente"
    )
    
    # Información de contacto
    correo = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        validators=[EmailValidator()],
        help_text="Correo electrónico del cliente"
    )
    
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[\+]?[0-9\s\-\(\)]{7,20}$',
                message='El teléfono debe tener entre 7 y 20 caracteres y puede incluir +, espacios, guiones y paréntesis'
            )
        ],
        help_text="Número telefónico del cliente"
    )
    
    # Información adicional
    direccion = models.TextField(
        blank=True,
        null=True,
        help_text="Dirección residencial del cliente"
    )
    
    ciudad = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Ciudad de residencia"
    )
    
    departamento = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Departamento o estado de residencia"
    )
    
    codigo_postal = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Código postal"
    )
    
    # Información comercial
    fecha_nacimiento = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de nacimiento del cliente"
    )
    
    genero = models.CharField(
        max_length=1,
        choices=[
            ('M', 'Masculino'),
            ('F', 'Femenino'),
            ('O', 'Otro'),
            ('N', 'Prefiero no decir')
        ],
        blank=True,
        null=True,
        help_text="Género del cliente"
    )
    
    acepta_marketing = models.BooleanField(
        default=False,
        help_text="Indica si el cliente acepta recibir comunicaciones de marketing"
    )
    
    # Campos de control
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el cliente está activo en el sistema"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación del registro"
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de la última actualización"
    )
    
    # Campos calculados/cache (para optimización)
    total_compras = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        help_text="Total acumulado de todas las compras del cliente"
    )
    
    numero_compras = models.PositiveIntegerField(
        default=0,
        help_text="Número total de compras realizadas"
    )
    
    fecha_ultima_compra = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fecha de la última compra realizada"
    )
    
    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        
        # Índices para optimización de consultas
        indexes = [
            models.Index(fields=['tipo_documento', 'numero_documento'], name='idx_cliente_documento'),
            models.Index(fields=['correo'], name='idx_cliente_correo'),
            models.Index(fields=['telefono'], name='idx_cliente_telefono'),
            models.Index(fields=['activo', 'fecha_creacion'], name='idx_cliente_activo_fecha'),
            models.Index(fields=['total_compras'], name='idx_cliente_total_compras'),
            models.Index(fields=['fecha_ultima_compra'], name='idx_cliente_ultima_compra'),
        ]
        
        # Restricciones únicas
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_documento', 'numero_documento'],
                name='unique_cliente_documento'
            ),
        ]
        
        # Ordenamiento por defecto
        ordering = ['-fecha_creacion', 'apellido', 'nombre']
    
    def __str__(self):
        return f"{self.get_nombre_completo()} ({self.tipo_documento.codigo}: {self.numero_documento})"
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        super().clean()
        
        # Normalizar datos
        if self.nombre:
            self.nombre = self.nombre.strip().title()
        if self.apellido:
            self.apellido = self.apellido.strip().title()
        if self.correo:
            self.correo = self.correo.strip().lower()
        if self.numero_documento:
            self.numero_documento = self.numero_documento.strip().upper()
        
        # Validar documento según tipo
        if self.tipo_documento and self.numero_documento:
            self._validar_documento()
        
        # Validar que el correo sea único si se proporciona
        if self.correo:
            self._validar_correo_unico()
        
        # Validar fecha de nacimiento
        if self.fecha_nacimiento:
            self._validar_fecha_nacimiento()
    
    def _validar_documento(self):
        """Valida el número de documento según el tipo"""
        tipo_doc = self.tipo_documento
        numero = self.numero_documento
        
        # Validar longitud
        if len(numero) < tipo_doc.longitud_minima or len(numero) > tipo_doc.longitud_maxima:
            raise ValidationError(
                f'El {tipo_doc.nombre} debe tener entre {tipo_doc.longitud_minima} '
                f'y {tipo_doc.longitud_maxima} caracteres'
            )
        
        # Validar formato si existe regex
        if tipo_doc.formato_validacion:
            if not re.match(tipo_doc.formato_validacion, numero):
                raise ValidationError(
                    f'El formato del {tipo_doc.nombre} no es válido'
                )
    
    def _validar_correo_unico(self):
        """Valida que el correo sea único entre clientes activos"""
        if self.correo:
            qs = Cliente.objects.filter(correo=self.correo, activo=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('Ya existe un cliente activo con este correo electrónico')
    
    def _validar_fecha_nacimiento(self):
        """Valida que la fecha de nacimiento sea coherente"""
        from django.utils import timezone
        from datetime import date, timedelta
        
        hoy = timezone.now().date()
        hace_150_años = hoy - timedelta(days=150*365)
        
        if self.fecha_nacimiento > hoy:
            raise ValidationError('La fecha de nacimiento no puede ser futura')
        
        if self.fecha_nacimiento < hace_150_años:
            raise ValidationError('La fecha de nacimiento no puede ser mayor a 150 años')
    
    def get_nombre_completo(self):
        """Retorna el nombre completo del cliente"""
        return f"{self.nombre} {self.apellido}".strip()
    
    def get_documento_completo(self):
        """Retorna el documento en formato legible"""
        return f"{self.tipo_documento.codigo}: {self.numero_documento}"
    
    def get_edad(self):
        """Calcula la edad del cliente si tiene fecha de nacimiento"""
        if not self.fecha_nacimiento:
            return None
        
        from django.utils import timezone
        hoy = timezone.now().date()
        edad = hoy.year - self.fecha_nacimiento.year
        
        # Ajustar si no ha cumplido años este año
        if hoy.month < self.fecha_nacimiento.month or (
            hoy.month == self.fecha_nacimiento.month and 
            hoy.day < self.fecha_nacimiento.day
        ):
            edad -= 1
            
        return edad
    
    def es_cliente_vip(self, monto_minimo=5000000):
        """Determina si el cliente es VIP basado en su total de compras"""
        return self.total_compras >= monto_minimo
    
    def get_resumen_comercial(self):
        """Retorna un resumen de la actividad comercial del cliente"""
        return {
            'total_compras': float(self.total_compras),
            'numero_compras': self.numero_compras,
            'promedio_compra': float(self.total_compras / self.numero_compras) if self.numero_compras > 0 else 0,
            'fecha_ultima_compra': self.fecha_ultima_compra,
            'es_vip': self.es_cliente_vip(),
        }
    
    def actualizar_estadisticas_compras(self):
        """
        Actualiza las estadísticas de compras del cliente.
        Debe llamarse cuando se crea/modifica una compra.
        """
        from django.db.models import Sum, Count, Max
        
        # Obtener estadísticas de compras completadas
        stats = self.compras.filter(estado__codigo='COMPLETADA').aggregate(
            total=Sum('monto_total'),
            cantidad=Count('id'),
            ultima_fecha=Max('fecha_compra')
        )
        
        self.total_compras = stats['total'] or 0
        self.numero_compras = stats['cantidad'] or 0
        self.fecha_ultima_compra = stats['ultima_fecha']
        
        # Guardar sin triggear clean() para evitar validaciones innecesarias
        self.save(update_fields=['total_compras', 'numero_compras', 'fecha_ultima_compra'])
    
    def desactivar(self, razon=None):
        """Desactiva el cliente (soft delete)"""
        self.activo = False
        self.save(update_fields=['activo'])
    
    def reactivar(self):
        """Reactiva el cliente"""
        self.activo = True
        self.save(update_fields=['activo'])

    @classmethod
    def buscar_por_documento(cls, tipo_documento_codigo, numero_documento):
        """
        Busca un cliente por tipo y número de documento.
        Método de conveniencia para la búsqueda principal del sistema.
        """
        try:
            return cls.objects.select_related('tipo_documento').get(
                tipo_documento__codigo=tipo_documento_codigo.upper(),
                numero_documento=numero_documento.upper(),
                activo=True
            )
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def buscar_por_correo(cls, correo):
        """Busca un cliente por correo electrónico"""
        try:
            return cls.objects.select_related('tipo_documento').get(
                correo=correo.lower(),
                activo=True
            )
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def obtener_clientes_vip(cls, monto_minimo=5000000, fecha_desde=None):
        """
        Obtiene clientes VIP basado en el total de compras.
        Opcionalmente filtra por fecha de última compra.
        """
        qs = cls.objects.filter(
            total_compras__gte=monto_minimo,
            activo=True
        ).select_related('tipo_documento')
        
        if fecha_desde:
            qs = qs.filter(fecha_ultima_compra__gte=fecha_desde)
        
        return qs.order_by('-total_compras')