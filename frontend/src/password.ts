export function passwordStrengthError(password: string): string | null {
  if (password.length < 12) return "Mật khẩu phải có ít nhất 12 ký tự.";

  const characterGroups = [
    /[a-z]/.test(password),
    /[A-Z]/.test(password),
    /\d/.test(password),
    /[^\p{L}\p{N}]/u.test(password),
  ];
  if (characterGroups.filter(Boolean).length < 3) {
    return "Mật khẩu phải dùng ít nhất 3 nhóm: chữ thường, chữ hoa, số và ký tự đặc biệt.";
  }
  return null;
}
