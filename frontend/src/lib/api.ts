const SESSION_KEY = "vads.demo.username";

export interface CurrentUser {
  id: string;
  commune_id: string;
  username: string;
  email: string;
  full_name: string;
  position: string | null;
  department: string | null;
  role: "ADMIN" | "USER";
  is_active: boolean;
  must_change_password: boolean;
}

type DemoAccount = CurrentUser & { passwordHash: string };

// Demo-only SHA-256 hashes. No plaintext password is stored in the account data.
const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    id: "demo-user",
    commune_id: "demo-commune",
    username: "user.test",
    email: "user.test@vads.local",
    full_name: "Người dùng kiểm thử",
    position: "Chuyên viên",
    department: "VADS",
    role: "USER",
    is_active: true,
    must_change_password: false,
    passwordHash: "30fc67291cb56e9c069c0d415475b88f62abea982492742566fa8195943ad085",
  },
  {
    id: "demo-admin",
    commune_id: "demo-commune",
    username: "admin.test",
    email: "admin.test@vads.local",
    full_name: "Quản trị viên kiểm thử",
    position: "Quản trị viên",
    department: "VADS",
    role: "ADMIN",
    is_active: true,
    must_change_password: false,
    passwordHash: "5e50623bf33bbb50f2e4fecdc9964a93f52e38aca277f5a786486be36b771da6",
  },
];

async function sha256(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function publicUser(account: DemoAccount): CurrentUser {
  const { passwordHash: _passwordHash, ...user } = account;
  return user;
}

export const authApi = {
  hasSession: () => Boolean(sessionStorage.getItem(SESSION_KEY)),
  clear: () => sessionStorage.removeItem(SESSION_KEY),

  async login(identifier: string, password: string): Promise<CurrentUser> {
    const normalized = identifier.trim().toLowerCase();
    const passwordHash = await sha256(password);
    const account = DEMO_ACCOUNTS.find(
      (candidate) =>
        (candidate.username === normalized || candidate.email === normalized) &&
        candidate.passwordHash === passwordHash,
    );
    if (!account) throw new Error("Tài khoản hoặc mật khẩu không đúng.");
    sessionStorage.setItem(SESSION_KEY, account.username);
    return publicUser(account);
  },

  async me(): Promise<CurrentUser> {
    const username = sessionStorage.getItem(SESSION_KEY);
    const account = DEMO_ACCOUNTS.find((candidate) => candidate.username === username);
    if (!account) throw new Error("Phiên đăng nhập không hợp lệ.");
    return publicUser(account);
  },

  async logout(): Promise<void> {
    this.clear();
  },
};
