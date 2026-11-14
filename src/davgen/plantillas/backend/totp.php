namespace App\Utils;

class Totp
{
    private const ALFABETO_B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

    public static function generarSecreto(int $longitud = 16): string
    {
        $s = '';
        for ($i = 0; $i < $longitud; $i++) {
            $s .= self::ALFABETO_B32[random_int(0, 31)];
        }
        return $s;
    }

    public static function uri(string $secreto, string $email, string $emisor): string
    {
        return 'otpauth://totp/' . rawurlencode($emisor . ':' . $email)
             . '?secret=' . $secreto . '&issuer=' . rawurlencode($emisor)
             . '&algorithm=SHA1&digits=6&period=30';
    }

    private static function base32Decode(string $b32): string
    {
        $b32  = strtoupper(preg_replace('/[^A-Za-z2-7]/', '', $b32));
        $bits = '';
        foreach (str_split($b32) as $c) {
            $bits .= str_pad(decbin(strpos(self::ALFABETO_B32, $c)), 5, '0', STR_PAD_LEFT);
        }
        $out = '';
        foreach (str_split($bits, 8) as $byte) {
            if (strlen($byte) === 8) {
                $out .= chr(bindec($byte));
            }
        }
        return $out;
    }

    public static function codigo(string $secreto, ?int $tiempo = null): string
    {
        $tiempo   = $tiempo ?? time();
        $contador = pack('N', 0) . pack('N', intdiv($tiempo, 30));
        $hash     = hash_hmac('sha1', $contador, self::base32Decode($secreto), true);
        $offset   = ord(substr($hash, -1)) & 0x0F;
        $valor    = (unpack('N', substr($hash, $offset, 4))[1] & 0x7FFFFFFF) % 1000000;
        return str_pad((string) $valor, 6, '0', STR_PAD_LEFT);
    }

    public static function verificar(string $secreto, string $codigo, int $ventana = 1): bool
    {
        $ahora = time();
        for ($i = -$ventana; $i <= $ventana; $i++) {
            if (hash_equals(self::codigo($secreto, $ahora + $i * 30), trim($codigo))) {
                return true;
            }
        }
        return false;
    }
}
