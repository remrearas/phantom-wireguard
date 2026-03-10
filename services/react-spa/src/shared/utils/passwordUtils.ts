const PASSWORD_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*_+-=';
const PASSWORD_PATTERN =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:'",.<>?/`~\\]).{8,256}$/;

export function generatePassword(length = 16): string {
  const lower = 'abcdefghijklmnopqrstuvwxyz';
  const upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const digits = '0123456789';
  const special = '!@#$%^&*_+-=';

  const pick = (chars: string) => chars[crypto.getRandomValues(new Uint8Array(1))[0] % chars.length];

  // Guarantee one from each required category
  const required = [pick(lower), pick(upper), pick(digits), pick(special)];

  // Fill remaining slots from the full character set
  const remaining = new Uint8Array(length - required.length);
  crypto.getRandomValues(remaining);
  for (const byte of remaining) required.push(PASSWORD_CHARS[byte % PASSWORD_CHARS.length]);

  // Shuffle with Fisher-Yates to avoid predictable positions
  const arr = required;
  for (let i = arr.length - 1; i > 0; i--) {
    const j = crypto.getRandomValues(new Uint8Array(1))[0] % (i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }

  return arr.join('');
}

export function isPasswordValid(password: string): boolean {
  return PASSWORD_PATTERN.test(password);
}

export interface PolicyCheck {
  key: string;
  label: string;
  test: (pw: string) => boolean;
}

export function getPolicyChecks(labels: {
  minLength: string;
  uppercase: string;
  lowercase: string;
  digit: string;
  special: string;
}): PolicyCheck[] {
  return [
    { key: 'minLength', label: labels.minLength, test: (pw) => pw.length >= 8 },
    { key: 'uppercase', label: labels.uppercase, test: (pw) => /[A-Z]/.test(pw) },
    { key: 'lowercase', label: labels.lowercase, test: (pw) => /[a-z]/.test(pw) },
    { key: 'digit', label: labels.digit, test: (pw) => /\d/.test(pw) },
    {
      key: 'special',
      label: labels.special,
      test: (pw) => /[!@#$%^&*()_+\-=\[\]{}|;:'",.<>?/`~\\]/.test(pw),
    },
  ];
}
