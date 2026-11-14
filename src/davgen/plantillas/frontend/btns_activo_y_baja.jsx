
                          {!r.activo ? (
                            <button className="btn btn-ghost btn-sm join-item text-success" aria-label={`Reactivar ${TITULO} ${r[PK]}`} onClick={() => reactivar(r)}>
                              Reactivar
                            </button>
                          ) : (
                            <button className="btn btn-ghost btn-sm join-item text-error" aria-label={`Dar de baja ${TITULO} ${r[PK]}`} onClick={() => setABaja(r)}>
                              Dar de baja
                            </button>
                          )}