const PASSWORD_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*_+-=';
const PASSWORD_PATTERN =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:'",.<>?/`~\\]).{8,256}$/;

export function generatePassword(length = 16): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  let pw = '';
  for (const byte of array) pw += PASSWORD_CHARS[byte % PASSWORD_CHARS.length];
  if (!/[a-z]/.test(pw)) pw = pw.slice(0, -1) + 'a';
  if (!/[A-Z]/.test(pw)) pw = pw.slice(0, -1) + 'A';
  if (!/\d/.test(pw)) pw = pw.slice(0, -1) + '1';
  if (!/[!@#$%^&*_+\-=]/.test(pw)) pw = pw.slice(0, -1) + '!';
  return pw;
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
