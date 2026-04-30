
import { extract_error } from "./errorApi";

type PostOptions = {
  endpoint: string;
  token?: string;
  body?: Record<string, any>;
  queryParams?: Record<string, string>;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export const patchData = async <T>({
  endpoint,
  body,
  token,
  queryParams,
  isFormData = false,
}: {
  endpoint: string;
  body: any;
  token?: string;
  queryParams?: Record<string, any>;
  isFormData?: boolean;
}): Promise<T> => {
  const headers: Record<string, string> = {};
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const queryString = queryParams
    ? `?${new URLSearchParams(queryParams).toString()}`
    : '';

  try {
    const response = await fetch(`${BASE_URL}${endpoint}${queryString}`, {
      method: 'PATCH',
      headers,
      body: isFormData ? body : JSON.stringify(body),
    });

    if (!response.ok) {
      // Handle 401 Unauthorized - token expired
      if (response.status === 401) {
        if (typeof window !== "undefined") {
          const pathname = window.location.pathname;
          if (pathname.includes("/dashboard")) {
            const locale = pathname.split("/")[1] || "en";
            document.cookie = "userToken=; path=/; max-age=0";
            document.cookie = "account_type=; path=/; max-age=0";
            document.cookie = "user_id=; path=/; max-age=0";
            window.location.href = `/${locale}/admin/login`;
            throw new Error("Token expired - redirecting to login");
          }
        }
      }
      let err: any;
      try {
        err = await response.json();
      } catch {
        err = { message: await response.text() };
      }
      throw err;
    }

    return response.json();
  } catch (error) {
    console.error("Error patching data:", error);
    throw error;
  }
};