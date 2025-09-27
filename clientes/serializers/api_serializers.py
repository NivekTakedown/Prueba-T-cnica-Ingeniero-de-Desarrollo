"""
Serializers específicos para Request/Response de las APIs del sistema.
Estos serializers manejan la comunicación con el frontend y validan
los datos de entrada y salida de los endpoints principales.
"""

from rest_framework import serializers
from datetime import date, datetime, timedelta
from decimal import Decimal
import re

from ..models import Cliente, TipoDocumento, Compra, Producto
from .cliente_serializers import ClienteResponseSerializer
from .compra_serializers import CompraResumenSerializer


class BusquedaClienteRequestSerializer(serializers.Serializer):
    """
    Serializer para validar la búsqueda de clientes por documento.
    Endpoint: POST /api/v1/clientes/buscar/
    """
    
    tipo_documento = serializers.ChoiceField(
        choices=[
            ('CC', 'Cédula de Ciudadanía'),
            ('NIT', 'Número de Identificación Tributaria'),
            ('PA', 'Pasaporte'),
            ('CE', 'Cédula de Extranjería'),
            ('TI', 'Tarjeta de Identidad')
        ],
        required=True,
        help_text="Tipo de documento de identificación"
    )
    
    numero_documento = serializers.CharField(
        max_length=20,
        min_length=5,
        required=True,
        help_text="Número del documento de identificación"
    )
    
    # Parámetros opcionales para filtrar información
    incluir_compras = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Incluir historial de compras del cliente"
    )
    
    limite_compras = serializers.IntegerField(
        default=10,
        min_value=1,
        max_value=50,
        required=False,
        help_text="Número máximo de compras a incluir"
    )
    
    solo_ultimo_mes = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Solo incluir compras del último mes"
    )
    
    def validate_numero_documento(self, value):
        """Valida el formato del número de documento."""
        if not value or not value.strip():
            raise serializers.ValidationError("El número de documento es requerido")
        
        value = value.strip()
        
        # Validar que solo contenga números, letras y guiones
        if not re.match(r'^[A-Za-z0-9-]+$', value):
            raise serializers.ValidationError(
                "El número de documento solo puede contener letras, números y guiones"
            )
        
        return value.upper()
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        tipo_documento = attrs.get('tipo_documento')
        numero_documento = attrs.get('numero_documento')
        
        # Validaciones específicas por tipo de documento
        if tipo_documento == 'CC':
            # Cédula debe ser solo números
            if not numero_documento.isdigit():
                raise serializers.ValidationError({
                    'numero_documento': 'La cédula de ciudadanía debe contener solo números'
                })
            
            if len(numero_documento) < 6 or len(numero_documento) > 12:
                raise serializers.ValidationError({
                    'numero_documento': 'La cédula debe tener entre 6 y 12 dígitos'
                })
        
        elif tipo_documento == 'NIT':
            # NIT puede tener guión
            if not re.match(r'^\d{9,12}-?\d?$', numero_documento):
                raise serializers.ValidationError({
                    'numero_documento': 'Formato de NIT inválido'
                })
        
        elif tipo_documento == 'PA':
            # Pasaporte: letras y números
            if len(numero_documento) < 6 or len(numero_documento) > 10:
                raise serializers.ValidationError({
                    'numero_documento': 'El pasaporte debe tener entre 6 y 10 caracteres'
                })
        
        return attrs


