namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Illuminate\Support\Facades\DB;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    use HasApiTokens, HasFactory, Notifiable;

    protected $table = 'tbl_seg_usuario';

    protected $fillable = ['nombre', 'email', 'password', 'rol', 'activo'];

    protected $hidden = ['password', 'remember_token', 'totp_secret'];

    /** Memo por request del flag es_admin por rol. */
    private static array $memoAdmin = [];

    /** Rol con es_admin=1 en tbl_seg_rol: acceso total, ignora permisos. */
    public function esAdmin(): bool
    {
        return self::$memoAdmin[$this->rol] ??= (bool) DB::table('tbl_seg_rol')
            ->where('nombre', $this->rol)->where('activo', 1)
            ->value('es_admin');
    }

    protected function casts(): array
    {
        return [
            'email_verificado_en' => 'datetime',
            'password'            => 'hashed',
            'activo'              => 'boolean',
        ];
    }
}
