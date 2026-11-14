namespace App\Services;

use App\Utils\PaginationUtil;
use App\Utils\Parametro;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/**
 * Capa de servicios: TODA la lógica de datos pasa por aquí y CADA operación
 * valida la autenticación normal y la verificación en dos pasos (2FA) antes
 * de tocar la base de datos — defensa en profundidad, además del middleware
 * auth + VerificarPermiso de las rutas.
 */
abstract class BaseService
{
    /** Nombre del token emitido tras superar el 2FA (ver AuthController). */
    public const TOKEN_2FA = 'api-token-2fa';

    protected string $vista;
    protected string $procedimiento;
    protected array  $campos     = [];
    protected array  $operadores = ['=', '!=', 'like', '>', '<', '>=', '<='];

    /** Autenticación normal + 2FA. Lanza ExcepcionServicio si falla. */
    protected function verificarAutenticacion(): void
    {
        $user = auth()->user();
        if (!$user) {
            throw new ExcepcionServicio('No autenticado', 401);
        }
        if (!$user->activo) {
            throw new ExcepcionServicio('Usuario inactivo', 403);
        }
        // 2FA efectivo del usuario (si es obligatorio, mínimo por correo)
        $metodo = $user->metodo_2fa ?? 'ninguno';
        if ($metodo === 'ninguno' && Parametro::activo('2fa_obligatorio')) {
            $metodo = 'correo';
        }
        // Con 2FA activo, el token DEBE haber nacido en /auth/verificar
        if ($metodo !== 'ninguno'
            && $user->currentAccessToken()?->name !== self::TOKEN_2FA) {
            throw new ExcepcionServicio(
                'Sesión sin verificación en dos pasos: vuelve a iniciar sesión', 401);
        }
    }

    /** Listado paginado con filtros dinámicos sobre la vista del recurso.
     *  $publico=true omite la verificación de autenticación (rutas sin token). */
    public function listar(Request $request, bool $publico = false): array
    {
        if (!$publico) {
            $this->verificarAutenticacion();
        }
        $perPage = PaginationUtil::perPage((int) $request->input('per_page', 0));
        $page    = PaginationUtil::page((int) $request->input('page', 0));

        $query = DB::table($this->vista);
        foreach ((array) $request->input('filters', []) as $filtro) {
            $campo    = $filtro['field']    ?? '';
            $operador = $filtro['operator'] ?? '=';
            $valor    = $filtro['value']    ?? '';
            if (!in_array($campo, $this->campos)) {
                throw new ExcepcionServicio("Campo '{$campo}' no válido", 400);
            }
            if (!in_array($operador, $this->operadores)) {
                throw new ExcepcionServicio("Operador '{$operador}' no válido", 400);
            }
            $query->where($campo, $operador,
                $operador === 'like' ? "%{$valor}%" : $valor);
        }
        $resultado = $query->paginate(perPage: $perPage, page: $page);

        return [
            'item'       => $resultado->items(),
            'pagination' => [
                'total'        => $resultado->total(),
                'per_page'     => $resultado->perPage(),
                'current_page' => $resultado->currentPage(),
                'last_page'    => $resultado->lastPage(),
                'from'         => $resultado->firstItem() ?? 0,
                'to'           => $resultado->lastItem()  ?? 0,
            ],
        ];
    }

    /** CRUD vía procedimiento pcru* ('C','R','U','D').
     *  $publico=true omite la verificación de autenticación (rutas sin token). */
    public function ejecutar(string $accion, array $params, bool $publico = false): array
    {
        if (!$publico) {
            $this->verificarAutenticacion();
        }
        $marcas = implode(', ', array_fill(0, count($params) + 1, '?'));
        return DB::select(
            "CALL {$this->procedimiento}({$marcas})",
            array_merge([$accion], array_values($params)));
    }
}
