
    /** Exporta __CN__ a CSV (descarga). Lee la vista __VISTA__ completa. */
    public function exportar(Request $request): \Symfony\Component\HttpFoundation\Response
    {
        $filas    = \Illuminate\Support\Facades\DB::table('__VISTA__')->get();
        $columnas = $filas->isNotEmpty() ? array_keys((array) $filas->first()) : [];
        $handle   = fopen('php://temp', 'r+');
        fputcsv($handle, $columnas);
        foreach ($filas as $fila) {
            fputcsv($handle, (array) $fila);
        }
        rewind($handle);
        $csv = stream_get_contents($handle);
        fclose($handle);
        return response($csv, 200, [
            'Content-Type'        => 'text/csv; charset=UTF-8',
            'Content-Disposition' => 'attachment; filename="__TABLA__.csv"',
        ]);
    }
