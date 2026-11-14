namespace App\Http\Controllers\seg;

use App\Http\Controllers\BaseController;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class SegRolController extends BaseController
{
    protected string $view          = 'vis_seg_rol';
    protected array  $allowedFields = ['id', 'nombre', 'descripcion',
        'es_admin', 'activo'];

    // ── POST /seguridad/roles/sel ──────────────────────────────────────
    public function sel(Request $request): JsonResponse
    {
        return $this->selQuery($request);
    }

    // ── POST /seguridad/roles/add — { nombre, descripcion, es_admin } ──
    public function add(Request $request): JsonResponse
    {
        $request->validate([
            'nombre'      => ['required', 'string', 'max:50',
                              'unique:tbl_seg_rol,nombre'],
            'descripcion' => ['nullable', 'string', 'max:255'],
            'es_admin'    => ['nullable', 'boolean'],
        ]);
        $id = DB::table('tbl_seg_rol')->insertGetId([
            'nombre'      => $request->nombre,
            'descripcion' => $request->input('descripcion'),
            'es_admin'    => $request->boolean('es_admin') ? 1 : 0,
            'activo'      => 1,
            'created_at'  => now(),
            'updated_at'  => now(),
        ]);
        $item = DB::table('vis_seg_rol')->where('id', $id)->first();
        return $this->respuesta('Rol creado', ['item' => [$item]]);
    }

    // ── POST /seguridad/roles/upd — { pid, descripcion, es_admin, activo }
    //    (el nombre no se renombra: tbl_seg_usuario.rol lo referencia) ───
    public function upd(Request $request): JsonResponse
    {
        $request->validate([
            'pid'         => ['required', 'integer', 'exists:tbl_seg_rol,id'],
            'descripcion' => ['nullable', 'string', 'max:255'],
            'es_admin'    => ['required', 'boolean'],
            'activo'      => ['required', 'boolean'],
        ]);
        DB::table('tbl_seg_rol')->where('id', $request->pid)->update([
            'descripcion' => $request->input('descripcion'),
            'es_admin'    => $request->boolean('es_admin') ? 1 : 0,
            'activo'      => $request->boolean('activo') ? 1 : 0,
            'updated_at'  => now(),
        ]);
        $item = DB::table('vis_seg_rol')->where('id', $request->pid)->first();
        return $this->respuesta('Rol actualizado', ['item' => [$item]]);
    }
}
