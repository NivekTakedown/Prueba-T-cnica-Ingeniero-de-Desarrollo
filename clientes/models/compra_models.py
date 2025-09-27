from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from .reference_models import CategoriaProducto, EstadoCompra
from .cliente_models import Cliente


class Producto(models.Model):
    """
    Catálogo de productos disponibles para la venta.
    Cada producto pertenece a una categoría y tiene información de precios e inventario.
    """
    
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.PROTECT,
        related_name='productos',
        help_text="Categoría a la que pertenece el producto"
    )
    
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único del producto (SKU)"
    )
    
    nombre = models.CharField(
        max_length=200,
        help_text="Nombre del producto"
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del producto"
    )
    
    # Información de precios
    precio_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio base del producto (sin descuentos ni impuestos)"
    )
    
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        help_text="Porcentaje de descuento aplicable (0-100)"
    )
    
    iva_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('19.00'),  # IVA colombiano estándar
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        help_text="Porcentaje de IVA aplicable (0-100)"
    )
    
    # Información de inventario
    stock = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad disponible en inventario"
    )
    
    stock_minimo = models.PositiveIntegerField(
        default=0,
        help_text="Stock mínimo para alertas de reposición"
    )
    
    # Información adicional
    peso = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Peso del producto en kilogramos"
    )
    
    dimensiones = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Dimensiones del producto (ej: 10x15x20 cm)"
    )
    
    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Marca del producto"
    )
    
    # Campos de control
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el producto está activo para la venta"
    )
    
    destacado = models.BooleanField(
        default=False,
        help_text="Indica si el producto está destacado en el catálogo"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'productos'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        
        indexes = [
            models.Index(fields=['categoria', 'activo'], name='idx_producto_categoria_activo'),
            models.Index(fields=['codigo'], name='idx_producto_codigo'),
            models.Index(fields=['nombre'], name='idx_producto_nombre'),
            models.Index(fields=['precio_base'], name='idx_producto_precio'),
            models.Index(fields=['stock'], name='idx_producto_stock'),
            models.Index(fields=['destacado', 'activo'], name='idx_producto_destacado'),
        ]
        
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        super().clean()
        
        # Normalizar código
        if self.codigo:
            self.codigo = self.codigo.upper().strip()
        
        # Normalizar nombre
        if self.nombre:
            self.nombre = self.nombre.strip()
        
        # Validar stock mínimo
        if self.stock_minimo > self.stock:
            self.stock_minimo = self.stock
    
    def get_precio_con_descuento(self):
        """Calcula el precio después del descuento"""
        if self.descuento_porcentaje > 0:
            descuento = self.precio_base * (self.descuento_porcentaje / 100)
            return self.precio_base - descuento
        return self.precio_base
    
    def get_precio_final(self):
        """Calcula el precio final incluyendo IVA"""
        precio_con_descuento = self.get_precio_con_descuento()
        iva = precio_con_descuento * (self.iva_porcentaje / 100)
        return precio_con_descuento + iva
    
    def tiene_stock_disponible(self, cantidad=1):
        """Verifica si hay stock suficiente para la cantidad solicitada"""
        return self.stock >= cantidad and self.activo
    
    def necesita_reposicion(self):
        """Indica si el producto necesita reposición de stock"""
        return self.stock <= self.stock_minimo
    
    def reducir_stock(self, cantidad):
        """Reduce el stock del producto"""
        if not self.tiene_stock_disponible(cantidad):
            raise ValidationError(f'Stock insuficiente. Disponible: {self.stock}, Solicitado: {cantidad}')
        
        self.stock -= cantidad
        self.save(update_fields=['stock'])
    
    def aumentar_stock(self, cantidad):
        """Aumenta el stock del producto"""
        self.stock += cantidad
        self.save(update_fields=['stock'])


class Compra(models.Model):
    """
    Cabecera de las transacciones de compra realizadas por los clientes.
    Almacena información general de la compra y totales calculados.
    """
    
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='compras',
        help_text="Cliente que realizó la compra"
    )
    
    estado = models.ForeignKey(
        EstadoCompra,
        on_delete=models.PROTECT,
        related_name='compras',
        help_text="Estado actual de la compra"
    )
    
    # Información de la compra
    numero_factura = models.CharField(
        max_length=50,
        unique=True,
        help_text="Número único de factura"
    )
    
    fecha_compra = models.DateTimeField(
        help_text="Fecha y hora en que se realizó la compra"
    )
    
    # Totales calculados
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Subtotal antes de descuentos e impuestos"
    )
    
    descuento_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total de descuentos aplicados"
    )
    
    iva_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total de IVA aplicado"
    )
    
    monto_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Monto total de la compra"
    )
    
    # Información adicional
    observaciones = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones adicionales de la compra"
    )
    
    metodo_pago = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('EFECTIVO', 'Efectivo'),
            ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
            ('TARJETA_DEBITO', 'Tarjeta de Débito'),
            ('PSE', 'PSE'),
            ('NEQUI', 'Nequi'),
            ('DAVIPLATA', 'Daviplata'),
            ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ],
        help_text="Método de pago utilizado"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'compras'
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        
        indexes = [
            models.Index(fields=['cliente', 'fecha_compra'], name='idx_compra_cliente_fecha'),
            models.Index(fields=['estado'], name='idx_compra_estado'),
            models.Index(fields=['numero_factura'], name='idx_compra_factura'),
            models.Index(fields=['fecha_compra'], name='idx_compra_fecha'),
            models.Index(fields=['monto_total'], name='idx_compra_monto'),
        ]
        
        ordering = ['-fecha_compra']
    
    def __str__(self):
        return f"Factura {self.numero_factura} - {self.cliente.get_nombre_completo()} - ${self.monto_total:,.2f}"
    
    def clean(self):
        """Validaciones personalizadas del modelo"""
        super().clean()
        
        # Validar que el monto total sea coherente
        total_calculado = self.subtotal - self.descuento_total + self.iva_total
        if abs(self.monto_total - total_calculado) > Decimal('0.01'):
            raise ValidationError('El monto total no coincide con la suma de subtotal - descuentos + IVA')
    
    def calcular_totales(self):
        """
        Calcula todos los totales basado en los detalles de la compra.
        Debe llamarse después de agregar/modificar productos.
        """
        detalles = self.detalles.all()
        
        self.subtotal = sum(detalle.get_subtotal_antes_descuento() for detalle in detalles)
        self.descuento_total = sum(detalle.descuento_aplicado for detalle in detalles)
        self.iva_total = sum(detalle.iva_aplicado for detalle in detalles)
        self.monto_total = sum(detalle.subtotal_producto for detalle in detalles)
        
        self.save(update_fields=['subtotal', 'descuento_total', 'iva_total', 'monto_total'])
    
    def agregar_producto(self, producto, cantidad):
        """Agrega un producto a la compra o actualiza la cantidad si ya existe"""
        detalle, created = DetalleCompra.objects.get_or_create(
            compra=self,
            producto=producto,
            defaults={
                'cantidad': cantidad,
                'precio_unitario': producto.precio_base
            }
        )
        
        if not created:
            detalle.cantidad += cantidad
            detalle.save()
        
        # Recalcular totales
        self.calcular_totales()
        
        return detalle
    
    def get_cantidad_productos(self):
        """Retorna la cantidad total de productos en la compra"""
        return self.detalles.aggregate(
            total=models.Sum('cantidad')
        )['total'] or 0
    
    def get_cantidad_items_unicos(self):
        """Retorna la cantidad de productos únicos en la compra"""
        return self.detalles.count()
    
    def puede_cancelarse(self):
        """Indica si la compra puede ser cancelada"""
        return self.estado.codigo in ['PENDIENTE', 'PAGADA']
    
    def cancelar(self, observacion=None):
        """Cancela la compra y devuelve el stock"""
        if not self.puede_cancelarse():
            raise ValidationError('Esta compra no puede ser cancelada')
        
        # Devolver stock de todos los productos
        for detalle in self.detalles.all():
            detalle.producto.aumentar_stock(detalle.cantidad)
        
        # Cambiar estado a cancelada
        estado_cancelada = EstadoCompra.objects.get(codigo='CANCELADA')
        self.estado = estado_cancelada
        
        if observacion:
            self.observaciones = f"{self.observaciones or ''}\nCancelada: {observacion}".strip()
        
        self.save()
    
    @classmethod
    def generar_numero_factura(cls):
        """Genera un número de factura único"""
        from django.utils import timezone
        import random
        
        fecha = timezone.now()
        prefijo = f"FAC-{fecha.year}{fecha.month:02d}{fecha.day:02d}"
        
        # Buscar el último número del día
        ultimo_numero = cls.objects.filter(
            numero_factura__startswith=prefijo
        ).order_by('-numero_factura').first()
        
        if ultimo_numero:
            try:
                ultimo_seq = int(ultimo_numero.numero_factura.split('-')[-1])
                nuevo_seq = ultimo_seq + 1
            except (ValueError, IndexError):
                nuevo_seq = random.randint(1000, 9999)
        else:
            nuevo_seq = 1001
        
        return f"{prefijo}-{nuevo_seq:04d}"


