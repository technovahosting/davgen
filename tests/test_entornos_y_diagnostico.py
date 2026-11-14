"""Accesos por entorno (desarrollo / producción), requisitos, diagnóstico de
conexiones y comparación con el backend publicado — sin BD ni FTP reales."""
import ftplib
import os
import socket

from conftest import CLAVE_PRUEBA, leer

from davgen.nucleo import bd, configuracion, diagnostico, remoto

DEV, PROD = '_acceso.desarrollo.ini', '_acceso.produccion.ini'


def _accesos(proyecto):
    for clave, valor in (('host', '127.0.0.1'), ('usuario', 'root'), ('database', 'dev_db')):
        configuracion.fijar_valor(proyecto, 'bd', clave, valor, archivo=DEV)
    for clave, valor in (('host', 'bd.hosting.test'), ('usuario', 'u_prod'),
                         ('password', 'Pr0d;#Clave'), ('database', 'prod_db')):
        configuracion.fijar_valor(proyecto, 'bd', clave, valor, archivo=PROD)
    for clave, valor in (('host', 'ftp.hosting.test'), ('usuario', 'ftpu'),
                         ('password', 'FtpClave9'), ('url', 'https://sitio.test')):
        configuracion.fijar_valor(proyecto, 'ftp', clave, valor, archivo=PROD)


# ── dos archivos de acceso ──────────────────────────────────────────────────
def test_cada_entorno_lee_sus_propios_accesos(proyecto_nuevo):
    _accesos(proyecto_nuevo)
    dev, e1 = configuracion.cargar(proyecto_nuevo)                        # por defecto
    prod, e2 = configuracion.cargar(proyecto_nuevo, entorno='produccion')
    assert e1 == [] and e2 == []
    assert dev['entorno'] == 'desarrollo' and dev['archivo_acceso'] == DEV
    assert dev['bd']['database'] == 'dev_db' and dev['bd']['password'] == ''
    assert dev['ftp_listo'] is False                 # en desarrollo no hay FTP
    assert prod['bd']['database'] == 'prod_db' and prod['bd']['password'] == 'Pr0d;#Clave'
    assert prod['ftp_listo'] is True and prod['ftp']['url'] == 'https://sitio.test'
    assert dev['admin_password'] == CLAVE_PRUEBA != prod['admin_password']
    assert dev['nombre'] == prod['nombre'] == 'Biblioteca'   # lo común, de _configtotal.ini


def test_la_variable_de_entorno_elige_el_archivo(proyecto_nuevo, monkeypatch):
    _accesos(proyecto_nuevo)
    monkeypatch.setenv('DAVGEN_ENTORNO', 'produccion')
    assert configuracion.cargar(proyecto_nuevo)[0]['bd']['database'] == 'prod_db'
    monkeypatch.setenv('DAVGEN_ENTORNO', 'cualquiera')            # inválido → desarrollo
    assert configuracion.cargar(proyecto_nuevo)[0]['bd']['database'] == 'dev_db'


def test_proyecto_sin_archivos_de_acceso_sigue_funcionando(tmp_path):
    (tmp_path / 'm.html').write_text('<html></html>', encoding='utf-8')
    (tmp_path / '_configtotal.ini').write_text(
        '[proyecto]\nnombre = Viejo\nmodulo = vie\n[entrada]\ntipo = mockup\nmockup = m.html\n'
        '[bd]\nhost = h\nusuario = u\ndatabase = d\npassword = p\n'
        '[ftp]\nhost = f\nusuario = fu\npassword = fp\nurl = https://v.test\n', encoding='utf-8')
    for entorno in ('desarrollo', 'produccion'):
        cfg, errores = configuracion.cargar(str(tmp_path), entorno=entorno)
        assert errores == [] and cfg['con_entornos'] is False
        assert cfg['bd']['database'] == 'd' and cfg['ftp_listo'] is True


