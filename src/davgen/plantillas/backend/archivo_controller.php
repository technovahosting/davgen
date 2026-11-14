namespace App\Http\Controllers;

use App\Utils\Parametro;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Symfony\Component\HttpFoundation\StreamedResponse;

class ArchivoController extends BaseController
{
    protected string $view          = 'vis_seg_archivo';
    protected array  $allowedFields = ['id', 'usuario_id', 'usuario_nombre',
        'nombre_original', 'mime', 'extension', 'tamanio_kb', 'descripcion',
        'activo', 'created_at'];

    /** Semilla de generación — en runtime manda tbl_seg_parametro */
    private const EXTENSIONES = [__EXTENSIONES__];
    private const MAX_MB      = __MAX_MB__;

    // ── POST /archivos/subir — multipart: archivo + descripcion ───────
    public function subir(Request $request): JsonResponse
    {
        $extensiones = Parametro::lista('extensiones_archivo', self::EXTENSIONES);
        $maxKb       = Parametro::entero('max_archivo_mb', self::MAX_MB) * 1024;
        $request->validate([
            'archivo'     => ['required', 'file',
                              'mimes:' . implode(',', $extensiones),
                              'max:' . $maxKb],
            'descripcion' => ['nullable', 'string', 'max:255'],
        ]);

        $user    = $request->user();
        $archivo = $request->file('archivo');
        $ruta    = $archivo->store("archivos/{$user->id}");

        $id = DB::table('tbl_seg_archivo')->insertGetId([
            'usuario_id'      => $user->id,
            'nombre_original' => $archivo->getClientOriginalName(),
            'ruta'            => $ruta,
            'mime'            => $archivo->getClientMimeType(),
            'extension'       => strtolower($archivo->getClientOriginalExtension()),
            'tamanio_kb'      => (int) round($archivo->getSize() / 1024),
            'descripcion'     => $request->input('descripcion'),
            'activo'          => 1,
            'created_at'      => now(),
            'updated_at'      => now(),
        ]);

        $registro = DB::table('vis_seg_archivo')->where('id', $id)->first();
        return $this->respuesta('Archivo subido', ['item' => [$registro]]);
    }

    // ── POST /archivos/sel — listado: propios (admin ve todos) ────────
    public function sel(Request $request): JsonResponse
    {
        $user = $request->user();
        if (!$user->esAdmin()) {
            // forzar el filtro de dueño para usuarios no admin
            $filtros   = (array) $request->input('filters', []);
            $filtros[] = ['field' => 'usuario_id', 'operator' => '=', 'value' => $user->id];
            $request->merge(['filters' => $filtros]);
        }
        return $this->selQuery($request);
    }

    // ── POST /archivos/descargar — { pid } ────────────────────────────
    public function descargar(Request $request): StreamedResponse|JsonResponse
    {
        $fila = $this->archivoAutorizado($request);
        if ($fila instanceof JsonResponse) {
            return $fila;
        }
        if (!Storage::exists($fila->ruta)) {
            return $this->error('El archivo físico no existe en el servidor', 404);
        }
        return Storage::download($fila->ruta, $fila->nombre_original);
    }

    // ── POST /archivos/del — { pid } · borrado lógico ─────────────────
    public function eliminar(Request $request): JsonResponse
    {
        $fila = $this->archivoAutorizado($request);
        if ($fila instanceof JsonResponse) {
            return $fila;
        }
        DB::table('tbl_seg_archivo')->where('id', $fila->id)
            ->update(['activo' => 0, 'updated_at' => now()]);
        return $this->respuesta('Archivo eliminado', ['item' => []]);
    }

    /** Busca el archivo y valida que el usuario sea dueño o admin. */
    private function archivoAutorizado(Request $request): \stdClass|JsonResponse
    {
        $request->validate(['pid' => ['required', 'integer']]);
        $fila = DB::table('tbl_seg_archivo')
            ->where('id', $request->pid)->where('activo', 1)->first();
        if (!$fila) {
            return $this->error('Archivo no encontrado', 404);
        }
        $user = $request->user();
        if (!$user->esAdmin() && $fila->usuario_id !== $user->id) {
            return $this->error('Sin permiso sobre este archivo', 403);
        }
        return $fila;
    }
}