class DetalleCompra(models.Model):
    """
    Tabla intermedia que implementa la relación muchos a muchos entre COMPRA y PRODUCTO.
    Almacena información específica de cada producto en una compra particular.
    """
    
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name='detalles',
        help_text="Compra a la que pertenece este detalle"
    )
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='detalles_compra',
        help_text="Producto incluido en la compra"
    )
    
    # Información de la compra específica
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Cantidad del producto comprado"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Precio unitario al momento de la compra (sin descuentos ni IVA)"
    )
    
    # Cálculos aplicados
    descuento_aplicado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Descuento total aplicado a este producto"
    )
    
    iva_aplicado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="IVA total aplicado a este producto"
    )
    
    subtotal_producto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Subtotal final calculado para este producto"
    )
    
    # Metadatos al momento de la compra (para auditoría)
    descuento_porcentaje_momento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Porcentaje de descuento que tenía el producto al momento de la compra"
    )
    
    iva_porcentaje_momento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('19.00'),
        help_text="Porcentaje de IVA que tenía el producto al momento de la compra"
    )
    
    class Meta:
        db_table = 'detalles_compra'
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'
        
        indexes = [
            models.Index(fields=['compra'], name='idx_detalle_compra'),
            models.Index(fields=['producto'], name='idx_detalle_producto'),
        ]
        
        constraints = [
            models.UniqueConstraint(
                fields=['compra', 'producto'],
                name='unique_compra_producto'
            ),
        ]
        
        ordering = ['id']
    
    def __str__(self):
        return f"{self.compra.numero_factura} - {self.producto.nombre} (x{self.cantidad})"
    
    def save(self, *args, **kwargs):
        """Override save para calcular totales automáticamente"""
        self.calcular_totales()
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """Calcula todos los totales para este detalle"""
        # Subtotal antes de descuentos
        subtotal_base = self.precio_unitario * self.cantidad
        
        # Calcular descuento
        if self.descuento_porcentaje_momento > 0:
            self.descuento_aplicado = subtotal_base * (self.descuento_porcentaje_momento / 100)
        else:
            self.descuento_aplicado = Decimal('0.00')
        
        # Subtotal después de descuentos
        subtotal_con_descuento = subtotal_base - self.descuento_aplicado
        
        # Calcular IVA sobre el subtotal con descuento
        self.iva_aplicado = subtotal_con_descuento * (self.iva_porcentaje_momento / 100)
        
        # Subtotal final
        self.subtotal_producto = subtotal_con_descuento + self.iva_aplicado
    
    def get_subtotal_antes_descuento(self):
        """Retorna el subtotal antes de aplicar descuentos"""
        return self.precio_unitario * self.cantidad
    
    def get_precio_unitario_final(self):
        """Retorna el precio unitario final (incluyendo descuentos e IVA)"""
        return self.subtotal_producto / self.cantidad if self.cantidad > 0 else Decimal('0.00')
    
    def get_ahorro_por_descuento(self):
        """Retorna el ahorro total por descuentos en este producto"""
        return self.descuento_aplicado
    
    @classmethod
    def crear_desde_producto(cls, compra, producto, cantidad):
        """
        Método de conveniencia para crear un detalle desde un producto actual.
        Captura los valores del producto al momento de la compra.
        """
        return cls.objects.create(
            compra=compra,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio_base,
            descuento_porcentaje_momento=producto.descuento_porcentaje,
            iva_porcentaje_momento=producto.iva_porcentaje
        )