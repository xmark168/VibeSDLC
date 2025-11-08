export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface AuthUser {
  _id: string;
  name: string;
  email: string;
}

export interface AuthResponse {
  user: AuthUser;
  token: string;
}
