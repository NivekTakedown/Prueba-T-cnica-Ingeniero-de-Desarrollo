from rest_framework import serializers
from django.core.validators import RegexValidator
from datetime import date, datetime
import re
from decimal import Decimal

from ..models import Cliente, TipoDocumento
from .reference_serializers import TipoDocumentoListSerializer


class ClienteSerializer(serializers.ModelSerializer):
    """
    Serializer completo para Cliente.
    Incluye todas las validaciones de negocio y campos relacionados.
    """
    
    # Campos relacionados
    tipo_documento = TipoDocumentoListSerializer(read_only=True)
    tipo_documento_id = serializers.IntegerField(write_only=True, required=True)
    
    # Campos calculados
    nombre_completo = serializers.SerializerMethodField()
    edad = serializers.SerializerMethodField()
    es_vip = serializers.SerializerMethodField()
    resumen_comercial = serializers.SerializerMethodField()
    
    # Campos de estadísticas (solo lectura)
    total_compras = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        read_only=True
    )
    numero_compras = serializers.IntegerField(read_only=True)
    fecha_ultima_compra = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Cliente
        fields = [
            'id',
            'tipo_documento',
            'tipo_documento_id',
            'numero_documento',
            'nombre',
            'apellido',
            'nombre_completo',
            'correo',
            'telefono',
            'fecha_nacimiento',
            'edad',
            'genero',
            'acepta_marketing',
            'total_compras',
            'numero_compras',
            'fecha_ultima_compra',
            'es_vip',
            'resumen_comercial',
            'activo',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
        read_only_fields = [
            'id',
            'total_compras',
            'numero_compras',
            'fecha_ultima_compra',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
    
    def get_nombre_completo(self, obj):
        """Retorna el nombre completo del cliente."""
        return obj.get_nombre_completo()
    
    def get_edad(self, obj):
        """Calcula la edad del cliente."""
        return obj.get_edad()
    
    def get_es_vip(self, obj):
        """Indica si el cliente es VIP."""
        return obj.es_cliente_vip()
    
    def get_resumen_comercial(self, obj):
        """Retorna resumen comercial del cliente."""
        return obj.get_resumen_comercial()
    
    def validate_tipo_documento_id(self, value):
        """
        Valida que el tipo de documento exista y esté activo.
        """
        try:
            tipo_documento = TipoDocumento.objects.get(id=value, activo=True)
            return value
        except TipoDocumento.DoesNotExist:
            raise serializers.ValidationError(
                "El tipo de documento no existe o no está activo"
            )
    
    def validate_numero_documento(self, value):
        """
        Valida el formato del número de documento.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El número de documento es requerido")
        
        # Normalizar: quitar espacios y convertir a mayúsculas
        value = value.strip().upper()
        
        # Validación básica de longitud
        if len(value) < 5 or len(value) > 20:
            raise serializers.ValidationError(
                "El número de documento debe tener entre 5 y 20 caracteres"
            )
        
        # Validaciones específicas por tipo (si está disponible en el contexto)
        if hasattr(self, 'initial_data'):
            tipo_documento_id = self.initial_data.get('tipo_documento_id')
            if tipo_documento_id:
                self._validate_documento_por_tipo(value, tipo_documento_id)
        
        return value
    
    def _validate_documento_por_tipo(self, numero, tipo_documento_id):
        """
        Valida el número de documento según su tipo específico.
        """
        try:
            tipo_doc = TipoDocumento.objects.get(id=tipo_documento_id)
            
            # Validar longitud específica
            if tipo_doc.longitud_minima and len(numero) < tipo_doc.longitud_minima:
                raise serializers.ValidationError(
                    f"El documento tipo {tipo_doc.codigo} debe tener mínimo {tipo_doc.longitud_minima} caracteres"
                )
            
            if tipo_doc.longitud_maxima and len(numero) > tipo_doc.longitud_maxima:
                raise serializers.ValidationError(
                    f"El documento tipo {tipo_doc.codigo} debe tener máximo {tipo_doc.longitud_maxima} caracteres"
                )
            
            # Validar formato con regex si está definido
            if tipo_doc.formato_validacion:
                if not re.match(tipo_doc.formato_validacion, numero):
                    raise serializers.ValidationError(
                        f"El formato del documento {tipo_doc.codigo} no es válido"
                    )
                    
        except TipoDocumento.DoesNotExist:
            pass  # Ya se validó en validate_tipo_documento_id
    
    def validate_nombre(self, value):
        """
        Valida el nombre del cliente.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es requerido")
        
        value = value.strip().title()
        
        # Validar longitud
        if len(value) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres")
        
        if len(value) > 50:
            raise serializers.ValidationError("El nombre no puede exceder 50 caracteres")
        
        # Validar que solo contenga letras y espacios
        if not re.match(r"^[A-Za-záéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise serializers.ValidationError(
                "El nombre solo puede contener letras y espacios"
            )
        
        return value
    
    def validate_apellido(self, value):
        """
        Valida el apellido del cliente.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El apellido es requerido")
        
        value = value.strip().title()
        
        # Validar longitud
        if len(value) < 2:
            raise serializers.ValidationError("El apellido debe tener al menos 2 caracteres")
        
        if len(value) > 50:
            raise serializers.ValidationError("El apellido no puede exceder 50 caracteres")
        
        # Validar que solo contenga letras y espacios
        if not re.match(r"^[A-Za-záéíóúÁÉÍÓÚñÑ\s]+$", value):
            raise serializers.ValidationError(
                "El apellido solo puede contener letras y espacios"
            )
        
        return value
    
    def validate_correo(self, value):
        """
        Valida el formato del correo electrónico.
        """
        if not value:
            return value  # Correo es opcional
        
        value = value.strip().lower()
        
        # Validación de formato básico
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError("El formato del correo electrónico no es válido")
        
        # Validar longitud
        if len(value) > 254:
            raise serializers.ValidationError("El correo electrónico es demasiado largo")
        
        return value
    
    def validate_telefono(self, value):
        """
        Valida el formato del teléfono.
        """
        if not value:
            return value  # Teléfono es opcional
        
        value = value.strip()
        
        # Permitir formato internacional (+57), nacional y con separadores
        telefono_regex = r'^(\+\d{1,3}[-.\s]?)?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}$'
        if not re.match(telefono_regex, value):
            raise serializers.ValidationError(
                "El formato del teléfono no es válido. Use formato: +57 3XX XXX XXXX"
            )
        
        # Validar longitud después de limpiar caracteres especiales
        telefono_limpio = re.sub(r'[^\d]', '', value)
        if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
            raise serializers.ValidationError(
                "El teléfono debe tener entre 7 y 15 dígitos"
            )
        
        return value
    
    def validate_fecha_nacimiento(self, value):
        """
        Valida la fecha de nacimiento.
        """
        if not value:
            return value  # Fecha de nacimiento es opcional
        
        # Validar que no sea futura
        if value > date.today():
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser futura"
            )
        
        # Validar edad mínima (13 años) y máxima (120 años)
        today = date.today()
        edad = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        
        if edad < 13:
            raise serializers.ValidationError(
                "El cliente debe tener al menos 13 años"
            )
        
        if edad > 120:
            raise serializers.ValidationError(
                "La fecha de nacimiento no es válida"
            )
        
        return value
    
    def validate_genero(self, value):
        """
        Valida el género del cliente.
        """
        if value and value not in ['M', 'F', 'O']:
            raise serializers.ValidationError(
                "El género debe ser 'M' (Masculino), 'F' (Femenino) u 'O' (Otro)"
            )
        return value
    
    def validate(self, attrs):
        """
        Validación a nivel de objeto.
        """
        # Validar unicidad del documento (solo en creación o si cambió el documento)
        numero_documento = attrs.get('numero_documento')
        tipo_documento_id = attrs.get('tipo_documento_id')
        
        if numero_documento and tipo_documento_id:
            query = Cliente.objects.filter(
                numero_documento=numero_documento,
                tipo_documento_id=tipo_documento_id,
                activo=True
            )
            
            # Excluir el objeto actual si estamos actualizando
            if self.instance:
                query = query.exclude(id=self.instance.id)
            
            if query.exists():
                raise serializers.ValidationError({
                    'numero_documento': 'Ya existe un cliente activo con este documento'
                })
        
        return attrs


class ClienteBusquedaSerializer(serializers.Serializer):
    """
    Serializer para búsqueda de clientes.
    Solo incluye los campos necesarios para realizar búsquedas.
    """
    
    tipo_documento = serializers.CharField(
        max_length=10,
        required=True,
        help_text="Código del tipo de documento (CC, NIT, PA, etc.)"
    )
    numero_documento = serializers.CharField(
        max_length=20,
        required=True,
        help_text="Número del documento de identificación"
    )
    incluir_compras = serializers.BooleanField(
        default=False,
        help_text="Si incluir información de compras del cliente"
    )
    incluir_estadisticas = serializers.BooleanField(
        default=True,
        help_text="Si incluir estadísticas comerciales del cliente"
    )
    
    def validate_tipo_documento(self, value):
        """
        Valida que el tipo de documento exista.
        """
        if not value:
            raise serializers.ValidationError("El tipo de documento es requerido")
        
        value = value.strip().upper()
        
        # Verificar que existe y está activo
        if not TipoDocumento.objects.filter(codigo=value, activo=True).exists():
            raise serializers.ValidationError(
                f"El tipo de documento '{value}' no existe o no está activo"
            )
        
        return value
    
    def validate_numero_documento(self, value):
        """
        Valida el número de documento para búsqueda.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El número de documento es requerido")
        
        return value.strip().upper()


class ClienteResponseSerializer(ClienteSerializer):
    """
    Serializer para respuestas API de cliente.
    Incluye información adicional de compras si se solicita.
    """
    
    # Información adicional de compras
    compras_recientes = serializers.SerializerMethodField()
    productos_favoritos = serializers.SerializerMethodField()
    
    class Meta(ClienteSerializer.Meta):
        fields = ClienteSerializer.Meta.fields + [
            'compras_recientes',
            'productos_favoritos'
        ]
    
    def get_compras_recientes(self, obj):
        """
        Retorna las últimas 5 compras del cliente si se incluyen compras.
        """
        incluir_compras = self.context.get('incluir_compras', False)
        if not incluir_compras:
            return None
        
        from ..models import Compra
        compras = Compra.objects.filter(
            cliente=obj,
            estado__codigo='COMPLETADA'
        ).order_by('-fecha_compra')[:5]
        
        return [
            {
                'numero_factura': compra.numero_factura,
                'fecha_compra': compra.fecha_compra,
                'monto_total': compra.monto_total,
                'cantidad_productos': compra.get_cantidad_productos()
            }
            for compra in compras
        ]
    
    def get_productos_favoritos(self, obj):
        """
        Retorna los 5 productos más comprados por el cliente.
        """
        incluir_compras = self.context.get('incluir_compras', False)
        if not incluir_compras:
            return None
        
        from django.db.models import Sum, Count
        from ..models import DetalleCompra
        
        productos_favoritos = DetalleCompra.objects.filter(
            compra__cliente=obj,
            compra__estado__codigo='COMPLETADA'
        ).values(
            'producto__nombre',
            'producto__codigo'
        ).annotate(
            veces_comprado=Count('id'),
            cantidad_total=Sum('cantidad'),
            monto_total=Sum('subtotal_producto')
        ).order_by('-veces_comprado')[:5]
        
        return list(productos_favoritos)


class ClienteListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de clientes.
    Solo incluye campos esenciales para tablas y grillas.
    """
    
    tipo_documento_codigo = serializers.CharField(source='tipo_documento.codigo', read_only=True)
    nombre_completo = serializers.SerializerMethodField()
    ultima_compra = serializers.DateTimeField(source='fecha_ultima_compra', read_only=True)
    
    class Meta:
        model = Cliente
        fields = [
            'id',
            'tipo_documento_codigo',
            'numero_documento',
            'nombre_completo',
            'correo',
            'telefono',
            'total_compras',
            'numero_compras',
            'ultima_compra',
            'activo'
        ]
    
    def get_nombre_completo(self, obj):
        return obj.get_nombre_completo()


class ClienteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para creación de clientes.
    Incluye validaciones adicionales para nuevos registros.
    """
    
    tipo_documento_codigo = serializers.CharField(
        write_only=True,
        help_text="Código del tipo de documento (CC, NIT, PA, etc.)"
    )
    
    class Meta:
        model = Cliente
        fields = [
            'tipo_documento_codigo',
            'numero_documento',
            'nombre',
            'apellido',
            'correo',
            'telefono',
            'fecha_nacimiento',
            'genero',
            'acepta_marketing'
        ]
    
    def validate_tipo_documento_codigo(self, value):
        """
        Valida y convierte el código a objeto TipoDocumento.
        """
        if not value:
            raise serializers.ValidationError("El tipo de documento es requerido")
        
        value = value.strip().upper()
        
        try:
            tipo_documento = TipoDocumento.objects.get(codigo=value, activo=True)
            return tipo_documento
        except TipoDocumento.DoesNotExist:
            raise serializers.ValidationError(
                f"El tipo de documento '{value}' no existe o no está activo"
            )
    
    def validate_numero_documento(self, value):
        """
        Valida el número de documento para creación.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El número de documento es requerido")
        
        value = value.strip().upper()
        
        # Validación básica de longitud
        if len(value) < 5 or len(value) > 20:
            raise serializers.ValidationError(
                "El número de documento debe tener entre 5 y 20 caracteres"
            )
        
        return value
    
    def validate_nombre(self, value):
        """Heredar validación del serializer principal."""
        return ClienteSerializer.validate_nombre(self, value)
    
    def validate_apellido(self, value):
        """Heredar validación del serializer principal.""" 
        return ClienteSerializer.validate_apellido(self, value)
    
    def validate_correo(self, value):
        """Heredar validación del serializer principal."""
        return ClienteSerializer.validate_correo(self, value)
    
    def validate_telefono(self, value):
        """Heredar validación del serializer principal."""
        return ClienteSerializer.validate_telefono(self, value)
    
    def validate_fecha_nacimiento(self, value):
        """Heredar validación del serializer principal."""
        return ClienteSerializer.validate_fecha_nacimiento(self, value)
    
    def validate_genero(self, value):
        """Heredar validación del serializer principal."""
        return ClienteSerializer.validate_genero(self, value)
    
    def validate(self, attrs):
        """
        Validación a nivel de objeto incluyendo unicidad.
        """
        # Validar unicidad del documento
        numero_documento = attrs.get('numero_documento')
        tipo_documento = attrs.get('tipo_documento_codigo')
        
        if numero_documento and tipo_documento:
            if Cliente.objects.filter(
                numero_documento=numero_documento,
                tipo_documento=tipo_documento,
                activo=True
            ).exists():
                raise serializers.ValidationError({
                    'numero_documento': 'Ya existe un cliente activo con este documento'
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        Crea un nuevo cliente con el tipo de documento convertido.
        """
        tipo_documento = validated_data.pop('tipo_documento_codigo')
        validated_data['tipo_documento'] = tipo_documento
        
        # Asegurar que esté activo por defecto
        validated_data['activo'] = True
        
        return super().create(validated_data)


class ClienteUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para actualización de clientes.
    Permite actualizaciones parciales con validaciones específicas.
    """
    
    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'apellido', 
            'correo',
            'telefono',
            'fecha_nacimiento',
            'genero',
            'acepta_marketing'
        ]
        # IMPORTANTE: Hacer todos los campos opcionales para actualizaciones
        extra_kwargs = {
            'nombre': {'required': False},
            'apellido': {'required': False},
            'correo': {'required': False},         # ← AGREGAR ESTA LÍNEA
            'telefono': {'required': False},       # ← AGREGAR ESTA LÍNEA  
            'fecha_nacimiento': {'required': False}, # ← AGREGAR ESTA LÍNEA
            'genero': {'required': False},         # ← AGREGAR ESTA LÍNEA
            'acepta_marketing': {'required': False}, # ← AGREGAR ESTA LÍNEA
        }
    
    def validate_nombre(self, value):
        """Validar nombre si se proporciona."""
        if value:  # Solo validar si no es None/vacío
            return ClienteSerializer.validate_nombre(self, value)
        return value
    
    def validate_apellido(self, value):
        """Validar apellido si se proporciona."""
        if value:  # Solo validar si no es None/vacío
            return ClienteSerializer.validate_apellido(self, value)
        return value
    
    def validate_correo(self, value):
        """Validar correo si se proporciona."""
        return ClienteSerializer.validate_correo(self, value)
    
    def validate_telefono(self, value):
        """Validar teléfono si se proporciona."""
        return ClienteSerializer.validate_telefono(self, value)
    
    def validate_fecha_nacimiento(self, value):
        """Validar fecha de nacimiento si se proporciona."""
        return ClienteSerializer.validate_fecha_nacimiento(self, value)
    
    def validate_genero(self, value):
        """Validar género si se proporciona."""
        return ClienteSerializer.validate_genero(self, value)