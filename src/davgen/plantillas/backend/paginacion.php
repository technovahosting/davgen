namespace App\Utils;

class PaginationUtil
{
    const PER_PAGE     = 15;
    const MAX_PER_PAGE = 100;
    const FIRST_PAGE   = 1;

    public static function perPage(int $solicitado = 0): int
    {
        return $solicitado <= 0 ? self::PER_PAGE : min($solicitado, self::MAX_PER_PAGE);
    }

    public static function page(int $solicitada = 0): int
    {
        return $solicitada > 0 ? $solicitada : self::FIRST_PAGE;
    }
}
