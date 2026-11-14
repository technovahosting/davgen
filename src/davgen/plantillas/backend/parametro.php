namespace App\Utils;

use Illuminate\Support\Facades\DB;

class Parametro
{
    /** Memo por request: una consulta por clave como máximo. */
    private static array $memo = [];

    public static function get(string $clave, string $defecto = ''): string
    {
        if (array_key_exists($clave, self::$memo)) {
            return self::$memo[$clave];
        }
        try {
            $v = (string) (DB::table('tbl_seg_parametro')
                ->where('clave', $clave)->where('activo', 1)
                ->value('valor') ?? $defecto);
        } catch (\Throwable) {
            $v = $defecto;
        }
        return self::$memo[$clave] = $v;
    }

    public static function entero(string $clave, int $defecto = 0): int
    {
        $v = self::get($clave, (string) $defecto);
        return is_numeric($v) ? (int) $v : $defecto;
    }

    public static function activo(string $clave, string $defecto = '0'): bool
    {
        return in_array(strtolower(self::get($clave, $defecto)),
            ['1', 'si', 'true'], true);
    }

    /** @return string[] valor de tipo lista (separado por comas) */
    public static function lista(string $clave, array $defecto = []): array
    {
        $v = self::get($clave);
        if ($v === '') {
            return $defecto;
        }
        return array_values(array_filter(array_map('trim', explode(',', $v))));
    }
}
