from rest_framework import serializers
from ..models import TipoDocumento, EstadoCompra, CategoriaProducto


class TipoDocumentoSerializer(serializers.ModelSerializer):
    """
    Serializer para TipoDocumento.
    Usado para listar tipos de documento disponibles en la API.
    """
    
    class Meta:
        model = TipoDocumento
        fields = [
            'id',
            'codigo',
            'nombre', 
            'descripcion',
            'formato_validacion',
            'longitud_minima',
            'longitud_maxima',
            'activo',
            'fecha_creacion'
        ]
        read_only_fields = ['id', 'fecha_creacion']
    
    def validate_codigo(self, value):
        """
        Valida que el código sea único y esté en mayúsculas.
        """
        if not value:
            raise serializers.ValidationError("El código es requerido")
        
        # Convertir a mayúsculas
        value = value.upper().strip()
        
        # Validar longitud
        if len(value) < 2 or len(value) > 10:
            raise serializers.ValidationError(
                "El código debe tener entre 2 y 10 caracteres"
            )
        
        # Validar que solo contenga letras y números
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                "El código solo puede contener letras, números y guiones bajos"
            )
        
        return value
    
    def validate_formato_validacion(self, value):
        """
        Valida que el formato de validación sea una expresión regular válida.
        """
        if value:
            try:
                import re
                re.compile(value)
            except re.error:
                raise serializers.ValidationError(
                    "El formato de validación debe ser una expresión regular válida"
                )
        return value
    
    def validate(self, attrs):
        """
        Validación a nivel de objeto.
        """
        longitud_min = attrs.get('longitud_minima', 0)
        longitud_max = attrs.get('longitud_maxima', 0)
        
        if longitud_min and longitud_max and longitud_min > longitud_max:
            raise serializers.ValidationError({
                'longitud_minima': 'La longitud mínima no puede ser mayor que la máxima'
            })
        
        return attrs


class TipoDocumentoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de tipos de documento.
    Solo incluye los campos esenciales para dropdowns y selecciones.
    """
    
    class Meta:
        model = TipoDocumento
        fields = ['id', 'codigo', 'nombre','descripcion', 'activo']


class EstadoCompraSerializer(serializers.ModelSerializer):
    """
    Serializer para EstadoCompra.
    Usado para gestionar los estados de las compras.
    """
    
    class Meta:
        model = EstadoCompra
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'activo',
            'fecha_creacion'
        ]
        read_only_fields = ['id', 'fecha_creacion']
    
    def validate_codigo(self, value):
        """
        Valida el código del estado.
        """
        if not value:
            raise serializers.ValidationError("El código es requerido")
        
        # Convertir a mayúsculas
        value = value.upper().strip()
        
        # Lista de códigos válidos
        codigos_validos = [
            'PENDIENTE', 
            'COMPLETADA', 
            'CANCELADA', 
            'PROCESANDO',
            'ENVIADO',
            'ENTREGADO'
        ]
        
        if value not in codigos_validos:
            raise serializers.ValidationError(
                f"El código debe ser uno de: {', '.join(codigos_validos)}"
            )
        
        return value
    
    def validate_nombre(self, value):
        """
        Valida el nombre del estado.
        """
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres"
            )
        
        return value.strip().title()


class EstadoCompraListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de estados.
    """
    
    class Meta:
        model = EstadoCompra
        fields = ['id', 'codigo', 'nombre', 'activo']


