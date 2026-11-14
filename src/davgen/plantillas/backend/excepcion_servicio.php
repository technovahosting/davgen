namespace App\Services;

/** Error de negocio/autorización lanzado por la capa de servicios. */
class ExcepcionServicio extends \RuntimeException
{
    public function __construct(string $mensaje, private int $estado = 400)
    {
        parent::__construct($mensaje);
    }

    public function estado(): int
    {
        return $this->estado;
    }
}
