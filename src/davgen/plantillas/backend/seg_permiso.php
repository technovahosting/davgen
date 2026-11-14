namespace App\Http\Controllers\seg;

use App\Http\Controllers\BaseController;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class SegPermisoController extends BaseController
{
    protected string $view          = 'vis_seg_permiso';
    protected array  $allowedFields = ['rol_id', 'rol_nombre', 'modulo_id',
        'modulo_clave', 'modulo_titulo', 'modulo_tipo',
        'sel', 'get', 'add', 'upd', 'del'];

    // ── POST /seguridad/permisos/matriz — roles × módulos × operaciones ─
    public function matriz(Request $request): JsonResponse
    {
        return $this->respuesta('Matriz de permisos', [
            'roles'    => DB::table('vis_seg_rol')->where('activo', 1)
                            ->orderBy('nombre')->get(),
            'modulos'  => DB::table('vis_seg_modulo')->where('activo', 1)
                            ->orderBy('orden')->get(),
            'permisos' => DB::table('vis_seg_permiso')->get(),
        ]);
    }

    // ── POST /seguridad/permisos/guardar — { rol_id, modulo_id, sel..del }
    public function guardar(Request $request): JsonResponse
    {
        $request->validate([
            'rol_id'    => ['required', 'integer', 'exists:tbl_seg_rol,id'],
            'modulo_id' => ['required', 'integer', 'exists:tbl_seg_modulo,id'],
            'sel'       => ['required', 'boolean'],
            'get'       => ['required', 'boolean'],
            'add'       => ['required', 'boolean'],
            'upd'       => ['required', 'boolean'],
            'del'       => ['required', 'boolean'],
        ]);
        DB::table('tbl_seg_permiso')->updateOrInsert(
            ['rol_id' => $request->rol_id, 'modulo_id' => $request->modulo_id],
            [
                'sel'        => $request->boolean('sel') ? 1 : 0,
                'get'        => $request->boolean('get') ? 1 : 0,
                'add'        => $request->boolean('add') ? 1 : 0,
                'upd'        => $request->boolean('upd') ? 1 : 0,
                'del'        => $request->boolean('del') ? 1 : 0,
                'updated_at' => now(),
            ],
        );
        return $this->respuesta('Permiso guardado', ['item' => []]);
    }
}
