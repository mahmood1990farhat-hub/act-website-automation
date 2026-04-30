type FetchOptions = {
  endpoint: string;
  token?: string;
  queryParams?: Record<string, string>;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function deleteData<T>({
  endpoint,
  token,
  queryParams,
}: FetchOptions): Promise<T> {
  try {
    const url = `${BASE_URL}${endpoint}/`;

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const queryString = queryParams
      ? "?" + new URLSearchParams(queryParams).toString()
      : "";

    const finalUrl = `${url}${queryString}`;

    const response = await fetch(finalUrl, {
      method: "DELETE",
      headers,
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
      throw new Error(
        `Failed to fetch data from ${finalUrl}. Status: ${response.status}`
      );
    }

    if (response.status === 204) {
      // 204 No Content => لا يوجد رد JSON
      return null as any;
    }

    // نقرا الرد كنص عشان نتأكد
    const text = await response.text();

    if (!text) {
      // لو الرد فارغ
      return null as any;
    }

    // نحول النص لـ JSON
    const data: T = JSON.parse(text);

    return data;
  } catch (error) {
    console.error("Error fetching data:", error);
    throw error;
  }
}