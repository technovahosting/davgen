namespace App\Http\Web;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;

// La raíz NO sirve la vista welcome (este es un backend de API): devuelve un
// health-check JSON con el estado de la base de datos.
Route::get('/', function () {
    $bd = 'ok';
    try {
        DB::select('SELECT 1');
    } catch (\Throwable $e) {
        $bd = 'error';
    }
    return response()->json([
        'servicio' => '__NOMBRE__',
        'estado'   => 'activo',
        'bd'       => $bd,
        'api'      => url('/api'),
        'hora'     => now()->toIso8601String(),
    ], $bd === 'ok' ? 200 : 503);
});