def test_en_desarrollo_nunca_se_publica(proyecto_nuevo, davgen):
    _accesos(proyecto_nuevo)
    configuracion.fijar_valor(proyecto_nuevo, 'generar', 'produccion', 'si')
    configuracion.fijar_valor(proyecto_nuevo, 'generar', 'front', 'si')
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local', '--produccion', 'si'])
    assert codigo == 0, salida
    assert 'entorno DESARROLLO' in salida
    assert 'El backend NO se sube a producción' in salida
    assert 'El frontend NO se despliega' in salida
    # ni el host ni el sitio de producción aparecen en una corrida de desarrollo
    assert 'ftp.hosting.test' not in salida and 'sitio.test' not in salida


def test_generar_muestra_los_requisitos_y_la_interfaz(proyecto_nuevo, davgen):
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0, salida
    bloque = salida.split('REQUISITOS')[1]
    assert 'Mockup' in bloque and 'Base de datos' in bloque and 'FTP' in bloque
    assert '_acceso.desarrollo.ini' in bloque
    assert 'adaptable' in bloque and 'claro y oscuro' in bloque


def test_entornos_mueve_los_accesos_de_un_proyecto_anterior(tmp_path, davgen):
    raiz = tmp_path / 'viejo'
    (raiz / '03-Backend').mkdir(parents=True)
    (raiz / 'm.html').write_text('<html></html>', encoding='utf-8')
    (raiz / '.gitignore').write_text('*.zip\n', encoding='utf-8')
    (raiz / '_configtotal.ini').write_text(
        '[proyecto]\nnombre = Viejo\nmodulo = vie\n[entrada]\ntipo = mockup\nmockup = m.html\n'
        '[bd]\nhost = bd.h.test\npuerto = 3306\nusuario = u\npassword = Clav3;Bd\ndatabase = d\n'
        '[seguridad]\nadmin_email = jefe@v.test\nadmin_password = AdminProd99\n'
        '[ftp]\nhost = ftp.h.test\nusuario = fu\npassword = Clav3Ftp\nruta_remota = /api2\n'
        'url = https://v.test\n', encoding='utf-8')
    antes, _ = configuracion.cargar(str(raiz))

    # sin decir de qué entorno son, no adivina
    codigo, salida = davgen(raiz, ['entornos', '--si'])
    assert codigo == 1 and '--actual' in salida
    assert not (raiz / PROD).exists()

    codigo, salida = davgen(raiz, ['entornos', '--actual', 'produccion', '--si'])
    assert codigo == 0, salida
    principal = leer(str(raiz), '_configtotal.ini')
    for secreto in ('Clav3;Bd', 'Clav3Ftp', 'AdminProd99', 'bd.h.test'):
        assert secreto not in principal
    assert 'admin_email = jefe@v.test' in principal            # lo no secreto se queda
    prod, errores = configuracion.cargar(str(raiz), entorno='produccion')
    assert errores == []
    for clave in ('bd', 'ftp', 'admin_password', 'admin_email'):
        assert prod[clave] == antes[clave], clave
    dev, _ = configuracion.cargar(str(raiz), entorno='desarrollo')
    assert dev['bd']['password'] == '' and dev['ftp_listo'] is False
    ignorados = leer(str(raiz), '.gitignore').splitlines()
    assert '_acceso.*.ini' in ignorados and '!_acceso.*.ejemplo.ini' in ignorados
    assert 'Clav3;Bd' not in leer(str(raiz), '_acceso.produccion.ejemplo.ini')
    # repetirlo no cambia nada
    codigo, _ = davgen(raiz, ['entornos', '--si'])
    assert codigo == 0
    assert configuracion.cargar(str(raiz), entorno='produccion')[0]['bd'] == antes['bd']


# ── por qué no conecta ──────────────────────────────────────────────────────
class _ErrorMysql(Exception):
    pass


