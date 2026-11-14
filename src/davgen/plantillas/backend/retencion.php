namespace App\Utils;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

/**
 * Conservación de datos: borra lo que ya cumplió su plazo.
 *
 *   · bitácora ............ tbl_seg_parametro.retencion_bitacora_dias (0 = no se borra)
 *   · códigos de verificación, enlaces de recuperación y sesiones vencidas:
 *     un día después de vencer.
 *
 * El hosting compartido no siempre permite programar tareas: la limpieza se
 * hace aprovechando uno de cada UNO_DE_CADA inicios de sesión. Nunca hace
 * fallar el ingreso: si algo sale mal, queda anotado en el log y nada más.
 * Las cuentas, los archivos y los datos del negocio NO se tocan.
 */
class Retencion
{
    private const UNO_DE_CADA = 20;
    private const DIAS_BITACORA = __DIAS_BITACORA__;   // semilla; manda tbl_seg_parametro

    public static function quizas(): void
    {
        if (random_int(1, self::UNO_DE_CADA) === 1) {
            self::aplicar();
        }
    }

    /** @return array<string,int> filas borradas por tabla */
    public static function aplicar(): array
    {
        $borradas = [];
        try {
            $dias = Parametro::entero('retencion_bitacora_dias', self::DIAS_BITACORA);
            if ($dias > 0) {
                $borradas['bitacora'] = DB::table('tbl_seg_bitacora')
                    ->where('created_at', '<', now()->subDays($dias))->delete();
            }
            $ayer = now()->subDay();
            $borradas['codigos'] = DB::table('tbl_seg_codigo_verificacion')
                ->where('expira_en', '<', $ayer)->delete();
            $borradas['recuperacion'] = DB::table('tbl_seg_token_reset')
                ->where('created_at', '<', $ayer)->delete();
            $borradas['sesiones'] = DB::table('personal_access_tokens')
                ->whereNotNull('expires_at')->where('expires_at', '<', $ayer)->delete();
        } catch (\Throwable $e) {
            Log::warning('Retención de datos: no se pudo completar la limpieza', [
                'error' => $e->getMessage(),
            ]);
        }
        return $borradas;
    }
}