class BusquedaClienteResponseSerializer(serializers.Serializer):
    """
    Serializer para la respuesta de búsqueda de clientes.
    Incluye información completa del cliente y sus compras.
    """
    
    # Información del cliente
    cliente = ClienteResponseSerializer()
    
    # Estadísticas de compras
    estadisticas_compras = serializers.SerializerMethodField()
    
    # Historial de compras (opcional)
    compras = CompraResumenSerializer(many=True, required=False)
    
    # Información del procesamiento
    fecha_consulta = serializers.DateTimeField(default=datetime.now)
    parametros_busqueda = serializers.DictField(required=False)
    
    def get_estadisticas_compras(self, obj):
        """Calcula estadísticas de compras del cliente."""
        cliente = obj.get('cliente')
        if not cliente:
            return None
        
        try:
            # Obtener compras del cliente
            compras = Compra.objects.filter(
                cliente=cliente,
                estado__codigo='COMPLETADA'
            )
            
            # Estadísticas generales
            total_compras = compras.count()
            
            if total_compras == 0:
                return {
                    'total_compras': 0,
                    'monto_total_historico': Decimal('0.00'),
                    'monto_promedio': Decimal('0.00'),
                    'ultima_compra': None,
                    'compras_ultimo_mes': 0,
                    'monto_ultimo_mes': Decimal('0.00')
                }
            
            # Cálculos
            monto_total = sum(compra.monto_total for compra in compras)
            monto_promedio = monto_total / total_compras if total_compras > 0 else Decimal('0.00')
            ultima_compra = compras.order_by('-fecha_compra').first()
            
            # Compras del último mes
            fecha_limite = datetime.now() - timedelta(days=30)
            compras_ultimo_mes = compras.filter(fecha_compra__gte=fecha_limite)
            monto_ultimo_mes = sum(compra.monto_total for compra in compras_ultimo_mes)
            
            return {
                'total_compras': total_compras,
                'monto_total_historico': monto_total,
                'monto_promedio': monto_promedio,
                'ultima_compra': ultima_compra.fecha_compra if ultima_compra else None,
                'compras_ultimo_mes': compras_ultimo_mes.count(),
                'monto_ultimo_mes': monto_ultimo_mes
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando estadísticas: {str(e)}'
            }


class ExportacionRequestSerializer(serializers.Serializer):
    """
    Serializer para validar las solicitudes de exportación.
    Endpoint: POST /api/v1/exportar/
    """
    
    FORMATOS_EXPORTACION = [
        ('csv', 'CSV - Comma Separated Values'),
        ('excel', 'Excel - Microsoft Excel'),
        ('txt', 'TXT - Texto plano')
    ]
    
    # Datos del cliente a exportar
    tipo_documento = serializers.ChoiceField(
        choices=[
            ('CC', 'Cédula de Ciudadanía'),
            ('NIT', 'Número de Identificación Tributaria'),
            ('PA', 'Pasaporte'),
            ('CE', 'Cédula de Extranjería'),
            ('TI', 'Tarjeta de Identidad')
        ],
        required=True
    )
    
    numero_documento = serializers.CharField(
        max_length=20,
        min_length=5,
        required=True
    )
    
    # Formato de exportación
    formato = serializers.ChoiceField(
        choices=FORMATOS_EXPORTACION,
        default='csv',
        required=False,
        help_text="Formato del archivo a exportar"
    )
    
    # Opciones de exportación
    incluir_compras = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Incluir información de compras"
    )
    
    incluir_productos = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Incluir detalle de productos en cada compra"
    )
    
    solo_ultimo_mes = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Solo exportar compras del último mes"
    )
    
    # Configuración del archivo
    nombre_archivo = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Nombre personalizado para el archivo (sin extensión)"
    )
    
    def validate_numero_documento(self, value):
        """Reutiliza la validación del serializer de búsqueda."""
        return BusquedaClienteRequestSerializer().validate_numero_documento(value)
    
    def validate_nombre_archivo(self, value):
        """Valida el nombre del archivo."""
        if value:
            # Remover caracteres no permitidos en nombres de archivo
            value = re.sub(r'[<>:"/\\|?*]', '_', value.strip())
            
            if len(value) < 3:
                raise serializers.ValidationError(
                    "El nombre del archivo debe tener al menos 3 caracteres"
                )
        
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        # Reutilizar validación de documento
        tipo_documento = attrs.get('tipo_documento')
        numero_documento = attrs.get('numero_documento')
        
        # Validar que el cliente exista
        try:
            from ..repositories.cliente_repository import ClienteRepository
            repo = ClienteRepository()
            cliente = repo.get_by_documento(tipo_documento, numero_documento)
            if not cliente:
                raise serializers.ValidationError(
                    "No se encontró un cliente con los datos proporcionados"
                )
        except Exception as e:
            raise serializers.ValidationError(
                f"Error validando cliente: {str(e)}"
            )
        
        # Generar nombre de archivo si no se proporciona
        if not attrs.get('nombre_archivo'):
            attrs['nombre_archivo'] = f'cliente_{numero_documento}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        return attrs


