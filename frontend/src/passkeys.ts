// Talk to the browser's WebAuthn API with the JSON the server speaks (base64url fields).

export const passkeySupported = () => typeof window !== 'undefined' && 'PublicKeyCredential' in window && !!navigator.credentials

const toBuf = (s: string): ArrayBuffer => {
  const b64 = s.replace(/-/g, '+').replace(/_/g, '/')
  const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4))
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out.buffer
}

const fromBuf = (b: ArrayBuffer | null | undefined): string | null => {
  if (!b) return null
  let s = ''
  new Uint8Array(b).forEach((x) => (s += String.fromCharCode(x)))
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

type JsonOptions = Record<string, any>

const withBuffers = (o: JsonOptions): JsonOptions => {
  const out: JsonOptions = { ...o, challenge: toBuf(o.challenge) }
  if (o.user) out.user = { ...o.user, id: toBuf(o.user.id) }
  for (const k of ['excludeCredentials', 'allowCredentials']) {
    if (Array.isArray(o[k])) out[k] = o[k].map((c: JsonOptions) => ({ ...c, id: toBuf(c.id) }))
  }
  return out
}

/** The credential as plain JSON, the way the server's library reads it. */
const toJSON = (cred: any): JsonOptions => {
  if (typeof cred.toJSON === 'function') return cred.toJSON()
  const r = cred.response
  const response: JsonOptions = { clientDataJSON: fromBuf(r.clientDataJSON) }
  if (r.attestationObject) {
    response.attestationObject = fromBuf(r.attestationObject)
    response.transports = typeof r.getTransports === 'function' ? r.getTransports() : []
  } else {
    response.authenticatorData = fromBuf(r.authenticatorData)
    response.signature = fromBuf(r.signature)
    response.userHandle = fromBuf(r.userHandle)
  }
  return { id: cred.id, rawId: fromBuf(cred.rawId), type: cred.type, authenticatorAttachment: cred.authenticatorAttachment ?? null, clientExtensionResults: cred.getClientExtensionResults?.() ?? {}, response }
}

export async function createPasskey(options: JsonOptions): Promise<JsonOptions> {
  const cred = await navigator.credentials.create({ publicKey: withBuffers(options) as PublicKeyCredentialCreationOptions })
  if (!cred) throw new Error('The browser returned no key.')
  return toJSON(cred)
}

export async function getPasskey(options: JsonOptions): Promise<JsonOptions> {
  const cred = await navigator.credentials.get({ publicKey: withBuffers(options) as PublicKeyCredentialRequestOptions })
  if (!cred) throw new Error('The browser returned no key.')
  return toJSON(cred)
}

/** Plain words for the browser's errors. */
export const passkeyProblem = (err: unknown): string => {
  const e = err as { name?: string; message?: string }
  switch (e?.name) {
    case 'NotAllowedError':
      return 'The key did not respond, or you cancelled. Plug it in or hold it to the phone and try again.'
    case 'InvalidStateError':
      return 'This key is already registered here.'
    case 'SecurityError':
      return 'Passkeys need https and a real hostname (not an IP address). Open the back office by its name.'
    case 'NotSupportedError':
      return 'This browser or key does not support passkeys.'
    default:
      return e?.message || 'Something went wrong with the key.'
  }
}
