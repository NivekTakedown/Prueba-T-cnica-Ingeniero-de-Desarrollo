from rest_framework import serializers
from datetime import date, datetime
from decimal import Decimal
import re

from ..models import Producto, Compra, DetalleCompra, Cliente, EstadoCompra, CategoriaProducto
from .reference_serializers import EstadoCompraListSerializer, CategoriaProductoListSerializer


class ProductoSerializer(serializers.ModelSerializer):
    """
    Serializer completo para Producto.
    Incluye validaciones de negocio y campos calculados.
    """
    
    # Campos relacionados
    categoria = CategoriaProductoListSerializer(read_only=True)
    categoria_id = serializers.IntegerField(write_only=True, required=True)
    
    # Campos calculados
    precio_con_descuento = serializers.SerializerMethodField()
    margen_ganancia = serializers.SerializerMethodField()
    comision_venta = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'categoria',
            'categoria_id',
            'precio_base',
            'precio_con_descuento',
            'margen_ganancia',
            'comision_venta',
            'stock',
            'stock_status',
            'activo',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
        read_only_fields = [
            'id',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
    
    def get_precio_con_descuento(self, obj):
        """Calcula el precio con descuento si aplica."""
        if hasattr(obj, 'get_precio_con_descuento'):
            return obj.get_precio_con_descuento()
        return obj.precio_base
    
    def get_margen_ganancia(self, obj):
        """Calcula el margen de ganancia."""
        if hasattr(obj, 'get_margen_ganancia'):
            return obj.get_margen_ganancia()
        return None
    
    def get_comision_venta(self, obj):
        """Calcula la comisión de venta basada en la categoría."""
        if hasattr(obj, 'get_comision_venta'):
            return obj.get_comision_venta()
        return None
    
    def get_stock_status(self, obj):
        """Retorna el estado del stock (disponible, bajo, agotado)."""
        if hasattr(obj, 'get_stock_status'):
            return obj.get_stock_status()
        
        # Fallback manual
        if obj.stock <= 0:
            return 'agotado'
        elif obj.stock < 10:
            return 'bajo'
        else:
            return 'disponible'
    
    def validate_categoria_id(self, value):
        """Valida que la categoría exista y esté activa."""
        try:
            categoria = CategoriaProducto.objects.get(id=value, activo=True)
            return value
        except CategoriaProducto.DoesNotExist:
            raise serializers.ValidationError(
                "La categoría no existe o no está activa"
            )
    
    def validate_codigo(self, value):
        """Valida el código del producto."""
        if not value or not value.strip():
            raise serializers.ValidationError("El código es requerido")
        
        value = value.strip().upper()
        
        if not re.match(r'^[A-Z0-9-_]+$', value):
            raise serializers.ValidationError(
                "El código solo puede contener letras, números, guiones y guiones bajos"
            )
        
        if len(value) < 3 or len(value) > 20:
            raise serializers.ValidationError(
                "El código debe tener entre 3 y 20 caracteres"
            )
        
        return value
    
    def validate_nombre(self, value):
        """Valida el nombre del producto."""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es requerido")
        
        value = value.strip().title()
        
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres"
            )
        
        if len(value) > 200:
            raise serializers.ValidationError(
                "El nombre no puede exceder 200 caracteres"
            )
        
        return value
    
    def validate_precio_base(self, value):
        """Valida el precio base del producto."""
        if value is None:
            raise serializers.ValidationError("El precio base es requerido")
        
        if value <= 0:
            raise serializers.ValidationError(
                "El precio base debe ser mayor a cero"
            )
        
        if value > Decimal('999999999.99'):
            raise serializers.ValidationError(
                "El precio base es demasiado alto"
            )
        
        # Validar que tenga máximo 2 decimales
        if value.as_tuple().exponent < -2:
            raise serializers.ValidationError(
                "El precio base puede tener máximo 2 decimales"
            )
        
        return value
    
    def validate_stock(self, value):
        """Valida el stock disponible."""
        if value is None:
            return 0  # Stock por defecto
        
        if value < 0:
            raise serializers.ValidationError(
                "El stock no puede ser negativo"
            )
        
        if value > 999999:
            raise serializers.ValidationError(
                "El stock es demasiado alto"
            )
        
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        # Validar unicidad del código
        codigo = attrs.get('codigo')
        if codigo:
            query = Producto.objects.filter(codigo=codigo, activo=True)
            
            if self.instance:
                query = query.exclude(id=self.instance.id)
            
            if query.exists():
                raise serializers.ValidationError({
                    'codigo': 'Ya existe un producto activo con este código'
                })
        
        return attrs


class ProductoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de productos.
    Solo incluye campos esenciales.
    """
    
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    precio_con_descuento = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id',
            'codigo',
            'nombre',
            'categoria_nombre',
            'precio_base',
            'precio_con_descuento',
            'stock',
            'stock_status',
            'activo'
        ]
    
    def get_precio_con_descuento(self, obj):
        if hasattr(obj, 'get_precio_con_descuento'):
            return obj.get_precio_con_descuento()
        return obj.precio_base
    
    def get_stock_status(self, obj):
        if hasattr(obj, 'get_stock_status'):
            return obj.get_stock_status()
        
        if obj.stock <= 0:
            return 'agotado'
        elif obj.stock < 10:
            return 'bajo'
        else:
            return 'disponible'


class DetalleCompraSerializer(serializers.ModelSerializer):
    """
    Serializer para DetalleCompra.
    Maneja la relación entre compra y productos.
    """
    
    # Campos relacionados
    producto = ProductoListSerializer(read_only=True)
    producto_id = serializers.IntegerField(write_only=True, required=True)
    
    # Campos calculados
    subtotal_calculado = serializers.SerializerMethodField()
    descuento_aplicado_calculado = serializers.SerializerMethodField()
    comision_detalle = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleCompra
        fields = [
            'id',
            'producto',
            'producto_id',
            'cantidad',
            'precio_unitario',
            'subtotal_producto',
            'subtotal_calculado',
            'descuento_aplicado',
            'descuento_aplicado_calculado',
            'comision_detalle'
        ]
        read_only_fields = [
            'id'
        ]
    
    def get_subtotal_calculado(self, obj):
        """Calcula el subtotal (cantidad * precio)."""
        if hasattr(obj, 'get_subtotal_calculado'):
            return obj.get_subtotal_calculado()
        return obj.cantidad * obj.precio_unitario
    
    def get_descuento_aplicado_calculado(self, obj):
        """Calcula el descuento aplicado en este detalle."""
        if hasattr(obj, 'get_descuento_aplicado'):
            return obj.get_descuento_aplicado()
        return obj.descuento_aplicado
    
    def get_comision_detalle(self, obj):
        """Calcula la comisión de este detalle."""
        if hasattr(obj, 'get_comision_detalle'):
            return obj.get_comision_detalle()
        return Decimal('0.00')
    
    def validate_producto_id(self, value):
        """Valida que el producto exista y esté activo."""
        try:
            producto = Producto.objects.get(id=value, activo=True)
            
            # Verificar stock disponible
            if producto.stock <= 0:
                raise serializers.ValidationError(
                    f"El producto '{producto.nombre}' no tiene stock disponible"
                )
            
            return value
        except Producto.DoesNotExist:
            raise serializers.ValidationError(
                "El producto no existe o no está activo"
            )
    
    def validate_cantidad(self, value):
        """Valida la cantidad del producto."""
        if not value or value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a cero"
            )
        
        if value > 9999:
            raise serializers.ValidationError(
                "La cantidad es demasiado alta"
            )
        
        return value
    
    def validate_precio_unitario(self, value):
        """Valida el precio unitario."""
        if value is None:
            raise serializers.ValidationError(
                "El precio unitario es requerido"
            )
        
        if value <= 0:
            raise serializers.ValidationError(
                "El precio unitario debe ser mayor a cero"
            )
        
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        producto_id = attrs.get('producto_id')
        cantidad = attrs.get('cantidad')
        
        if producto_id and cantidad:
            try:
                producto = Producto.objects.get(id=producto_id)
                
                # Verificar stock suficiente
                if producto.stock < cantidad:
                    raise serializers.ValidationError({
                        'cantidad': f'Stock insuficiente. Disponible: {producto.stock}'
                    })
                
                # Auto-calcular subtotal_producto si no se proporciona
                precio_unitario = attrs.get('precio_unitario')
                if precio_unitario:
                    attrs['subtotal_producto'] = cantidad * precio_unitario
                
            except Producto.DoesNotExist:
                pass  # Ya se validó en validate_producto_id
        
        return attrs


class CompraSerializer(serializers.ModelSerializer):
    """
    Serializer completo para Compra.
    Incluye detalles de compra y validaciones de negocio.
    """
    
    # Campos relacionados
    cliente = serializers.StringRelatedField(read_only=True)
    cliente_id = serializers.IntegerField(write_only=True, required=True)
    estado = EstadoCompraListSerializer(read_only=True)
    estado_id = serializers.IntegerField(write_only=True, required=True)
    
    # Detalles de la compra
    detalles = DetalleCompraSerializer(many=True, required=False)
    
    # Campos calculados
    cantidad_productos = serializers.SerializerMethodField()
    monto_total_calculado = serializers.SerializerMethodField()
    comision_total = serializers.SerializerMethodField()
    resumen_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Compra
        fields = [
            'id',
            'numero_factura',
            'cliente',
            'cliente_id',
            'estado',
            'estado_id',
            'fecha_compra',
            'monto_total',
            'monto_total_calculado',
            'cantidad_productos',
            'comision_total',
            'detalles',
            'resumen_productos',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
        read_only_fields = [
            'id',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
    
    def get_cantidad_productos(self, obj):
        """Retorna la cantidad total de productos."""
        if hasattr(obj, 'get_cantidad_productos'):
            return obj.get_cantidad_productos()
        return obj.detalles.count() if hasattr(obj, 'detalles') else 0
    
    def get_monto_total_calculado(self, obj):
        """Calcula el monto total basado en los detalles."""
        if hasattr(obj, 'get_monto_total_calculado'):
            return obj.get_monto_total_calculado()
        return obj.monto_total
    
    def get_comision_total(self, obj):
        """Calcula la comisión total de la compra."""
        if hasattr(obj, 'get_comision_total'):
            return obj.get_comision_total()
        return Decimal('0.00')
    
    def get_resumen_productos(self, obj):
        """Retorna resumen de productos comprados."""
        if hasattr(obj, 'get_resumen_productos'):
            return obj.get_resumen_productos()
        return []
    
    def validate_cliente_id(self, value):
        """Valida que el cliente exista y esté activo."""
        try:
            cliente = Cliente.objects.get(id=value, activo=True)
            return value
        except Cliente.DoesNotExist:
            raise serializers.ValidationError(
                "El cliente no existe o no está activo"
            )
    
    def validate_estado_id(self, value):
        """Valida que el estado exista y esté activo."""
        try:
            estado = EstadoCompra.objects.get(id=value, activo=True)
            return value
        except EstadoCompra.DoesNotExist:
            raise serializers.ValidationError(
                "El estado no existe o no está activo"
            )
    
    def validate_numero_factura(self, value):
        """Valida el número de factura."""
        if not value or not value.strip():
            raise serializers.ValidationError("El número de factura es requerido")
        
        value = value.strip().upper()
        
        if not re.match(r'^[A-Z0-9-]+$', value):
            raise serializers.ValidationError(
                "El número de factura solo puede contener letras, números y guiones"
            )
        
        if len(value) < 5 or len(value) > 20:
            raise serializers.ValidationError(
                "El número de factura debe tener entre 5 y 20 caracteres"
            )
        
        return value
    
    def validate_fecha_compra(self, value):
        """Valida la fecha de compra."""
        # ✅ CORRECCIÓN: Convertir date a datetime si es necesario
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())
        
        if not value:
            return datetime.now()
        
        if value.date() > date.today():
            raise serializers.ValidationError(
                "La fecha de compra no puede ser futura"
            )
        
        from datetime import timedelta
        fecha_limite = date.today() - timedelta(days=365)
        if value.date() < fecha_limite:
            raise serializers.ValidationError(
                "La fecha de compra no puede ser anterior a un año"
            )
        
        return value
    
    def validate_monto_total(self, value):
        """Valida el monto total de la compra."""
        if value is None:
            raise serializers.ValidationError("El monto total es requerido")
        
        if value <= 0:
            raise serializers.ValidationError(
                "El monto total debe ser mayor a cero"
            )
        
        if value > Decimal('999999999.99'):
            raise serializers.ValidationError(
                "El monto total es demasiado alto"
            )
        
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        numero_factura = attrs.get('numero_factura')
        if numero_factura:
            query = Compra.objects.filter(numero_factura=numero_factura)
            
            if self.instance:
                query = query.exclude(id=self.instance.id)
            
            if query.exists():
                raise serializers.ValidationError({
                    'numero_factura': 'Ya existe una compra con este número de factura'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Crea una compra con sus detalles."""
        detalles_data = validated_data.pop('detalles', [])
        compra = Compra.objects.create(**validated_data)
        
        # Crear detalles de compra
        for detalle_data in detalles_data:
            DetalleCompra.objects.create(compra=compra, **detalle_data)
        
        return compra
    
    def update(self, instance, validated_data):
        """Actualiza una compra y sus detalles."""
        detalles_data = validated_data.pop('detalles', [])
        
        # Actualizar compra
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar detalles (eliminar y recrear)
        if detalles_data:
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                DetalleCompra.objects.create(compra=instance, **detalle_data)
        
        return instance


class CompraResumenSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados de compras."""
    
    cliente_nombre = serializers.CharField(source='cliente.get_nombre_completo', read_only=True)
    cliente_documento = serializers.CharField(source='cliente.numero_documento', read_only=True)
    estado_nombre = serializers.CharField(source='estado.nombre', read_only=True)
    cantidad_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Compra
        fields = [
            'id',
            'numero_factura',
            'cliente_nombre',
            'cliente_documento',
            'estado_nombre',
            'fecha_compra',
            'monto_total',
            'cantidad_productos'
        ]
    
    def get_cantidad_productos(self, obj):
        if hasattr(obj, 'get_cantidad_productos'):
            return obj.get_cantidad_productos()
        return obj.detalles.count() if hasattr(obj, 'detalles') else 0


class CompraCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para creación de compras."""
    
    detalles = DetalleCompraSerializer(many=True, required=True)
    
    class Meta:
        model = Compra
        fields = [
            'numero_factura',
            'cliente_id',
            'estado_id',
            'fecha_compra',
            'detalles'
        ]
    
    def validate_fecha_compra(self, value):
        """Valida y convierte la fecha de compra."""
        # ✅ CORRECCIÓN: Convertir date a datetime
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime.combine(value, datetime.min.time())
        return value
    
    def validate_detalles(self, value):
        """Valida que haya al menos un detalle de compra."""
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "La compra debe tener al menos un producto"
            )
        
        if len(value) > 50:
            raise serializers.ValidationError(
                "La compra no puede tener más de 50 productos diferentes"
            )
        
        return value
    
    def create(self, validated_data):
        """Crea una compra calculando automáticamente el monto total."""
        detalles_data = validated_data.pop('detalles')
        
        # Calcular monto total automáticamente
        monto_total = Decimal('0.00')
        for detalle_data in detalles_data:
            cantidad = detalle_data['cantidad']
            precio = detalle_data['precio_unitario']
            monto_total += cantidad * precio
        
        validated_data['monto_total'] = monto_total
        
        # ✅ CORRECCIÓN: Asegurar que otros campos requeridos estén presentes
        if 'subtotal' not in validated_data:
            validated_data['subtotal'] = monto_total
        if 'descuento_total' not in validated_data:
            validated_data['descuento_total'] = Decimal('0.00')
        if 'iva_total' not in validated_data:
            validated_data['iva_total'] = monto_total * Decimal('0.19')  # 19% IVA
        
        # Crear la compra
        compra = Compra.objects.create(**validated_data)
        
        # Crear los detalles
        for detalle_data in detalles_data:
            DetalleCompra.objects.create(compra=compra, **detalle_data)
        
        return compra


class CompraEstadisticasSerializer(serializers.Serializer):
    """Serializer para estadísticas de compras."""
    
    total_compras = serializers.IntegerField()
    monto_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    monto_promedio = serializers.DecimalField(max_digits=15, decimal_places=2)
    productos_mas_vendidos = serializers.ListField(
        child=serializers.DictField(), 
        required=False
    )
    clientes_frecuentes = serializers.ListField(
        child=serializers.DictField(), 
        required=False
    )
    ventas_por_mes = serializers.ListField(
        child=serializers.DictField(), 
        required=False
    )