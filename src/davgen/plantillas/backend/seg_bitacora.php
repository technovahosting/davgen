namespace App\Http\Controllers\seg;

use App\Http\Controllers\BaseController;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class SegBitacoraController extends BaseController
{
    protected string $view          = 'vis_seg_bitacora';
    protected array  $allowedFields = ['id', 'usuario_id', 'usuario_nombre',
        'usuario_email', 'modulo', 'operacion', 'ip', 'created_at'];

    // ── POST /seguridad/bitacora/sel — solo lectura ────────────────────
    public function sel(Request $request): JsonResponse
    {
        return $this->selQuery($request);
    }
}
