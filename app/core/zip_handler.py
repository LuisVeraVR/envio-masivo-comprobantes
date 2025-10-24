"""
Manejador de archivos ZIP
Extrae PDFs y los asocia con clientes por NIT/cédula
Versión mejorada: Soporta cédulas de 7-10 dígitos y NITs
"""

import os
import re
import zipfile
import shutil
import unicodedata
from typing import List, Dict, Tuple
from pathlib import Path


class ZipHandler:
    """Maneja archivos ZIP con comprobantes PDF"""

    def __init__(self, logger=None):
        """
        Inicializa el manejador de ZIP

        Args:
            logger: Instancia del logger (opcional)
        """
        self.logger = logger
        self.archivos_extraidos: List[str] = []
        self.archivos_por_nit: Dict[str, List[str]] = {}  # {nit: [lista_rutas_pdf]}
        self.temp_dir: str | None = None

    # ========================= Helpers de normalización =========================

    def _only_digits(self, s: str) -> str:
        """Extrae solo dígitos de un string"""
        return ''.join(ch for ch in str(s or "") if ch.isdigit())

    def _strip_accents_lower_alnum_spaces(self, s: str) -> str:
        """Normaliza texto removiendo acentos y caracteres especiales"""
        if not isinstance(s, str):
            s = str(s or "")
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        s = re.sub(r'[^a-z0-9]+', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _normalizar_texto(self, texto):
        """Normaliza texto para comparación (compat con lógica previa)"""
        if not texto:
            return ""
        texto = str(texto).lower()
        texto = unicodedata.normalize("NFKD", texto)
        texto = texto.encode("ASCII", "ignore").decode("ASCII")
        texto = re.sub(r"[^a-z0-9\s]", " ", texto)
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    # ========================= Flujo principal ZIP ==============================

    def _crear_directorio_temporal(self):
        """
        Crea un directorio temporal para extraer archivos

        Returns:
            Ruta al directorio temporal
        """
        import time
        timestamp = int(time.time())
        temp_dir = f"temp/zip_extract_{timestamp}"
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        return temp_dir

    def _extraer_nit_de_nombre(self, nombre_archivo):
        """
        Extrae el NIT/cédula del nombre de un archivo PDF.
        
        Estrategias combinadas:
        1. Busca patrones explícitos con "NIT" (al inicio o en cualquier parte)
        2. Busca números con dígito verificador (formato X-Y)
        3. Acepta identificaciones de 7-10 dígitos (cédulas y NITs)
        4. Filtra números de factura (F_, ORF_, RF-)
        5. Prioriza el número más cercano a la palabra "NIT"
        
        Ejemplos soportados:
        - NIT._ 31404561 → 31404561
        - NIT._ 800035120 → 800035120
        - RF-84838082-900219353-V-F-F → 900219353
        - 1085245654-5 → 1085245654
        """
        base = os.path.splitext(os.path.basename(nombre_archivo))[0]
        candidatos = set()

        # ==================== ESTRATEGIA 1: NIT explícito al inicio ====================
        # Patrón: ^[espacios/guiones]*NIT._[espacios]*DIGITOS
        m1 = re.search(r"^[_\s-]*NIT\._?\s*(\d{7,10})(?!\d)", base, flags=re.IGNORECASE)
        if m1:
            candidatos.add(m1.group(1))
        
        # Con dígito verificador: NIT._ 12345678-9
        m1b = re.search(r"^[_\s-]*NIT\._?\s*(\d{7,10})-\d\b", base, flags=re.IGNORECASE)
        if m1b:
            candidatos.add(m1b.group(1))

        # ==================== ESTRATEGIA 2: NIT en cualquier parte ====================
        # Patrón flexible: N.I.T / NIT / N I T seguido de número
        patron_flexible = re.compile(
            r"(?i)(?:^|[^A-Za-z0-9])N\.?\s*I\.?\s*T\.?\s*[_\.\s-]*\s*(\d{7,10})(?!\d)"
        )
        for match in patron_flexible.finditer(base):
            candidatos.add(match.group(1))

        # ==================== ESTRATEGIA 3: Números con dígito verificador ====================
        # Formato: 12345678-9 (sin importar posición)
        for match in re.finditer(r"\b(\d{7,10})-\d\b", base):
            candidatos.add(match.group(1))

        # ==================== ESTRATEGIA 4: Formato RF- con múltiples números ====================
        # Ejemplo: RF-84838082-900219353-V-F-F
        # Buscar el número más largo después de RF-
        if base.startswith("RF-"):
            numeros_rf = re.findall(r"\b(\d{7,10})\b", base)
            if numeros_rf:
                # Tomar el más largo (probablemente el NIT)
                mas_largo = max(numeros_rf, key=len)
                candidatos.add(mas_largo)

        if not candidatos:
            return None

        # ==================== FILTRADO DE FALSOS POSITIVOS ====================
        # Descartar números que son claramente facturas (F_, ORF_, RF_)
        candidatos_filtrados = []
        
        for c in candidatos:
            # Verificar si este número aparece después de F_, ORF_, o RF_ como factura
            # Ejemplo: "F_ ORF_ 84838066" → 84838066 es factura, NO NIT
            patron_factura = r"(?i)\b(?:F|ORF|RF)[_\s]+0*" + re.escape(c) + r"\b"
            
            # Si el número NO aparece como factura, es candidato válido
            if not re.search(patron_factura, base):
                candidatos_filtrados.append(c)
            else:
                # Verificar si también aparece en otro contexto (cerca de "NIT")
                patron_nit_cercano = r"(?i)NIT[._\s]+0*" + re.escape(c) + r"\b"
                if re.search(patron_nit_cercano, base):
                    # Está cerca de "NIT", probablemente es el NIT correcto
                    candidatos_filtrados.append(c)

        # Si todos fueron filtrados, usar los originales
        if not candidatos_filtrados:
            candidatos_filtrados = list(candidatos)

        # ==================== SELECCIÓN DEL MEJOR CANDIDATO ====================
        # Priorizar el número más cercano a la palabra "NIT"
        def _score(numero):
            # Buscar posición de "NIT" en el nombre
            match_nit = re.search(r"(?i)N\.?\s*I\.?\s*T", base)
            idx_nit = match_nit.start() if match_nit else -1
            
            # Buscar posición del número
            idx_num = base.find(numero)
            
            # Calcular distancia (menor es mejor)
            if idx_nit >= 0 and idx_num >= 0:
                distancia = abs(idx_num - idx_nit)
            else:
                distancia = 999  # Penalizar si no hay "NIT"
            
            # Preferir números más largos en caso de empate (NITs suelen ser más largos)
            longitud = -len(numero)  # Negativo para que más largo = mejor
            
            return (distancia, longitud, idx_num)

        # Ordenar candidatos por score y tomar el mejor
        mejor_candidato = sorted(set(candidatos_filtrados), key=_score)[0]
        
        # Validación final: aceptar 7-10 dígitos
        if len(mejor_candidato) < 7:
            return None
            
        return mejor_candidato

    def procesar_zip(self, ruta_zip, temp_dir=None):
        """
        Procesa un archivo ZIP y extrae los PDFs

        Args:
            ruta_zip: Ruta al archivo ZIP
            temp_dir: Directorio temporal (opcional, se crea automáticamente)

        Returns:
            Tupla (exito, mensaje, archivos_por_nit)
        """
        from app.utils.validator import Validator
        
        self.archivos_extraidos = []
        self.archivos_por_nit = {}

        # Validar ZIP
        es_valido, mensaje = Validator.validar_archivo_zip(ruta_zip)
        if not es_valido:
            if self.logger:
                self.logger.error(f"Archivo ZIP inválido: {mensaje}", modulo="ZipHandler")
            return False, mensaje, {}

        # Directorio temporal
        self.temp_dir = temp_dir or self._crear_directorio_temporal()

        try:
            if self.logger:
                self.logger.info(
                    f"Procesando archivo ZIP: {os.path.basename(ruta_zip)}",
                    modulo="ZipHandler",
                )

            with zipfile.ZipFile(ruta_zip, "r") as zip_ref:
                # Listado de PDFs
                archivos = [
                    f for f in zip_ref.namelist()
                    if f.lower().endswith(".pdf") and not f.startswith("__MACOSX")
                ]

                if not archivos:
                    mensaje = "No se encontraron archivos PDF en el ZIP"
                    if self.logger:
                        self.logger.warning(mensaje, modulo="ZipHandler")
                    return False, mensaje, {}

                if self.logger:
                    self.logger.info(
                        f"Encontrados {len(archivos)} archivos PDF", modulo="ZipHandler"
                    )

                pdfs_sin_nit = []

                for archivo in archivos:
                    try:
                        # Extraer
                        zip_ref.extract(archivo, self.temp_dir)
                        ruta_extraida = os.path.join(self.temp_dir, archivo)
                        self.archivos_extraidos.append(ruta_extraida)

                        # NIT/cédula desde nombre
                        nit = self._extraer_nit_de_nombre(archivo)
                        if nit:
                            # ✅ SOLUCIÓN: Solo normalizar, SIN crear llaves espejo
                            nit_normalizado = Validator.normalizar_nit(nit)

                            # Indexar con UNA SOLA llave (el NIT completo)
                            if nit_normalizado not in self.archivos_por_nit:
                                self.archivos_por_nit[nit_normalizado] = []
                            
                            self.archivos_por_nit[nit_normalizado].append(ruta_extraida)

                            if self.logger:
                                self.logger.debug(
                                    f"PDF asociado: {os.path.basename(archivo)} -> NIT {nit_normalizado}",
                                    modulo="ZipHandler",
                                )
                        else:
                            pdfs_sin_nit.append(archivo)
                            if self.logger:
                                self.logger.warning(
                                    f"No se pudo extraer NIT/cédula de: {archivo}",
                                    modulo="ZipHandler",
                                )

                    except Exception as e:
                        if self.logger:
                            self.logger.error(
                                f"Error al extraer {archivo}: {str(e)}",
                                modulo="ZipHandler",
                                exc_info=True,
                            )

                # Resumen final
                if self.logger:
                    self.logger.info(
                        f"Procesamiento ZIP completado: {os.path.basename(ruta_zip)} | "
                        f"PDFs extraídos: {len(self.archivos_extraidos)} | "
                        f"NITs únicos: {len(self.archivos_por_nit)} | "
                        f"PDFs sin NIT: {len(pdfs_sin_nit)}",
                        modulo="ZipHandler"
                    )

                    if pdfs_sin_nit:
                        self.logger.warning(
                            f"=== {len(pdfs_sin_nit)} PDFs SIN NIT/CÉDULA DETECTADO ===",
                            modulo="ZipHandler",
                        )
                        for i, pdf in enumerate(pdfs_sin_nit[:10], 1):
                            self.logger.warning(f"  {i}. {pdf}", modulo="ZipHandler")
                        if len(pdfs_sin_nit) > 10:
                            self.logger.warning(
                                f"  ... y {len(pdfs_sin_nit) - 10} más", modulo="ZipHandler"
                            )

                mensaje = f"Procesados {len(self.archivos_extraidos)} PDFs, {len(self.archivos_por_nit)} NITs únicos"
                return True, mensaje, self.archivos_por_nit

        except Exception as e:
            mensaje = f"Error al procesar ZIP: {str(e)}"
            if self.logger:
                self.logger.error(mensaje, modulo="ZipHandler", exc_info=True)
            return False, mensaje, {}

    # ========================= Búsquedas por NIT / Nombre =======================

    def obtener_archivos_por_nit(self, nit):
        """
        Devuelve los PDFs asociados al NIT. Usa llaves espejo para mayor tolerancia.
        """
        n = str(nit or "").strip()
        if not n:
            return []
        digits = self._only_digits(n)
        if not digits:
            return []

        # Llaves espejo para búsqueda flexible
        keys = {digits}
        if len(digits) == 10:
            keys.add(digits[:-1])  # 10 → 9
        elif len(digits) == 9:
            keys.add(digits[:-1])  # 9 → 8
        elif len(digits) == 8:
            keys.add(digits[:-1])  # 8 → 7

        resultados: List[str] = []
        for k in keys:
            resultados.extend(self.archivos_por_nit.get(k, []))
        return list(dict.fromkeys(resultados))  # sin duplicados

    def buscar_archivos_por_nit_flexible(self, nit_buscado, nombre_cliente=None):
        """
        Busca archivos por NIT de forma flexible y, si falla, por nombre de empresa.
        """
        digits = self._only_digits(nit_buscado)
        if digits:
            # 1) Por llaves espejo
            archivos = self.obtener_archivos_por_nit(digits)
            if archivos:
                return archivos

            # 2) Por aparición del número en el nombre del archivo
            candidatos = []
            for ruta in self.archivos_extraidos:
                nombre = os.path.basename(ruta)
                if digits in nombre:
                    candidatos.append(ruta)
            if candidatos:
                return candidatos

        # 3) Por similitud del nombre de empresa
        if nombre_cliente:
            por_nombre = self._buscar_por_nombre_empresa(nombre_cliente)
            if por_nombre:
                return por_nombre

        return []

    def _buscar_por_nombre_empresa(self, nombre_cliente):
        """
        Busca archivos por similitud en el nombre de la empresa
        """
        if not nombre_cliente:
            return []

        nombre_norm = self._normalizar_texto(nombre_cliente)

        palabras_ignorar = {
            "sas", "s.a.s", "sa", "s.a", "ltda", "limitada",
            "sociedad", "por", "acciones", "simplificada",
            "comercializadora", "distribuidora", "inversiones",
            "productos", "servicios", "empresa", "compania", "compañia",
            "cia", "de", "del", "la", "el", "y", "e", "los", "las",
            "quesos", "florida"
        }

        palabras = [p for p in nombre_norm.split() if len(p) >= 4 and p not in palabras_ignorar]
        if not palabras:
            palabras = nombre_norm.split()[:3]

        candidatos = []
        for ruta in self.archivos_extraidos:
            nombre_archivo = self._normalizar_texto(os.path.basename(ruta))
            score = sum(1 for p in palabras if p in nombre_archivo)
            if score >= max(1, int(len(palabras) * 0.5)):
                candidatos.append((ruta, score))

        candidatos.sort(key=lambda x: (-x[1], x[0]))
        return [archivo for archivo, _ in candidatos]

    # ========================= Reportes / Limpieza ==============================

    def obtener_todos_los_nits(self):
        """Lista de todos los NITs/cédulas indexados"""
        return list(self.archivos_por_nit.keys())

    def validar_archivos_contra_clientes(self, lista_clientes):
        """
        Valida que los archivos del ZIP coincidan con los clientes del Excel
        Usa comparación flexible ignorando el dígito verificador
        """
        from app.utils.validator import Validator
        
        nits_excel = [Validator.normalizar_nit(cliente["nit"]) for cliente in lista_clientes]
        nits_zip = list(self.obtener_todos_los_nits())

        nits_coincidentes = []
        clientes_sin_archivos = []

        for cliente in lista_clientes:
            nit_excel = Validator.normalizar_nit(cliente["nit"])
            encontrado = False
            for nit_zip in nits_zip:
                if Validator.nits_coinciden(nit_excel, nit_zip):
                    encontrado = True
                    if nit_excel not in nits_coincidentes:
                        nits_coincidentes.append(nit_excel)
                    break
            if not encontrado:
                clientes_sin_archivos.append({
                    "nit": cliente["nit"],
                    "nombre": cliente["nombre"],
                    "email": cliente["email"],
                })

        archivos_sin_cliente = []
        for nit_zip in nits_zip:
            encontrado = any(Validator.nits_coinciden(nit_excel, nit_zip) for nit_excel in nits_excel)
            if not encontrado:
                archivos_nit = self.archivos_por_nit.get(nit_zip, [])
                for archivo in archivos_nit:
                    archivos_sin_cliente.append({"nit": nit_zip, "archivo": os.path.basename(archivo)})

        resultado = {
            "total_excel": len(nits_excel),
            "total_zip": len(nits_zip),
            "coincidentes": len(nits_coincidentes),
            "sin_archivos": clientes_sin_archivos,
            "sin_cliente": archivos_sin_cliente,
        }

        # Logs
        if self.logger:
            if clientes_sin_archivos:
                self.logger.warning(
                    f"=== {len(clientes_sin_archivos)} CLIENTES SIN ARCHIVOS ===",
                    modulo="ZipHandler",
                )
                for i, cliente in enumerate(clientes_sin_archivos[:20], 1):
                    self.logger.warning(
                        f"  {i}. NIT: {cliente['nit']} | Nombre: {cliente['nombre'][:50]} | Email: {cliente['email']}",
                        modulo="ZipHandler",
                    )
                if len(clientes_sin_archivos) > 20:
                    self.logger.warning(
                        f"  ... y {len(clientes_sin_archivos) - 20} más",
                        modulo="ZipHandler",
                    )

            if archivos_sin_cliente:
                agrupados = {}
                for info in archivos_sin_cliente:
                    agrupados.setdefault(info["nit"], []).append(info["archivo"])

                total_nits_sin_cliente = len(agrupados)
                total_archivos_sin_cliente = len(archivos_sin_cliente)

                self.logger.warning(
                    f"=== {total_nits_sin_cliente} NITs SIN CLIENTE ({total_archivos_sin_cliente} archivos) ===",
                    modulo="ZipHandler",
                )

                for i, (nit, archivos) in enumerate(list(agrupados.items())[:20], 1):
                    if len(archivos) == 1:
                        self.logger.warning(f"  {i}. NIT: {nit} | {archivos[0]}", modulo="ZipHandler")
                    else:
                        self.logger.warning(f"  {i}. NIT: {nit} | {len(archivos)} archivos", modulo="ZipHandler")
                        for j, archivo in enumerate(archivos[:3], 1):
                            self.logger.warning(f"      {j}. {archivo}", modulo="ZipHandler")
                        if len(archivos) > 3:
                            self.logger.warning(f"      ... y {len(archivos) - 3} archivos más", modulo="ZipHandler")

                if total_nits_sin_cliente > 20:
                    self.logger.warning(f"  ... y {total_nits_sin_cliente - 20} NITs más", modulo="ZipHandler")

        return resultado

    def limpiar_temporales(self):
        """Elimina los archivos temporales extraídos"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                if self.logger:
                    self.logger.debug(
                        f"Directorio temporal eliminado: {self.temp_dir}",
                        modulo="ZipHandler",
                    )
                self.temp_dir = None
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error al eliminar temporales: {e}", modulo="ZipHandler"
                    )

    def obtener_resumen(self):
        """
        Genera un resumen del procesamiento

        Returns:
            Diccionario con estadísticas
        """
        total_archivos = sum(len(archivos) for archivos in self.archivos_por_nit.values())

        nit_con_mas_archivos = None
        max_archivos = 0
        for nit, archivos in self.archivos_por_nit.items():
            if len(archivos) > max_archivos:
                max_archivos = len(archivos)
                nit_con_mas_archivos = nit

        return {
            "total_archivos": total_archivos,
            "total_nits": len(self.archivos_por_nit),
            "promedio_archivos_por_nit": (total_archivos / len(self.archivos_por_nit)) if self.archivos_por_nit else 0,
            "nit_con_mas_archivos": nit_con_mas_archivos,
            "max_archivos_por_nit": max_archivos,
        }

    def __del__(self):
        """Destructor: limpia archivos temporales al eliminar el objeto"""
        try:
            self.limpiar_temporales()
        except Exception:
            pass