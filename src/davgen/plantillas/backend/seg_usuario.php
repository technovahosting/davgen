namespace App\Http\Controllers\seg;

use App\Http\Controllers\BaseController;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

class SegUsuarioController extends BaseController
{
    protected string $view          = 'vis_seg_usuario';
    protected array  $allowedFields = ['id', 'nombre', 'email', 'rol',
        'metodo_2fa', 'activo', 'created_at'];

    // ── POST /seguridad/usuarios/sel ───────────────────────────────────
    public function sel(Request $request): JsonResponse
    {
        return $this->selQuery($request);
    }

    // ── POST /seguridad/usuarios/add — { nombre, email, password, rol } ─
    public function add(Request $request): JsonResponse
    {
        $request->validate([
            'nombre'   => ['required', 'string', 'max:150'],
            'email'    => ['required', 'email', 'max:191',
                           'unique:tbl_seg_usuario,email'],
            'password' => ['required', 'string', 'min:8'],
            'rol'      => ['required', 'string', 'exists:tbl_seg_rol,nombre'],
        ]);
        $id = DB::table('tbl_seg_usuario')->insertGetId([
            'nombre'     => $request->nombre,
            'email'      => $request->email,
            'password'   => Hash::make($request->password),
            'rol'        => $request->rol,
            'activo'     => 1,
            'created_at' => now(),
            'updated_at' => now(),
        ]);
        $item = DB::table('vis_seg_usuario')->where('id', $id)->first();
        return $this->respuesta('Usuario creado', ['item' => [$item]]);
    }

    // ── POST /seguridad/usuarios/upd — { pid, nombre, rol, activo } ────
    public function upd(Request $request): JsonResponse
    {
        $request->validate([
            'pid'    => ['required', 'integer', 'exists:tbl_seg_usuario,id'],
            'nombre' => ['required', 'string', 'max:150'],
            'rol'    => ['required', 'string', 'exists:tbl_seg_rol,nombre'],
            'activo' => ['required', 'boolean'],
        ]);
        DB::table('tbl_seg_usuario')->where('id', $request->pid)->update([
            'nombre'     => $request->nombre,
            'rol'        => $request->rol,
            'activo'     => $request->boolean('activo') ? 1 : 0,
            'updated_at' => now(),
        ]);
        if (!$request->boolean('activo')) {
            // usuario desactivado: invalidar sus sesiones
            DB::table('personal_access_tokens')
                ->where('tokenable_id', $request->pid)->delete();
        }
        $item = DB::table('vis_seg_usuario')->where('id', $request->pid)->first();
        return $this->respuesta('Usuario actualizado', ['item' => [$item]]);
    }

    // ── POST /seguridad/usuarios/reset — { pid, password } ─────────────
    public function resetPassword(Request $request): JsonResponse
    {
        $request->validate([
            'pid'      => ['required', 'integer', 'exists:tbl_seg_usuario,id'],
            'password' => ['required', 'string', 'min:8'],
        ]);
        DB::table('tbl_seg_usuario')->where('id', $request->pid)->update([
            'password'   => Hash::make($request->password),
            'updated_at' => now(),
        ]);
        DB::table('personal_access_tokens')
            ->where('tokenable_id', $request->pid)->delete();
        return $this->respuesta('Contraseña restablecida', ['item' => []]);
    }
}
