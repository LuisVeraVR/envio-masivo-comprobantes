"""
Manejador de archivos ZIP
Extrae PDFs y los asocia con clientes por NIT
"""

import os
import re
import zipfile
import shutil
import unicodedata
from typing import List, Dict, Tuple
from pathlib import Path
from app.utils.validator import Validator
from app.utils.logger import get_logger


class ZipHandler:
    """Maneja archivos ZIP con comprobantes PDF"""

    def __init__(self, logger=None):
        """
        Inicializa el manejador de ZIP

        Args:
            logger: Instancia del logger (opcional)
        """
        self.logger = logger or get_logger()
        self.archivos_extraidos: List[str] = []
        self.archivos_por_nit: Dict[str, List[str]] = {}  # {nit: [lista_rutas_pdf]}
        self.temp_dir: str | None = None

    # ========================= Helpers de normalización =========================

    def _only_digits(self, s: str) -> str:
        return ''.join(ch for ch in str(s or "") if ch.isdigit())

    def _strip_accents_lower_alnum_spaces(self, s: str) -> str:
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
        Extrae el NIT del nombre de un archivo PDF combinando dos estrategias:
        - V1 (estricta): Busca 'NIT._' al inicio (compatibilidad con tu patrón original).
        - V2 (flexible): Acepta NIT / N.I.T / NIT._ en cualquier parte, tolerando _.- y espacios.
        Reglas:
          * Captura 8-10 dígitos como NIT.
          * Solo descarta si F_/ORF_ están seguidos del MISMO número capturado.
          * Elige el candidato más “cercano” a la palabra NIT cuando hay múltiples.
        """
        base = os.path.splitext(os.path.basename(nombre_archivo))[0]
        candidatos = set()

        # --- V1: ESTRICTA (inicio con NIT._)
        m1 = re.search(r"^[_\s]*NIT\._?\s*(\d{8,10})(?!\d)", base, flags=re.IGNORECASE)
        if m1:
            candidatos.add(m1.group(1))
        m1b = re.search(r"^[_\s]*NIT\._?\s*(\d{8,10})-\d\b", base, flags=re.IGNORECASE)
        if m1b:
            candidatos.add(m1b.group(1))

        # --- V2: FLEXIBLE (NIT/N.I.T en cualquier parte)
        patron_flexible = re.compile(
            r"(?i)(?:^|[^A-Za-z0-9])N\.?\s*I\.?\s*T\.?\s*[_\.\s-]*\s*(\d{8,10})(?!\d)"
        )
        m2 = patron_flexible.search(base)
        if m2:
            candidatos.add(m2.group(1))

        # DV en cualquier parte: ".... 901234567-1 ..."
        m2b = re.search(r"\b(\d{8,10})-\d\b", base)
        if m2b:
            candidatos.add(m2b.group(1))

        if not candidatos:
            return None

        # Descarta candidato solo si F_/ORF_ llevan el MISMO número
        candidatos_filtrados = []
        for c in candidatos:
            mismo_num_despues_F = re.search(
                r"(?i)\b[FO]R?F[_\s]+0*" + re.escape(c) + r"\b", base
            ) is not None
            if not mismo_num_despues_F:
                candidatos_filtrados.append(c)

        if not candidatos_filtrados:
            candidatos_filtrados = list(candidatos)

        # Elegir el mejor candidato: el más cercano a la palabra "NIT"
        def _score(n):
            pos_nit = re.search(r"(?i)N\.?\s*I\.?\s*T", base)
            idx_nit = pos_nit.start() if pos_nit else -1
            idx_num = base.find(n)
            dist = abs(idx_num - idx_nit) if (idx_nit >= 0 and idx_num >= 0) else 999
            return (dist, idx_num)

        elegido = sorted(set(candidatos_filtrados), key=_score)[0]
        if len(elegido) <= 7:
            return None
        return elegido

    def procesar_zip(self, ruta_zip, temp_dir=None):
        """
        Procesa un archivo ZIP y extrae los PDFs

        Args:
            ruta_zip: Ruta al archivo ZIP
            temp_dir: Directorio temporal (opcional, se crea automáticamente)

        Returns:
            Tupla (exito, mensaje, archivos_por_nit)
        """
        self.archivos_extraidos = []
        self.archivos_por_nit = {}

        # Validar ZIP
        es_valido, mensaje = Validator.validar_archivo_zip(ruta_zip)
        if not es_valido:
            self.logger.error(f"Archivo ZIP inválido: {mensaje}", modulo="ZipHandler")
            return False, mensaje, {}

        # Directorio temporal
        self.temp_dir = temp_dir or self._crear_directorio_temporal()

        try:
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
                    self.logger.warning(mensaje, modulo="ZipHandler")
                    return False, mensaje, {}

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

                        # NIT desde nombre
                        nit = self._extraer_nit_de_nombre(archivo)
                        if nit:
                            nit_digits = self._only_digits(nit)

                            # llaves espejo: 10 → 9 también
                            keys = {nit_digits}
                            if len(nit_digits) == 10:
                                keys.add(nit_digits[:-1])

                            for k in keys:
                                self.archivos_por_nit.setdefault(k, []).append(ruta_extraida)

                            self.logger.debug(
                                f"PDF asociado: {os.path.basename(archivo)} -> NIT(s) {', '.join(keys)}",
                                modulo="ZipHandler",
                            )
                        else:
                            pdfs_sin_nit.append(archivo)
                            self.logger.warning(
                                f"No se pudo extraer NIT de: {archivo}",
                                modulo="ZipHandler",
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Error al extraer {archivo}: {e}",
                            modulo="ZipHandler",
                            exc_info=True,
                        )

            # Log del procesamiento
            self.logger.log_procesamiento_zip(
                os.path.basename(ruta_zip), len(self.archivos_extraidos)
            )

            # Resumen
            partes = [
                f"Extraídos {len(self.archivos_extraidos)} archivos PDF",
                f"Agrupados en {len(self.archivos_por_nit)} NITs diferentes",
            ]
            if pdfs_sin_nit:
                partes.append(f"⚠️ {len(pdfs_sin_nit)} archivos sin NIT identificable")
            mensaje = "\n".join(partes)

            if not self.archivos_por_nit:
                return False, "No se pudieron asociar archivos a ningún NIT", {}

            return True, mensaje, self.archivos_por_nit

        except Exception as e:
            mensaje = f"Error al procesar ZIP: {str(e)}"
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

        keys = {digits}
        if len(digits) == 10:
            keys.add(digits[:-1])

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
        """Lista de todos los NITs indexados"""
        return list(self.archivos_por_nit.keys())

    def validar_archivos_contra_clientes(self, lista_clientes):
        """
        Valida que los archivos del ZIP coincidan con los clientes del Excel
        Usa comparación flexible ignorando el dígito verificador
        """
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
                self.logger.debug(
                    f"Directorio temporal eliminado: {self.temp_dir}",
                    modulo="ZipHandler",
                )
                self.temp_dir = None
            except Exception as e:
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
