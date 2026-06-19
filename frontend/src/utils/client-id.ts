function randomHex(bytes: Uint8Array): string {
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
}

function getCrypto(): Crypto {
  if (!globalThis.crypto?.getRandomValues) {
    throw new Error('crypto.getRandomValues is required to create client IDs')
  }

  return globalThis.crypto
}

export function createClientId(): string {
  const bytes = new Uint8Array(16)
  getCrypto().getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80

  const hex = randomHex(bytes)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