class ReporteFidelizacionRequestSerializer(serializers.Serializer):
    """
    Serializer para validar solicitudes del reporte de fidelización.
    Endpoint: GET/POST /api/v1/reportes/fidelizacion/
    """
    
    # Parámetros de filtro
    fecha_inicio = serializers.DateField(
        required=False,
        help_text="Fecha de inicio para el cálculo (por defecto: último mes)"
    )
    
    fecha_fin = serializers.DateField(
        required=False,
        help_text="Fecha de fin para el cálculo (por defecto: hoy)"
    )
    
    monto_minimo = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('5000000.00'),
        min_value=Decimal('0.01'),
        required=False,
        help_text="Monto mínimo para ser considerado cliente VIP"
    )
    
    # Opciones de exportación
    exportar_excel = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Generar archivo Excel automáticamente"
    )
    
    incluir_detalle_compras = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Incluir detalle de compras de cada cliente"
    )
    
    limite_resultados = serializers.IntegerField(
        default=100,
        min_value=1,
        max_value=1000,
        required=False,
        help_text="Número máximo de clientes a incluir en el reporte"
    )
    
    def validate_fecha_inicio(self, value):
        """Valida la fecha de inicio."""
        if value and value > date.today():
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser futura"
            )
        return value
    
    def validate_fecha_fin(self, value):
        """Valida la fecha de fin."""
        if value and value > date.today():
            raise serializers.ValidationError(
                "La fecha de fin no puede ser futura"
            )
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto."""
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        
        # Configurar fechas por defecto
        if not fecha_fin:
            attrs['fecha_fin'] = date.today()
        
        if not fecha_inicio:
            # Por defecto: último mes
            attrs['fecha_inicio'] = attrs['fecha_fin'] - timedelta(days=30)
        
        # Validar que fecha_inicio < fecha_fin
        if attrs['fecha_inicio'] >= attrs['fecha_fin']:
            raise serializers.ValidationError(
                "La fecha de inicio debe ser anterior a la fecha de fin"
            )
        
        # Validar rango máximo (por performance)
        rango_dias = (attrs['fecha_fin'] - attrs['fecha_inicio']).days
        if rango_dias > 365:
            raise serializers.ValidationError(
                "El rango de fechas no puede ser mayor a 365 días"
            )
        
        return attrs


class ReporteFidelizacionResponseSerializer(serializers.Serializer):
    """
    Serializer para la respuesta del reporte de fidelización.
    """
    
    # Información del reporte
    parametros_reporte = serializers.DictField()
    fecha_generacion = serializers.DateTimeField(default=datetime.now)
    
    # Estadísticas generales
    estadisticas_generales = serializers.SerializerMethodField()
    
    # Lista de clientes VIP
    clientes_vip = serializers.SerializerMethodField()
    
    # Información del archivo Excel (si se genera)
    archivo_excel = serializers.SerializerMethodField()
    
    def get_estadisticas_generales(self, obj):
        """Calcula estadísticas generales del reporte."""
        return {
            'total_clientes_vip': len(obj.get('clientes_vip', [])),
            'monto_total_periodo': obj.get('monto_total_periodo', Decimal('0.00')),
            'monto_promedio_vip': obj.get('monto_promedio_vip', Decimal('0.00')),
            'rango_fechas': {
                'inicio': obj.get('fecha_inicio'),
                'fin': obj.get('fecha_fin')
            }
        }
    
    def get_clientes_vip(self, obj):
        """Serializa la lista de clientes VIP."""
        clientes = obj.get('clientes_vip', [])
        resultado = []
        
        for cliente_data in clientes:
            resultado.append({
                'documento': f"{cliente_data['tipo_documento']} {cliente_data['numero_documento']}",
                'nombre_completo': f"{cliente_data['nombre']} {cliente_data['apellido']}",
                'correo': cliente_data['correo'],
                'telefono': cliente_data['telefono'],
                'total_compras_periodo': cliente_data['total_compras'],
                'monto_total_periodo': cliente_data['monto_total'],
                'numero_transacciones': cliente_data['numero_transacciones'],
                'fecha_ultima_compra': cliente_data.get('fecha_ultima_compra')
            })
        
        return resultado
    
    def get_archivo_excel(self, obj):
        """Información del archivo Excel generado."""
        if obj.get('archivo_excel_generado'):
            return {
                'generado': True,
                'nombre_archivo': obj.get('nombre_archivo_excel'),
                'ruta_descarga': obj.get('url_descarga'),
                'tamaño_archivo': obj.get('tamaño_archivo_bytes'),
                'fecha_generacion': obj.get('fecha_generacion_archivo')
            }
        return {'generado': False}


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer estándar para respuestas de error.
    """
    
    error = serializers.BooleanField(default=True)
    mensaje = serializers.CharField()
    codigo_error = serializers.CharField(required=False)
    detalles = serializers.DictField(required=False)
    timestamp = serializers.DateTimeField(default=datetime.now)


