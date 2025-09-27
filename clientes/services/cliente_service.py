"""
Cliente Service - Lógica de negocio para operaciones con clientes.
Incluye búsqueda por documento e información completa del cliente.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from .base_service import (
    BaseService, 
    ServiceException, 
    ClienteNoEncontradoException,
    DocumentoInvalidoException,
    require_params
)
from ..repositories.cliente_repository import ClienteRepository
from ..repositories.compra_repository import CompraRepository
from ..models import Cliente, Compra


class ClienteService(BaseService):
    """
    Service para manejo de lógica de negocio relacionada con clientes.
    """
    
    def __init__(self):
        super().__init__()
        self.cliente_repo = ClienteRepository()
        self.compra_repo = CompraRepository()
    
    def buscar_cliente_por_documento(self, tipo_documento: str, numero_documento: str) -> Dict[str, Any]:
        """
        Busca un cliente por tipo y número de documento.
        
        Args:
            tipo_documento: Tipo de documento (CC, NIT, PA, etc.)
            numero_documento: Número del documento
            
        Returns:
            Dict con información del cliente encontrado
            
        Raises:
            DocumentoInvalidoException: Si el documento es inválido
            ClienteNoEncontradoException: Si no se encuentra el cliente
        """
        def _buscar_operacion():
            # Validar parámetros requeridos
            require_params({
                'tipo_documento': tipo_documento,
                'numero_documento': numero_documento
            }, 'tipo_documento', 'numero_documento')
            
            # Validar formato del documento
            self._validar_formato_documento(tipo_documento, numero_documento)
            
            # Buscar cliente en la base de datos
            cliente = self.cliente_repo.get_by_documento(tipo_documento, numero_documento)
            
            if not cliente:
                raise ClienteNoEncontradoException(
                    f"No se encontró cliente con documento {tipo_documento} {numero_documento}"
                )
            
            # Verificar que esté activo
            if not cliente.activo:
                raise ClienteNoEncontradoException(
                    "El cliente existe pero está inactivo"
                )
            
            self.log_info(f"Cliente encontrado: {cliente.get_nombre_completo()}")
            
            return {
                'cliente': cliente,
                'documento_completo': f"{cliente.tipo_documento.codigo} {cliente.numero_documento}",
                'fecha_consulta': datetime.now()
            }
        
        return self.execute_with_transaction(
            "buscar_cliente_por_documento",
            _buscar_operacion
        )
    
    def obtener_informacion_completa(self, cliente_id: int, incluir_compras: bool = True, 
                                   limite_compras: int = 10) -> Dict[str, Any]:
        """
        Obtiene información completa de un cliente incluyendo estadísticas de compras.
        
        Args:
            cliente_id: ID del cliente
            incluir_compras: Si incluir historial de compras
            limite_compras: Límite de compras a incluir
            
        Returns:
            Dict con información completa del cliente
        """
        def _obtener_info_operacion():
            # Obtener cliente
            cliente = self.cliente_repo.get_by_id(cliente_id)
            
            if not cliente or not cliente.activo:
                raise ClienteNoEncontradoException(
                    f"Cliente con ID {cliente_id} no encontrado o inactivo"
                )
            
            # Información básica
            resultado = {
                'cliente': cliente,
                'documento_completo': f"{cliente.tipo_documento.codigo} {cliente.numero_documento}",
                'fecha_consulta': datetime.now()
            }
            
            # Estadísticas de compras
            estadisticas = self._calcular_estadisticas_compras(cliente_id)
            resultado['estadisticas_compras'] = estadisticas
            
            # Historial de compras (opcional)
            if incluir_compras:
                # ✅ CORRECCIÓN: Sin parámetro 'limite'
                compras = self.compra_repo.get_compras_by_cliente(cliente_id)
                
                # Aplicar límite manualmente si es necesario
                if compras and limite_compras > 0:
                    compras = compras[:limite_compras]
                
                resultado['compras_recientes'] = compras
            
            self.log_info(f"Información completa obtenida para cliente: {cliente.get_nombre_completo()}")
            
            return resultado
        
        return self.execute_with_transaction(
            "obtener_informacion_completa",
            _obtener_info_operacion
        )
    
    def validar_datos_cliente(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos de un cliente antes de operaciones.
        
        Args:
            data: Diccionario con datos del cliente
            
        Returns:
            Dict con resultado de validación
        """
        def _validar_operacion():
            errores = []
            
            # Validar campos requeridos
            campos_requeridos = ['tipo_documento', 'numero_documento', 'nombre', 'apellido']
            
            for campo in campos_requeridos:
                if not data.get(campo):
                    errores.append(f"Campo requerido: {campo}")
            
            # Validar formato de documento
            if data.get('tipo_documento') and data.get('numero_documento'):
                try:
                    self._validar_formato_documento(
                        data['tipo_documento'], 
                        data['numero_documento']
                    )
                except DocumentoInvalidoException as e:
                    errores.append(str(e))
            
            # Validar email si está presente
            if data.get('correo'):
                if not self._validar_email(data['correo']):
                    errores.append("Formato de correo inválido")
            
            # Validar teléfono si está presente
            if data.get('telefono'):
                if not self._validar_telefono(data['telefono']):
                    errores.append("Formato de teléfono inválido")
            
            # Verificar unicidad del documento (si es creación)
            if not data.get('cliente_id'):  # Es creación, no actualización
                cliente_existente = self.cliente_repo.get_by_documento(
                    data.get('tipo_documento'), 
                    data.get('numero_documento')
                )
                if cliente_existente:
                    errores.append("Ya existe un cliente con este documento")
            
            resultado = {
                'valido': len(errores) == 0,
                'errores': errores,
                'fecha_validacion': datetime.now()
            }
            
            if errores:
                self.log_warning("Datos de cliente inválidos", {'errores': errores})
            else:
                self.log_info("Datos de cliente válidos")
            
            return resultado
        
        return self.execute_with_transaction(
            "validar_datos_cliente",
            _validar_operacion
        )
    
    def obtener_clientes_vip(self, monto_minimo: Decimal = Decimal('5000000.00'), 
                           fecha_inicio: datetime = None) -> Dict[str, Any]:
        """
        Obtiene lista de clientes VIP basado en monto de compras.
        
        Args:
            monto_minimo: Monto mínimo para ser considerado VIP
            fecha_inicio: Fecha de inicio para el cálculo (por defecto último mes)
            
        Returns:
            Dict con lista de clientes VIP y estadísticas
        """
        def _obtener_vip_operacion():
            # Fecha por defecto: último mes
            if not fecha_inicio:
                fecha_inicio_calc = datetime.now() - timedelta(days=30)
            else:
                fecha_inicio_calc = fecha_inicio
            
            # Obtener clientes VIP usando el repository
            clientes_vip = self.compra_repo.get_clientes_vip(
                monto_minimo=monto_minimo,
                fecha_inicio=fecha_inicio_calc
            )
            
            # Calcular estadísticas
            total_clientes = len(clientes_vip)
            monto_total = sum(cliente.get('monto_total', 0) for cliente in clientes_vip)
            monto_promedio = monto_total / total_clientes if total_clientes > 0 else Decimal('0.00')
            
            resultado = {
                'clientes_vip': clientes_vip,
                'estadisticas': {
                    'total_clientes_vip': total_clientes,
                    'monto_total_periodo': monto_total,
                    'monto_promedio': monto_promedio,
                    'fecha_inicio': fecha_inicio_calc,
                    'fecha_fin': datetime.now(),
                    'monto_minimo_vip': monto_minimo
                },
                'parametros_consulta': {
                    'monto_minimo': monto_minimo,
                    'fecha_inicio': fecha_inicio_calc
                },
                'fecha_consulta': datetime.now()
            }
            
            self.log_info(f"Clientes VIP obtenidos: {total_clientes} clientes")
            
            return resultado
        
        return self.execute_with_transaction(
            "obtener_clientes_vip",
            _obtener_vip_operacion
        )
    
    # Métodos privados de validación
    
    def _validar_formato_documento(self, tipo_documento: str, numero_documento: str):
        """Valida el formato del documento según su tipo."""
        import re
        
        if not tipo_documento or not numero_documento:
            raise DocumentoInvalidoException("Tipo y número de documento son requeridos")
        
        numero_documento = numero_documento.strip()
        
        if tipo_documento == 'CC':
            # Cédula: solo números, 6-12 dígitos
            if not re.match(r'^\d{6,12}$', numero_documento):
                raise DocumentoInvalidoException(
                    "La cédula debe contener solo números entre 6 y 12 dígitos"
                )
        
        elif tipo_documento == 'NIT':
            # NIT: números con posible guión y dígito verificador
            if not re.match(r'^\d{9,12}-?\d?$', numero_documento):
                raise DocumentoInvalidoException(
                    "Formato de NIT inválido"
                )
        
        elif tipo_documento == 'PA':
            # Pasaporte: alfanumérico, 6-10 caracteres
            if not re.match(r'^[A-Za-z0-9]{6,10}$', numero_documento):
                raise DocumentoInvalidoException(
                    "El pasaporte debe tener entre 6 y 10 caracteres alfanuméricos"
                )
        
        else:
            # Validación genérica para otros tipos
            if len(numero_documento) < 5 or len(numero_documento) > 20:
                raise DocumentoInvalidoException(
                    "El número de documento debe tener entre 5 y 20 caracteres"
                )
    
    def _validar_email(self, email: str) -> bool:
        """Valida formato de email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validar_telefono(self, telefono: str) -> bool:
        """Valida formato de teléfono."""
        import re
        # Permite números, espacios, guiones y paréntesis
        pattern = r'^[\d\s\-\(\)]{7,15}$'
        return bool(re.match(pattern, telefono))
    
    def _calcular_estadisticas_compras(self, cliente_id: int) -> Dict[str, Any]:
        """Calcula estadísticas de compras para un cliente."""
        try:
            # Obtener todas las compras del cliente
            compras = Compra.objects.filter(
                cliente_id=cliente_id,
                estado__codigo='COMPLETADA'
            ).order_by('-fecha_compra')
            
            if not compras.exists():
                return {
                    'total_compras': 0,
                    'monto_total_historico': Decimal('0.00'),
                    'monto_promedio': Decimal('0.00'),
                    'ultima_compra': None,
                    'compras_ultimo_mes': 0,
                    'monto_ultimo_mes': Decimal('0.00')
                }
            
            # Estadísticas generales
            total_compras = compras.count()
            monto_total = sum(compra.monto_total for compra in compras)
            monto_promedio = monto_total / total_compras if total_compras > 0 else Decimal('0.00')
            ultima_compra = compras.first()
            
            # Compras del último mes
            fecha_limite = datetime.now() - timedelta(days=30)
            compras_ultimo_mes = compras.filter(fecha_compra__gte=fecha_limite)
            monto_ultimo_mes = sum(compra.monto_total for compra in compras_ultimo_mes)
            
            return {
                'total_compras': total_compras,
                'monto_total_historico': monto_total,
                'monto_promedio': monto_promedio,
                'ultima_compra': ultima_compra.fecha_compra if ultima_compra else None,
                'numero_factura_ultima': ultima_compra.numero_factura if ultima_compra else None,
                'compras_ultimo_mes': compras_ultimo_mes.count(),
                'monto_ultimo_mes': monto_ultimo_mes,
                'cliente_vip': monto_ultimo_mes >= Decimal('5000000.00')
            }
            
        except Exception as e:
            self.log_error("Error calculando estadísticas de compras", e)
            return {
                'error': 'Error calculando estadísticas',
                'total_compras': 0,
                'monto_total_historico': Decimal('0.00')
            }