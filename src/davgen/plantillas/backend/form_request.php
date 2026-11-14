namespace App\Http\Requests;

use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Http\Exceptions\HttpResponseException;

/**
 * Validación de __TABLA__ (add/upd) — reglas derivadas del esquema.
 * Para reglas de dominio: crear una clase que EXTIENDA esta (no editar aquí,
 * se regenera). El permiso de la ruta lo valida VerificarPermiso.
 */
class __CN__Request extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
__REGLAS__
        ];
    }

    /** Conserva el envelope de error de la API: { "error": { "text": ... } }. */
    protected function failedValidation(Validator $validator): void
    {
        throw new HttpResponseException(response()->json([
            'error' => ['text' => $validator->errors()->first()],
        ], 422));
    }
}
