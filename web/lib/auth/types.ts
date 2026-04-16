export const SESSION_COOKIE_NAME = "noveland_session";
export const CSRF_COOKIE_NAME = "noveland_csrf";
export const CSRF_HEADER_NAME = "X-CSRF-Token";

export type AuthSubject = {
  user_id: string;
  email: string;
  display_name: string;
  roles: string[];
};

export type CsrfResponse = {
  csrf_token: string;
};

export type LoginInput = {
  email: string;
  password: string;
};