class CategoriaProductoSerializer(serializers.ModelSerializer):
    """
    Serializer para CategoriaProducto.
    Incluye validaciones de negocio y campos calculados.
    """
    
    # Campo calculado para mostrar información adicional
    productos_count = serializers.SerializerMethodField()
    comision_decimal = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoriaProducto
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'comision_porcentaje',
            'comision_decimal',
            'activo',
            'fecha_creacion',
            'productos_count'
        ]
        read_only_fields = [
            'id', 
            'fecha_creacion', 
            'productos_count',
            'comision_decimal'
        ]
    
    def get_productos_count(self, obj):
        """
        Retorna la cantidad de productos activos en esta categoría.
        """
        return obj.productos.filter(activo=True).count()
    
    def get_comision_decimal(self, obj):
        """
        Retorna la comisión como decimal (para cálculos).
        """
        if obj.comision_porcentaje:
            return float(obj.comision_porcentaje) / 100
        return 0.0
    
    def validate_codigo(self, value):
        """
        Valida el código de la categoría.
        """
        if not value:
            raise serializers.ValidationError("El código es requerido")
        
        # Convertir a mayúsculas
        value = value.upper().strip()
        
        # Validar longitud
        if len(value) < 2 or len(value) > 20:
            raise serializers.ValidationError(
                "El código debe tener entre 2 y 20 caracteres"
            )
        
        # Validar formato (solo letras, números y guiones)
        import re
        if not re.match(r'^[A-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                "El código solo puede contener letras mayúsculas, números, guiones y guiones bajos"
            )
        
        return value
    
    def validate_nombre(self, value):
        """
        Valida el nombre de la categoría.
        """
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres"
            )
        
        if len(value.strip()) > 100:
            raise serializers.ValidationError(
                "El nombre no puede exceder 100 caracteres"
            )
        
        return value.strip().title()
    
    def validate_comision_porcentaje(self, value):
        """
        Valida el porcentaje de comisión.
        """
        if value is not None:
            if value < 0:
                raise serializers.ValidationError(
                    "La comisión no puede ser negativa"
                )
            
            if value > 100:
                raise serializers.ValidationError(
                    "La comisión no puede ser mayor al 100%"
                )
            
            # Validar que tenga máximo 2 decimales
            if value.as_tuple().exponent < -2:
                raise serializers.ValidationError(
                    "La comisión puede tener máximo 2 decimales"
                )
        
        return value
    
    def validate(self, attrs):
        """
        Validación a nivel de objeto.
        """
        # Validar unicidad del código si se está creando
        if not self.instance:  # Creación
            codigo = attrs.get('codigo')
            if codigo and CategoriaProducto.objects.filter(
                codigo=codigo, 
                activo=True
            ).exists():
                raise serializers.ValidationError({
                    'codigo': 'Ya existe una categoría activa con este código'
                })
        
        return attrs


class CategoriaProductoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de categorías.
    Usado en dropdowns y selecciones.
    """
    
    productos_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoriaProducto
        fields = [
            'id', 
            'codigo', 
            'nombre', 
            'comision_porcentaje',
            'productos_count',
            'activo'
        ]
    
    def get_productos_count(self, obj):
        """Cantidad de productos activos en la categoría."""
        return getattr(obj, '_productos_count', 0)


class CategoriaProductoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para creación de categorías.
    Incluye validaciones adicionales para nuevos registros.
    """
    
    class Meta:
        model = CategoriaProducto
        fields = [
            'codigo',
            'nombre', 
            'descripcion',
            'comision_porcentaje'
        ]
    
    def create(self, validated_data):
        """
        Crea una nueva categoría con validaciones adicionales.
        """
        # Asegurar que el código esté en mayúsculas
        validated_data['codigo'] = validated_data['codigo'].upper()
        
        # Asegurar que esté activa por defecto
        validated_data['activo'] = True
        
        return super().create(validated_data)


# Serializers para respuestas de API estructuradas
class ApiResponseSerializer(serializers.Serializer):
    """
    Serializer base para respuestas estructuradas de la API.
    """
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(max_length=500, required=False)
    data = serializers.JSONField(required=False)
    errors = serializers.JSONField(required=False)
    
    
class TipoDocumentoResponseSerializer(ApiResponseSerializer):
    """
    Respuesta estructurada para endpoints de tipos de documento.
    """
    data = TipoDocumentoListSerializer(many=True, required=False)


class EstadoCompraResponseSerializer(ApiResponseSerializer):
    """
    Respuesta estructurada para endpoints de estados de compra.
    """
    data = EstadoCompraListSerializer(many=True, required=False)


class CategoriaProductoResponseSerializer(ApiResponseSerializer):
    """
    Respuesta estructurada para endpoints de categorías.
    """
    data = CategoriaProductoListSerializer(many=True, required=False)