def test_explica_los_errores_tipicos_de_mysql():
    local = {'host': '127.0.0.1', 'puerto': '3306', 'database': 'd'}
    remoto_ = {'host': 'bd.hosting.test', 'puerto': '3306', 'database': 'd'}
    causa, hacer = diagnostico.explicar_error_bd(_ErrorMysql(2003, "Can't connect"), local)
    assert 'no está iniciado' in causa and 'iniciar MySQL' in hacer
    causa, hacer = diagnostico.explicar_error_bd(_ErrorMysql(2003, "Can't connect"), remoto_)
    assert 'REMOTA' in hacer
    causa, hacer = diagnostico.explicar_error_bd(_ErrorMysql(1045, 'Access denied'), remoto_)
    assert 'contraseña' in causa and 'IP' in hacer
    assert 'no existe' in diagnostico.explicar_error_bd(_ErrorMysql(1049, 'Unknown'), local)[0]
    assert 'DNS' in diagnostico.explicar_error_bd(socket.gaierror(11001, 'getaddrinfo failed'), remoto_)[0]
    assert 'límite' in diagnostico.explicar_error_bd(_ErrorMysql(1226, 'max_connections'), remoto_)[0]


def test_explica_los_errores_tipicos_del_ftp():
    datos = {'host': 'ftp://ftp.hosting.test'}
    assert 'DNS' in diagnostico.explicar_error_ftp(socket.gaierror(11001, 'getaddrinfo failed'), datos)[0]
    causa, hacer = diagnostico.explicar_error_ftp(ftplib.error_perm('530 Login incorrect'), datos)
    assert 'rechazados' in causa and 'CUENTA FTP' in hacer
    assert 'firewall' in diagnostico.explicar_error_ftp(TimeoutError('timed out'), datos)[1]


def test_probar_bd_distingue_caida_sin_sembrar_y_lista():
    datos = {'host': '127.0.0.1', 'puerto': '3306', 'usuario': 'u', 'password': '', 'database': 'd'}
    assert diagnostico.probar_bd({})[0] == 'aviso'

    def caida(_d, _t):
        raise _ErrorMysql(2003, "Can't connect")
    bd.usar_fabrica(caida)
    estado, _n, detalle, hacer = diagnostico.probar_bd(datos)
    assert estado == 'falta' and 'no conecta' in detalle and hacer

    class _Cur:
        def __init__(self, seg):
            self.seg, self.filas = seg, []

        def execute(self, sql, params=None):
            self.filas = [('11.8-MariaDB',)] if 'VERSION' in sql else [(self.seg,)]

        def fetchall(self):
            return self.filas

    class _Con:
        def __init__(self, seg):
            self.seg = seg

        def cursor(self):
            return _Cur(self.seg)

        def close(self):
            pass

    bd.usar_fabrica(lambda _d, _t: _Con(0))
    estado, _n, detalle, hacer = diagnostico.probar_bd(datos)
    assert estado == 'aviso' and 'davgen seguridad' in hacer
    bd.usar_fabrica(lambda _d, _t: _Con(10))
    assert diagnostico.probar_bd(datos)[0] == 'ok'


def test_requisitos_avisa_de_google_sin_client_id(proyecto_nuevo):
    configuracion.fijar_valor(proyecto_nuevo, 'seguridad', 'google_auth_activo', 'si')
    cfg, _ = configuracion.cargar(proyecto_nuevo)
    google = [p for p in diagnostico.requisitos(cfg) if p[1] == 'Google'][0]
    assert google[0] == 'falta' and 'no aparecerá' in google[2]


# ── comparar con lo publicado ───────────────────────────────────────────────
class _FtpFalso:
    """Servidor FTP en memoria: {ruta remota: contenido}. Solo lectura."""
    def __init__(self, archivos):
        self.archivos = archivos
        self.ordenes = []

    def mlsd(self, ruta):
        ruta = ruta.rstrip('/')
        hijos = {}
        for r in self.archivos:
            if r.startswith(ruta + '/'):
                resto = r[len(ruta) + 1:]
                nombre = resto.split('/')[0]
                hijos[nombre] = 'dir' if '/' in resto else 'file'
        if not hijos:
            raise ftplib.error_perm('550 No such directory')
        return [(n, {'type': t}) for n, t in sorted(hijos.items())]

    def retrbinary(self, orden, escribir):
        self.ordenes.append(orden)
        ruta = orden.split(' ', 1)[1]
        if ruta not in self.archivos:
            raise ftplib.error_perm('550 No such file')
        escribir(self.archivos[ruta].encode('utf-8'))

    def quit(self):
        pass

    def __getattr__(self, nombre):            # cualquier orden de escritura rompe la prueba
        raise AssertionError(f'el comparador no debe usar ftp.{nombre}')


