    protected function setUp(): void
    {
        parent::setUp();
        // reinicia los contadores de rate-limit (CACHE_STORE) entre pruebas
        \Illuminate\Support\Facades\Cache::flush();
        // estas pruebas necesitan la BD real (MySQL con tbl_seg_*); si el
        // entorno de test no la tiene (p. ej. sqlite :memory: por defecto),
        // se omiten en vez de fallar. Para ejecutarlas: apuntar phpunit.xml /
        // las variables DB_* a una BD MySQL con el esquema (ver LEEME.md).
        try {
            \Illuminate\Support\Facades\DB::table('tbl_seg_parametro')->limit(1)->get();
        } catch (\Throwable $e) {
            $this->markTestSkipped('Requiere BD MySQL con tbl_seg_* (ver LEEME.md).');
        }
    }
