namespace App\Http\Middleware;

use App\Utils\Parametro;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Symfony\Component\HttpFoundation\Response;

class VerificarPermiso
{
    /** Memo por request: una consulta por rol|módulo visitado. */
    private static array $memo = [];

    private const OPS_ESCRITURA = ['add', 'upd', 'del'];

    /** Uso en rutas: ->middleware(VerificarPermiso::class . ':modulo,operacion') */
    public function handle(Request $request, Closure $next,
                           string $modulo, string $operacion): Response
    {
        $user = $request->user();
        if (!$user) {
            return response()->json(['error' => ['text' => 'No autenticado']], 401);
        }
        if (!$user->esAdmin()) {
            $clave = $user->rol . '|' . $modulo;
            $fila  = self::$memo[$clave] ??= DB::table('tbl_seg_permiso AS p')
                ->join('tbl_seg_rol AS r', 'r.id', '=', 'p.rol_id')
                ->join('tbl_seg_modulo AS m', 'm.id', '=', 'p.modulo_id')
                ->where('r.nombre', $user->rol)->where('r.activo', 1)
                ->where('m.clave', $modulo)->where('m.activo', 1)
                ->select('p.sel', 'p.get', 'p.add', 'p.upd', 'p.del')
                ->first() ?? false;
            if (!$fila || !$fila->{$operacion}) {
                return response()->json(['error' => [
                    'text' => "Sin permiso '{$operacion}' sobre '{$modulo}'",
                ]], 403);
            }
        }

        $respuesta = $next($request);

        // Bitácora de escrituras exitosas (configurable en tbl_seg_parametro)
        if (in_array($operacion, self::OPS_ESCRITURA, true)
            && $respuesta->getStatusCode() < 400
            && Parametro::activo('bitacora_activa', '1')) {
            DB::table('tbl_seg_bitacora')->insert([
                'usuario_id' => $user->id,
                'modulo'     => $modulo,
                'operacion'  => $operacion,
                'detalle'    => mb_substr(json_encode(
                    $request->except(['password', 'archivo'])), 0, 500),
                'ip'         => $request->ip(),
                'created_at' => now(),
            ]);
        }
        return $respuesta;
    }
}