GEN = "<?php\n/**\n * @generated davgen v5.0.0 | {fecha}\n */\n{cuerpo}\n"


def _escribir(base, rel, texto):
    ruta = os.path.join(str(base), *rel.split('/'))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto)


def test_baja_el_backend_publicado_y_lo_compara_en_local(tmp_path):
    espejo, laravel, bajado = tmp_path / 'espejo', tmp_path / 'laravel', tmp_path / '_remoto'
    igual = GEN.format(fecha='2026-01-01 00:00', cuerpo='class Igual {}')
    for base in (espejo, laravel):
        _escribir(base, 'app/Services/Igual.php', igual)
        _escribir(base, 'app/Services/Cambiado.php', GEN.format(fecha='x', cuerpo='class Nuevo {}'))
        _escribir(base, 'routes/api.php', GEN.format(fecha='x', cuerpo='// rutas'))
    _escribir(laravel, 'routes/Custom/propio.php', "<?php\n// mío\n")
    servidor = _FtpFalso({
        # misma clase, otra fecha de generación: debe contar como IGUAL
        '/servicio/app/Services/Igual.php': GEN.format(fecha='2025-05-05 10:10', cuerpo='class Igual {}'),
        '/servicio/app/Services/Cambiado.php': GEN.format(fecha='x', cuerpo='class Viejo {}'),
        '/servicio/app/Http/Controllers/SubidoAMano.php': "<?php\n// alguien lo subió\n",
        '/servicio/routes/api.php': GEN.format(fecha='x', cuerpo='// rutas'),
        '/servicio/bootstrap/app.php': "<?php\n// arranque\n",
        '/servicio/app/notas.txt': 'no es php',
        '/servicio/.env': 'DB_PASSWORD=secreto',
    })
    remoto.usar_fabrica_ftp(lambda _cfg: servidor)
    try:
        rep = remoto.descargar_backend({'ruta_remota': '/servicio'}, str(bajado))
    finally:
        remoto.usar_fabrica_ftp(None)
    assert rep['existe'] and rep['errores'] == [] and rep['descargados'] == 5
    assert not (bajado / '.env').exists() and not (bajado / 'app' / 'notas.txt').exists()
    assert all(o.startswith('RETR /servicio/') for o in servidor.ordenes)

    c = remoto.comparar(str(espejo), str(laravel), str(bajado))
    assert c['iguales'] == ['app/Services/Igual.php', 'routes/api.php']
    assert c['distintos'] == ['app/Services/Cambiado.php']
    assert c['solo_local'] == ['routes/Custom/propio.php']
    assert c['solo_remoto'] == ['app/Http/Controllers/SubidoAMano.php', 'bootstrap/app.php']


def test_servidor_sin_despliegue_no_es_un_error(tmp_path):
    remoto.usar_fabrica_ftp(lambda _cfg: _FtpFalso({}))
    try:
        rep = remoto.descargar_backend({'ruta_remota': '/servicio'}, str(tmp_path / 'r'))
    finally:
        remoto.usar_fabrica_ftp(None)
    assert rep == {'existe': False, 'descargados': 0, 'errores': []}


def test_comando_comparar_remoto_usa_el_ftp_de_produccion(proyecto_nuevo, davgen):
    _accesos(proyecto_nuevo)
    codigo, salida = davgen(proyecto_nuevo, ['generar', '--local'])
    assert codigo == 0, salida
    usados = []

    def fabrica(cfg_ftp):
        usados.append(cfg_ftp['host'])
        return _FtpFalso({})
    remoto.usar_fabrica_ftp(fabrica)
    try:
        codigo, salida = davgen(proyecto_nuevo, ['comparar', '--remoto'])
    finally:
        remoto.usar_fabrica_ftp(None)
    assert usados == ['ftp.hosting.test']             # tomó _acceso.produccion.ini solo
    assert codigo == 1                                # hay archivos por subir
    assert 'primer despliegue' in salida and 'falta subirlos' in salida
