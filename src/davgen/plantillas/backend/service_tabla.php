namespace App\Services;

/**
 * Servicio de __TABLA__ — listar (vista __VISTA__) + CRUD (pcru__CN__).
 * Hereda de BaseService la validación de autenticación normal + 2FA.
 * Agregar aquí (en una clase hija o trait) la lógica de negocio propia.
 */
class __CN__Service extends BaseService
{
    protected string $vista         = '__VISTA__';
    protected string $procedimiento = 'pcru__CN__';
    protected array  $campos        = [__CAMPOS__];
}
