// useAuth() — login (con paso 2FA), verificación y logout sobre el cliente
// ./services/api. Guarda token+usuario en localStorage (sesion).
import { useCallback, useState } from 'react'
import { post, sesion } from '../services/api'

export function useAuth() {
  const [usuario, setUsuario] = useState(sesion.usuario())
  const [error, setError] = useState('')

  const login = useCallback(async (email, password) => {
    setError('')
    try {
      const { info } = await post('/auth/login', { email, password })
      if (info.requiere_2fa) return { requiere2fa: true, metodo: info.metodo }
      sesion.guardar(info.token, info.user)
      setUsuario(info.user)
      return { ok: true }
    } catch (e) {
      setError(e.message)
      return { error: e.message }
    }
  }, [])

  const verificar2fa = useCallback(async (email, password, codigo) => {
    setError('')
    try {
      const { info } = await post('/auth/verificar', { email, password, codigo })
      sesion.guardar(info.token, info.user)
      setUsuario(info.user)
      return { ok: true }
    } catch (e) {
      setError(e.message)
      return { error: e.message }
    }
  }, [])

  const logout = useCallback(async () => {
    try { await post('/auth/logout') } catch { /* sesión ya inválida */ }
    sesion.limpiar()
    setUsuario(null)
  }, [])

  return { usuario, autenticado: Boolean(usuario), error, login, verificar2fa, logout }
}
