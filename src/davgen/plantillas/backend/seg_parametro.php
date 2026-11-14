namespace App\Http\Controllers\seg;

use App\Http\Controllers\BaseController;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class SegParametroController extends BaseController
{
    protected string $view          = 'vis_seg_parametro';
    protected array  $allowedFields = ['clave', 'valor', 'tipo',
        'descripcion', 'activo'];

    // ── POST /seguridad/parametros/sel ─────────────────────────────────
    public function sel(Request $request): JsonResponse
    {
        return $this->selQuery($request);
    }

    // ── POST /seguridad/parametros/upd — { clave, valor } ──────────────
    public function upd(Request $request): JsonResponse
    {
        $request->validate([
            'clave' => ['required', 'string', 'exists:tbl_seg_parametro,clave'],
            'valor' => ['required', 'string', 'max:500'],
        ]);
        DB::table('tbl_seg_parametro')->where('clave', $request->clave)
            ->update(['valor' => $request->valor, 'updated_at' => now()]);
        $item = DB::table('vis_seg_parametro')
            ->where('clave', $request->clave)->first();
        return $this->respuesta('Parámetro actualizado', ['item' => [$item]]);
    }
}
