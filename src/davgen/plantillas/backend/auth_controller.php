namespace App\Http\Controllers;

use App\Models\User;
use App\Utils\Parametro;
use App\Utils\Totp;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;

class AuthController extends Controller
{
    /** Hash bcrypt de un valor aleatorio descartado: no abre ninguna cuenta. */
    private const HASH_SENUELO = '$2y$12$28BJVIqFVn4U4wuK.WzLFOgi2pVH8sg8phEBjiVBuVJ5Vcy5LQT0C';

    // ── helpers ──────────────────────────────────────────────────────
    private function usuarioValido(Request $request): User|JsonResponse
    {
        $request->validate([
            'email'    => ['required', 'email'],
            'password' => ['required', 'string'],
        ]);
        $user = User::where('email', $request->email)->first();
        if (!$user) {
            // se calcula un hash igual: si no, responder más rápido cuando el
            // correo no existe permite averiguar qué correos están registrados
            Hash::check($request->password, self::HASH_SENUELO);
        }
        if (!$user || !Hash::check($request->password, $user->password)) {
            return response()->json(['error' => ['text' => 'Credenciales incorrectas']], 401);
        }
        if (!$user->activo) {
            return response()->json(['error' => ['text' => 'Usuario inactivo']], 403);
        }
        return $user;
    }

    private function emitirToken(User $user, bool $con2fa = false): JsonResponse
    {
        if (Parametro::activo('sesion_unica', '1')) {
            $user->tokens()->delete();   // un solo token activo por usuario
        }
        if (Parametro::activo('bitacora_activa', '1')) {
            DB::table('tbl_seg_bitacora')->insert([
                'usuario_id' => $user->id,
                'modulo'     => 'auth',
                'operacion'  => 'login',
                'detalle'    => null,
                'ip'         => request()->ip(),
                'created_at' => now(),
            ]);
        }
        // conservación de datos: de vez en cuando borra lo que cumplió su plazo
        \App\Utils\Retencion::quizas();
        return response()->json([
            'mensaje' => 'Login exitoso',
            'info'    => [
                // el nombre del token registra si la sesión superó el 2FA;
                // la capa de servicios (BaseService) lo exige cuando aplica
                'token' => $user->createToken(
                    $con2fa ? \App\Services\BaseService::TOKEN_2FA : 'api-token',
                    ['*'],
                    // la sesión vence: tbl_seg_parametro.sesion_minutos (0 = nunca)
                    ($minutos = Parametro::entero('sesion_minutos', 720)) > 0
                        ? now()->addMinutes($minutos) : null
                )->plainTextToken,
                'user'  => $this->datosUsuario($user),
            ],
        ]);
    }

    /** Método 2FA efectivo: si el parámetro 2fa_obligatorio está activo y el
     *  usuario no enroló ninguno, se fuerza el código por correo. */
    private function metodoEfectivo(User $user): string
    {
        $metodo = $user->metodo_2fa ?? 'ninguno';
        if ($metodo === 'ninguno' && Parametro::activo('2fa_obligatorio')) {
            return 'correo';
        }
        return $metodo;
    }

    private function datosUsuario(User $user): array
    {
        return [
            'id'         => $user->id,
            'nombre'     => $user->nombre,
            'email'      => $user->email,
            'rol'        => $user->rol,
            'metodo_2fa' => $user->metodo_2fa ?? 'ninguno',
        ];
    }

    private function enviarCodigo(User $user, string $proposito): void
    {
        $minutos = Parametro::entero('codigo_2fa_minutos', 10);
        $codigo  = str_pad((string) random_int(0, 999999), 6, '0', STR_PAD_LEFT);
        DB::table('tbl_seg_codigo_verificacion')->insert([
            'usuario_id' => $user->id,
            'codigo'     => hash('sha256', $codigo),
            'proposito'  => $proposito,
            'expira_en'  => now()->addMinutes($minutos),
            'usado'      => 0,
            'created_at' => now(),
        ]);
        try {
            Mail::raw(
                "Tu código de verificación es: {$codigo}\n"
                . "Vence en {$minutos} minutos.",
                fn ($m) => $m->to($user->email)->subject('Código de verificación'),
            );
        } catch (\Exception $e) {
            // Sin MAIL_* configurado. El código SOLO se anota en el log en
            // desarrollo (APP_DEBUG=true): en producción el log no debe tener
            // nunca un código válido — quien lo lea entra sin el correo.
            if (config('app.debug')) {
                Log::info("[2fa] código {$proposito} para {$user->email}: {$codigo} "
                    . '(' . $e->getMessage() . ')');
            } else {
                Log::error("[2fa] no se pudo enviar el código a {$user->email}: "
                    . $e->getMessage() . ' — configurar MAIL_* en .env');
            }
        }
    }

