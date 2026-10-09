/** A readable temporary password (no 0/O, 1/l/I) that satisfies the API's 8-character minimum. */
export function generatePassword(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = crypto.getRandomValues(new Uint32Array(10));
  const body = Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
  return `${body}@${(bytes[0] % 90) + 10}`;
}