class SuccessResponseSerializer(serializers.Serializer):
    """
    Serializer estándar para respuestas exitosas.
    """
    
    success = serializers.BooleanField(default=True)
    mensaje = serializers.CharField(default="Operación exitosa")
    data = serializers.DictField(required=False)
    timestamp = serializers.DateTimeField(default=datetime.now)


class TiposDocumentoResponseSerializer(serializers.Serializer):
    """
    Serializer para la respuesta de tipos de documento disponibles.
    Endpoint: GET /api/v1/tipos-documento/
    """
    
    tipos_documento = serializers.SerializerMethodField()
    total_tipos = serializers.SerializerMethodField()
    
    def get_tipos_documento(self, obj):
        """Lista los tipos de documento activos."""
        tipos = TipoDocumento.objects.filter(activo=True).order_by('codigo')
        return [
            {
                'codigo': tipo.codigo,
                'descripcion': tipo.descripcion,
                'activo': tipo.activo
            }
            for tipo in tipos
        ]
    
    def get_total_tipos(self, obj):
        """Cuenta total de tipos de documento activos."""
        return TipoDocumento.objects.filter(activo=True).count()


class ValidacionDocumentoSerializer(serializers.Serializer):
    """
    Serializer para validar documentos antes de búsquedas.
    Endpoint: POST /api/v1/validar-documento/
    """
    
    tipo_documento = serializers.ChoiceField(
        choices=[
            ('CC', 'Cédula de Ciudadanía'),
            ('NIT', 'NIT'),
            ('PA', 'Pasaporte'),
            ('CE', 'Cédula de Extranjería'),
            ('TI', 'Tarjeta de Identidad')
        ]
    )
    
    numero_documento = serializers.CharField(max_length=20, min_length=5)
    
    def validate(self, attrs):
        """Reutiliza validaciones del serializer de búsqueda."""
        # Crear instancia temporal para validar
        temp_serializer = BusquedaClienteRequestSerializer(data=attrs)
        if temp_serializer.is_valid():
            return attrs
        else:
            raise serializers.ValidationError(temp_serializer.errors)


# Exportar todos los serializers
__all__ = [
    'BusquedaClienteRequestSerializer',
    'BusquedaClienteResponseSerializer', 
    'ExportacionRequestSerializer',
    'ReporteFidelizacionRequestSerializer',
    'ReporteFidelizacionResponseSerializer',
    'ErrorResponseSerializer',
    'SuccessResponseSerializer',
    'TiposDocumentoResponseSerializer',
    'ValidacionDocumentoSerializer'
]