    private function validarCodigoCorreo(User $user, string $codigo, string $proposito): bool
    {
        $fila = DB::table('tbl_seg_codigo_verificacion')
            ->where('usuario_id', $user->id)
            ->where('proposito', $proposito)
            ->where('usado', 0)
            ->where('expira_en', '>=', now())
            ->where('codigo', hash('sha256', trim($codigo)))
            ->orderByDesc('id')
            ->first();
        if (!$fila) {
            return false;
        }
        DB::table('tbl_seg_codigo_verificacion')->where('id', $fila->id)->update(['usado' => 1]);
        return true;
    }

    // ── POST /auth/login — público · paso 1 ──────────────────────────
    public function login(Request $request): JsonResponse
    {
        $user = $this->usuarioValido($request);
        if ($user instanceof JsonResponse) {
            return $user;
        }
        // Política: los roles "solo Google" (tbl_seg_parametro.roles_solo_google)
        // NO pueden entrar por contraseña.
        if ($this->rolSoloGoogle($user->rol)) {
            return response()->json(['error' => ['text' =>
                'Este usuario debe ingresar con Google']], 403);
        }
        $metodo = $this->metodoEfectivo($user);
        if ($metodo === 'ninguno') {
            return $this->emitirToken($user);
        }
        if ($metodo === 'correo') {
            $this->enviarCodigo($user, 'login');
        }
        return response()->json([
            'mensaje' => 'Verificación en dos pasos requerida',
            'info'    => ['requiere_2fa' => true, 'metodo' => $metodo],
        ]);
    }

    // ── POST /auth/verificar — público · paso 2 ──────────────────────
    public function verificar(Request $request): JsonResponse
    {
        $request->validate(['codigo' => ['required', 'string']]);
        $user = $this->usuarioValido($request);
        if ($user instanceof JsonResponse) {
            return $user;
        }
        $valido = match ($this->metodoEfectivo($user)) {
            'app'    => $user->totp_secret && Totp::verificar($user->totp_secret, $request->codigo),
            'correo' => $this->validarCodigoCorreo($user, $request->codigo, 'login'),
            default  => false,
        };
        if (!$valido) {
            return response()->json(['error' => ['text' => 'Código inválido o vencido']], 401);
        }
        return $this->emitirToken($user, con2fa: true);
    }

    // ── POST /auth/google — público · inicio de sesión con Google ─────
    // Se habilita/deshabilita DESDE LA BASE DE DATOS (tbl_seg_parametro):
    //   google_auth_activo = 1   y   google_client_id = <Client ID OAuth>
    // El frontend envía el ID token de Google Identity Services en
    // { credential }; aquí se verifica contra Google (firma, vigencia y
    // audiencia) y se emite el token de la API para el usuario YA
    // registrado en tbl_seg_usuario con ese email (el alta es de admin).
    public function googleLogin(Request $request): JsonResponse
    {
        if (!Parametro::activo('google_auth_activo', '0')) {
            return response()->json(['error' => ['text' =>
                'Autenticación con Google deshabilitada '
                . '(tbl_seg_parametro: google_auth_activo)']], 403);
        }
        $request->validate(['credential' => ['required', 'string']]);

        $clientId = Parametro::get('google_client_id');
        if ($clientId === '') {
            return response()->json(['error' => ['text' =>
                'Falta configurar google_client_id en tbl_seg_parametro']], 500);
        }

        try {
            $respuesta = Http::timeout(10)->get(
                'https://oauth2.googleapis.com/tokeninfo',
                ['id_token' => $request->credential]);
        } catch (\Exception $e) {
            Log::error('auth/google: ' . $e->getMessage());
            return response()->json(['error' => ['text' =>
                'No se pudo verificar el token con Google']], 502);
        }
        $datos = $respuesta->json() ?? [];
        if (!$respuesta->ok()
            || ($datos['aud'] ?? '') !== $clientId
            || ($datos['email_verified'] ?? '') !== 'true'
            || empty($datos['email'])) {
            return response()->json(['error' => ['text' => 'Token de Google inválido']], 401);
        }

        $email  = $datos['email'];
        $nombre = $datos['name'] ?? $email;
        $user   = User::where('email', $email)->first();
        if (!$user) {
            // ¿dominio auto-aceptado? -> alta automática como cliente verificado
            $dominio = strtolower(substr(strrchr($email, '@'), 1));
            $permitidos = array_filter(array_map('trim', explode(',',
                strtolower(Parametro::get('google_dominios_permitidos', '')))));
            if (in_array($dominio, $permitidos, true)) {
                DB::table('tbl_seg_usuario')->insert([
                    'nombre' => $nombre, 'email' => $email, 'password' => '',
                    'rol' => 'cliente', 'activo' => 1, 'created_at' => now(),
                ]);
                $user = User::where('email', $email)->first();
            } else {
                // cola de aprobación: el owner/admin decide desde el panel
                DB::table('tbl_seg_acceso_solicitud')->updateOrInsert(
                    ['email' => $email],
                    ['nombre' => $nombre, 'estado' => 'pendiente', 'rol' => 'cliente',
                     'origen' => 'google', 'updated_at' => now()]
                );
                return response()->json(['error' => ['text' =>
                    'Tu acceso quedó PENDIENTE de aprobación por el administrador']], 403);
            }
        }
        if (!$user->activo) {
            return response()->json(['error' => ['text' => 'Usuario inactivo']], 403);
        }
        // Google verificó la identidad: cuenta como verificación fuerte (2FA)
        return $this->emitirToken($user, con2fa: true);
    }

