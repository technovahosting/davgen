<?php
// descomprimir.php — GENERADO por davgen. Extrae servicio.zip en su carpeta
// y luego se elimina (junto al zip). Proteger con token en la URL.
if (!hash_equals('{token}', (string) ($_GET['token'] ?? ''))) { http_response_code(403); exit('token'); }
$dir = __DIR__;
$zip = new ZipArchive();
if ($zip->open("$dir/servicio.zip") !== true) { http_response_code(500); exit('no zip'); }
$zip->extractTo($dir);
$zip->close();
@unlink("$dir/servicio.zip");
echo "OK: " . date('c');
@unlink(__FILE__);
