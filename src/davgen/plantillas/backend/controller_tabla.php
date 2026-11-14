namespace App\Http\Controllers\__MOD__;

use App\Http\Controllers\BaseController;
use App\Services\ExcepcionServicio;
use App\Services\__CN__Service;
use Illuminate\Database\QueryException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
__USE_REQUEST__
/** Controller delgado — módulo __MOD__: la lógica vive en __CN__Service. */
class __CTRL_CLASS__ extends BaseController
{
    protected string $view          = '__VISTA__';
    protected array  $allowedFields = [__CAMPOS__];

    private __CN__Service $servicio;

    public function __construct()
    {
        $this->servicio = new __CN__Service();
    }

    public function listar(Request $request): JsonResponse
    {
        try {
            return $this->respuesta('Lista de __CN__', $this->servicio->listar($request));
        } catch (ExcepcionServicio $e) {
            return $this->error($e->getMessage(), $e->estado());
        }
    }

    private function _ejecutar(string $accion, Request $request): JsonResponse
    {
__VALIDAR_ID__        try {
            $item = $this->servicio->ejecutar(
                $accion, array_values($this->inputParams($request)));
            return $this->respuesta("$accion __CN__", ['item' => $item]);
        } catch (ExcepcionServicio $e) {
            return $this->error($e->getMessage(), $e->estado());
        } catch (QueryException $e) {
            // Al cliente solo el MESSAGE_TEXT (ej. SIGNAL 1644 del SP);
            // el detalle técnico (SQLSTATE, CALL, conexión) queda en el log.
            Log::error("pcru__CN__ {$accion}: " . $e->getMessage());
            return $this->errorBd($e);
        } catch (\Exception $e) {
            Log::error("pcru__CN__ {$accion}: " . $e->getMessage());
            return $this->error('Error interno del servidor');
        }
    }

    private function inputParams(Request $request): array
    {
        return [
__PARAMS__
        ];
    }

    public function obtener(Request $r): JsonResponse      { return $this->_ejecutar('R', $r); }
    public function guardar(__REQADD__ $r): JsonResponse   { return $this->_ejecutar('C', $r); }
    public function actualizar(__REQUPD__ $r): JsonResponse { return $this->_ejecutar('U', $r); }
    public function eliminar(Request $r): JsonResponse     { return $this->_ejecutar('D', $r); }
__EXPORT_METODO__
    // ── Rutas públicas (sin token) — solo lectura ──
    public function listarPublico(Request $request): JsonResponse
    {
        try {
            return $this->respuesta('Lista de __CN__', $this->servicio->listar($request, true));
        } catch (ExcepcionServicio $e) {
            return $this->error($e->getMessage(), $e->estado());
        }
    }

    public function obtenerPublico(Request $request): JsonResponse
    {
__VALIDAR_ID_R__        try {
            $item = $this->servicio->ejecutar('R', array_values($this->inputParams($request)), true);
            return $this->respuesta('R __CN__', ['item' => $item]);
        } catch (ExcepcionServicio $e) {
            return $this->error($e->getMessage(), $e->estado());
        } catch (QueryException $e) {
            Log::error('pcru__CN__ R publico: ' . $e->getMessage());
            return $this->errorBd($e);
        } catch (\Exception $e) {
            Log::error('pcru__CN__ R publico: ' . $e->getMessage());
            return $this->error('Error interno del servidor');
        }
    }

    // ── POST público (sin token): alta desde formularios del portal (cotización,
    //    cita, contacto…). Honeypot anti-bots + solo los campos `p{columna}` de la
    //    tabla (inputParams ya hace whitelist). La ruta lleva throttle por IP. ──
    public function guardarPublico(Request $request): JsonResponse
    {
        if ($request->filled('_hp')) {            // honeypot: campo señuelo lleno = bot
            return $this->respuesta('OK __CN__', ['item' => null]);
        }
        try {
            // alta pública: el visitante no elige el id ni el estado del registro
            $params = $this->inputParams($request);
__PUBLICO_FIJOS__            $item = $this->servicio->ejecutar('C', array_values($params), true);
            return $this->respuesta('C __CN__', ['item' => $item]);
        } catch (ExcepcionServicio $e) {
            return $this->error($e->getMessage(), $e->estado());
        } catch (QueryException $e) {
            Log::error('pcru__CN__ C publico: ' . $e->getMessage());
            return $this->errorBd($e);
        } catch (\Exception $e) {
            Log::error('pcru__CN__ C publico: ' . $e->getMessage());
            return $this->error('Error interno del servidor');
        }
    }
}
