namespace App\Http\Controllers;

use App\Utils\PaginationUtil;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

abstract class BaseController extends Controller
{
    protected string $view;
    protected array  $allowedFields    = [];
    protected array  $allowedOperators = ['=', '!=', 'like', '>', '<', '>=', '<='];

    /** Listado paginado con filtros dinámicos sobre la vista del recurso. */
    public function selQuery(Request $request): JsonResponse
    {
        $perPage = PaginationUtil::perPage((int) $request->input('per_page', 0));
        $page    = PaginationUtil::page((int) $request->input('page', 0));

        $query = DB::table($this->view);

        foreach ((array) $request->input('filters', []) as $filtro) {
            $campo    = $filtro['field']    ?? '';
            $operador = $filtro['operator'] ?? '=';
            $valor    = $filtro['value']    ?? '';

            if (!in_array($campo, $this->allowedFields)) {
                return $this->error("Campo '{$campo}' no válido", 400);
            }
            if (!in_array($operador, $this->allowedOperators)) {
                return $this->error("Operador '{$operador}' no válido", 400);
            }
            $query->where($campo, $operador,
                $operador === 'like' ? "%{$valor}%" : $valor);
        }

        $resultado = $query->paginate(perPage: $perPage, page: $page);

        return $this->respuesta('Lista de ' . class_basename(static::class), [
            'item'       => $resultado->items(),
            'pagination' => [
                'total'        => $resultado->total(),
                'per_page'     => $resultado->perPage(),
                'current_page' => $resultado->currentPage(),
                'last_page'    => $resultado->lastPage(),
                'from'         => $resultado->firstItem() ?? 0,
                'to'           => $resultado->lastItem()  ?? 0,
            ],
        ]);
    }

    /** Envelope estándar v4: { mensaje, info } */
    protected function respuesta(string $mensaje, array $info, int $estado = 200): JsonResponse
    {
        return response()->json(['mensaje' => $mensaje, 'info' => $info], $estado);
    }

    /**
     * Respuesta para un error de la base de datos SIN detalles internos.
     * Solo el mensaje de un SIGNAL de un procedimiento (SQLSTATE 45000) es para
     * el usuario: lo escribió quien programó la regla de negocio. Cualquier
     * otro error de MySQL nombra columnas, índices o tipos («Data truncated for
     * column…», «Duplicate entry … for key …»): al cliente va un texto genérico
     * y el detalle queda en el log.
     */
    protected function errorBd(\Illuminate\Database\QueryException $e): JsonResponse
    {
        $estado = (string) ($e->errorInfo[0] ?? '');
        $codigo = (int) ($e->errorInfo[1] ?? 0);
        if ($estado === '45000') {
            return $this->error($e->errorInfo[2] ?? 'Operación rechazada');
        }
        return match (true) {
            $codigo === 1062 => $this->error('Ya existe un registro con esos datos', 422),
            in_array($codigo, [1451, 1452], true)
                => $this->error('El registro está relacionado con otros datos', 422),
            in_array($codigo, [1048, 1264, 1265, 1292, 1366, 1406], true)
                => $this->error('Algún dato no tiene el formato o el tamaño esperado', 422),
            default => $this->error('Error de base de datos'),
        };
    }

    /** true si $valor es un identificador entero no negativo. */
    protected function esId(mixed $valor): bool
    {
        return (is_int($valor) && $valor >= 0)
            || (is_string($valor) && $valor !== '' && ctype_digit($valor) && strlen($valor) <= 18);
    }

    protected function error(string $texto, int $estado = 500): JsonResponse
    {
        return response()->json(['error' => ['text' => $texto]], $estado);
    }
}
