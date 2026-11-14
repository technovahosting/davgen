      {aBaja && (
        <div className="modal modal-open" role="alertdialog" aria-modal="true" aria-labelledby="titulo-baja" aria-describedby="texto-baja"
          onKeyDown={(e) => { if (e.key === 'Escape') setABaja(null) }}>
          <div className="modal-box">
            <h3 id="titulo-baja" className="mb-2 text-lg font-bold">Dar de baja</h3>
            <p id="texto-baja" className="text-base-content/70">
              {TIENE_ACTIVO
                ? 'Es una baja lógica: el registro se desactiva y podrás reactivarlo cuando quieras.'
                : 'La baja la resuelve el procedimiento almacenado (modo D).'}
            </p>
            <div className="modal-action">
              <button className="btn" autoFocus onClick={() => setABaja(null)}>Cancelar</button>
              <button className="btn btn-error" disabled={ocupado} onClick={confirmarBaja}>
                Dar de baja
              </button>
            </div>
          </div>
        </div>
      )}