    // ── GET /config-publica — config pública para el front (sin token) ────
    public function configPublica(): JsonResponse
    {
        return response()->json(['info' => [
            'google_auth_activo' => Parametro::activo('google_auth_activo', '0'),
            'google_client_id'   => Parametro::get('google_client_id', ''),
        ]]);
    }

    /** ¿El rol solo puede entrar con Google? (tbl_seg_parametro.roles_solo_google) */
    private function rolSoloGoogle(string $rol): bool
    {
        $lista = array_filter(array_map('trim', explode(',',
            strtolower(Parametro::get('roles_solo_google', '')))));
        return in_array(strtolower($rol), $lista, true);
    }

    // ── Cola de solicitudes de acceso (Google) — administra el owner/admin ─
    public function accesosPendientes(Request $request): JsonResponse
    {
        if (!$request->user()->esAdmin()) {
            return response()->json(['error' => ['text' => 'Solo administradores']], 403);
        }
        $filas = DB::table('vis_seg_acceso_solicitud')
            ->where('estado', 'pendiente')->orderBy('created_at')->get();
        return response()->json(['info' => $filas]);
    }

    public function accesoAprobar(Request $request): JsonResponse
    {
        if (!$request->user()->esAdmin()) {
            return response()->json(['error' => ['text' => 'Solo administradores']], 403);
        }
        $request->validate(['id' => ['required', 'integer'], 'rol' => ['nullable', 'string']]);
        $sol = DB::table('tbl_seg_acceso_solicitud')->where('id', $request->id)->first();
        if (!$sol) {
            return response()->json(['error' => ['text' => 'Solicitud no encontrada']], 404);
        }
        $rol = $request->rol ?: ($sol->rol ?: 'cliente');
        $u   = DB::table('tbl_seg_usuario')->where('email', $sol->email)->first();
        if ($u) {
            DB::table('tbl_seg_usuario')->where('id', $u->id)
              ->update(['rol' => $rol, 'activo' => 1, 'updated_at' => now()]);
        } else {
            DB::table('tbl_seg_usuario')->insert([
                'nombre' => $sol->nombre ?: $sol->email, 'email' => $sol->email,
                'password' => '', 'rol' => $rol, 'activo' => 1, 'created_at' => now(),
            ]);
        }
        DB::table('tbl_seg_acceso_solicitud')->where('id', $sol->id)->update([
            'estado' => 'aprobada', 'rol' => $rol, 'resuelto_por' => $request->user()->id,
            'resuelto_at' => now(), 'updated_at' => now(),
        ]);
        return response()->json(['mensaje' => 'Acceso aprobado para ' . $sol->email]);
    }

    public function accesoDenegar(Request $request): JsonResponse
    {
        if (!$request->user()->esAdmin()) {
            return response()->json(['error' => ['text' => 'Solo administradores']], 403);
        }
        $request->validate(['id' => ['required', 'integer']]);
        DB::table('tbl_seg_acceso_solicitud')->where('id', $request->id)->update([
            'estado' => 'denegada', 'resuelto_por' => $request->user()->id,
            'resuelto_at' => now(), 'updated_at' => now(),
        ]);
        return response()->json(['mensaje' => 'Acceso denegado']);
    }

    // ── POST /auth/logout · /auth/me — requieren token ────────────────
    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();
        return response()->json(['mensaje' => 'Sesión cerrada correctamente']);
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json([
            'mensaje' => 'Usuario autenticado',
            'info'    => ['user' => $this->datosUsuario($request->user())],
        ]);
    }

    // ── POST /auth/menu — módulos y permisos del rol (desde la BD) ────
    public function menu(Request $request): JsonResponse
    {
        $user  = $request->user();
        $query = DB::table('tbl_seg_modulo AS m')
            ->where('m.activo', 1)->where('m.visible', 1)
            ->orderBy('m.orden')->orderBy('m.titulo');

        if ($user->esAdmin()) {
            $modulos = $query
                ->get(['m.clave', 'm.titulo', 'm.icono', 'm.orden', 'm.tipo'])
                ->map(fn ($m) => (array) $m
                    + ['sel' => 1, 'get' => 1, 'add' => 1, 'upd' => 1, 'del' => 1]);
        } else {
            $modulos = $query
                ->join('tbl_seg_permiso AS p', 'p.modulo_id', '=', 'm.id')
                ->join('tbl_seg_rol AS r', 'r.id', '=', 'p.rol_id')
                ->where('r.nombre', $user->rol)->where('r.activo', 1)
                ->where('p.sel', 1)
                ->get(['m.clave', 'm.titulo', 'm.icono', 'm.orden', 'm.tipo',
                       'p.sel', 'p.get', 'p.add', 'p.upd', 'p.del']);
        }
        return response()->json([
            'mensaje' => 'Menú del usuario',
            'info'    => ['modulos' => $modulos],
        ]);
    }

    // ── POST /auth/2fa/activar — { metodo: app|correo } ───────────────
    public function dosfaActivar(Request $request): JsonResponse
    {
        $request->validate(['metodo' => ['required', 'in:app,correo']]);
        $user = $request->user();

        if ($request->metodo === 'app') {
            $secreto = Totp::generarSecreto();
            $user->forceFill(['totp_secret' => $secreto])->save();
            return response()->json([
                'mensaje' => 'Vincular la app y confirmar con un código',
                'info'    => [
                    'metodo'  => 'app',
                    'secreto' => $secreto,
                    'uri'     => Totp::uri($secreto, $user->email, config('app.name', 'Portal')),
                ],
            ]);
        }
        $this->enviarCodigo($user, 'activacion');
        return response()->json([
            'mensaje' => 'Código de activación enviado al correo',
            'info'    => ['metodo' => 'correo'],
        ]);
    }

    // ── POST /auth/2fa/confirmar — { metodo, codigo } ─────────────────
    public function dosfaConfirmar(Request $request): JsonResponse
    {
        $request->validate([
            'metodo' => ['required', 'in:app,correo'],
            'codigo' => ['required', 'string'],
        ]);
        $user   = $request->user();
        $valido = $request->metodo === 'app'
            ? ($user->totp_secret && Totp::verificar($user->totp_secret, $request->codigo))
            : $this->validarCodigoCorreo($user, $request->codigo, 'activacion');
        if (!$valido) {
            return response()->json(['error' => ['text' => 'Código inválido o vencido']], 401);
        }
        $user->forceFill(['metodo_2fa' => $request->metodo])->save();
        return response()->json([
            'mensaje' => 'Verificación en dos pasos activada',
            'info'    => ['metodo_2fa' => $request->metodo],
        ]);
    }

    // ── POST /auth/2fa/desactivar — { password } ──────────────────────
    public function dosfaDesactivar(Request $request): JsonResponse
    {
        $request->validate(['password' => ['required', 'string']]);
        $user = $request->user();
        if (!Hash::check($request->password, $user->password)) {
            return response()->json(['error' => ['text' => 'Contraseña incorrecta']], 401);
        }
        $user->forceFill(['metodo_2fa' => 'ninguno', 'totp_secret' => null])->save();
        DB::table('tbl_seg_codigo_verificacion')->where('usuario_id', $user->id)->delete();
        return response()->json([
            'mensaje' => 'Verificación en dos pasos desactivada',
            'info'    => ['metodo_2fa' => 'ninguno'],
        ]);
    }
}
