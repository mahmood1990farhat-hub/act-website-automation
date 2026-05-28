import { NextRequest, NextResponse } from "next/server";
import { i18n, languageType } from "../i18n.config";
import { match as matchLocale } from "@formatjs/intl-localematcher";
import Negotiator from "negotiator";

function getLocale(request: NextRequest): string | undefined {
  const negotiatorHeaders: Record<string, string> = {};
  request.headers.forEach((value, key) => (negotiatorHeaders[key] = value));

  const locales: languageType[] = i18n.locales;
  const languages = new Negotiator({ headers: negotiatorHeaders }).languages();
  let locale = "";

  try {
    locale = matchLocale(languages, locales, i18n.defaultLocale);
  } catch (error: any) {
    console.error(error.message);
    locale = i18n.defaultLocale;
  }

  return locale;
}

export function middleware(request: NextRequest) {
  const requestHeader = new Headers(request.headers);
  requestHeader.set("x-url", request.url);
  const locale = getLocale(request);
  const protectedRoutes = ["my-trips", "driver", "dashboard"];

  const pathname = request.nextUrl.pathname;

  const token = request.cookies.get("userToken")?.value;
  const accountType = request.cookies.get("account_type")?.value;
  const isAdminVerified = request.cookies.get("is_admin_verified")?.value === "true";
  const splitPathname = pathname.split("/");
  const isAuth = splitPathname.some((path) => protectedRoutes.includes(path));
  const isDashboard = splitPathname.includes("dashboard");
  const isDriver = splitPathname.includes("driver");
  const isMyTrips = splitPathname.includes("my-trips");
  const isAdminLogin = splitPathname.includes("admin") && splitPathname.includes("login");
  const isHomePage = pathname === `/${locale}` || pathname === `/${locale}/`;
  const pathnameIsMissingLocale = i18n.locales.every(
    (locale) => !pathname.startsWith(`/${locale}`)
  );

  // Always allow access to admin login page (for logout/re-login)
  if (isAdminLogin) {
    return NextResponse.next();
  }

  // Redirect to auth if accessing protected routes without token
  if (isAuth && !token) {
    return NextResponse.redirect(new URL(`/${locale}/auth`, request.url));
  }

  // STRICT ROUTE ISOLATION - Each account type can only access their designated sections
  
  // For "normal" accounts (dashboard users) - can ONLY access dashboard routes
  if (token && accountType === "normal") {
    // Block access to driver routes
    if (isDriver) {
      return NextResponse.redirect(new URL(`/${locale}/dashboard/overview`, request.url));
    }
    // Admins should stay in dashboard only (block site)
    // If it's a dashboard route and not blocked, allow it
    if (isDashboard && !isHomePage && !isMyTrips) {
      // Allow dashboard access
      return NextResponse.next();
    }
    // Redirect to dashboard if trying to access non-dashboard routes
    if (!isDashboard || isHomePage || isMyTrips) {
      return NextResponse.redirect(new URL(`/${locale}/dashboard/overview`, request.url));
    }
  }

  // For "normal_driver" accounts - check verification status
  if (token && accountType === "normal_driver") {
    // Block access to dashboard routes
    if (isDashboard) {
      return NextResponse.redirect(new URL(`/${locale}`, request.url));
    }
    
    // Allow access to upload-documents route for unverified drivers (needs modification)
    // This check MUST come before the isAdminVerified check
    // Note: upload-documents is now in site section, not driver section
    const isUploadDocuments = pathname.includes("upload-documents");
    
    // Debug logging (remove after fixing)
    if (isUploadDocuments) {
      console.log("🔍 Middleware: upload-documents route detected", {
        pathname,
        isDriver,
        isAdminVerified,
        token: !!token,
        accountType
      });
    }
    
    // Allow upload-documents for drivers (it's in site section now, so isDriver won't be true)
    if (isUploadDocuments && accountType === "normal_driver") {
      console.log("✅ Middleware: Allowing access to upload-documents");
      const response = NextResponse.next();
      response.headers.set("x-url", request.url);
      response.headers.set("x-pathname", pathname);
      return response;
    }
    
    if (isAdminVerified) {
      // Verified drivers - can ONLY access driver routes
      // Block access to home page and my-trips (passenger routes)
      if (isHomePage || isMyTrips) {
        return NextResponse.redirect(new URL(`/${locale}`, request.url));
      }
      // Allow driver access
      if (isDriver) {
        return NextResponse.next();
      }
    } else {
      // Unverified drivers - can ONLY access site routes (like passengers)
      // Block access to driver routes (except upload-documents which is handled above)
      if (isDriver) {
        console.log("❌ Middleware: Blocking driver route for unverified driver", { pathname });
        return NextResponse.redirect(new URL(`/${locale}`, request.url));
      }
      // Allow site access (home, my-trips, etc.)
      return NextResponse.next();
    }
  }

  // For passengers (no account_type or other types) - can ONLY access site routes
  if (token && (!accountType || (accountType !== "normal" && accountType !== "normal_driver"))) {
    // Block access to dashboard routes
    if (isDashboard) {
      return NextResponse.redirect(new URL(`/${locale}`, request.url));
    }
    // Block access to driver routes
    if (isDriver) {
      return NextResponse.redirect(new URL(`/${locale}`, request.url));
    }
    // Allow site access (home, my-trips, etc.)
    return NextResponse.next();
  }

  // if (token && isAuth) {
  //   return NextResponse.redirect(new URL(`/${locale}`));
  // }

  // if (isAuth && accountType === "normal_driver") {
  //   return NextResponse.redirect(new URL(`/${locale}/driver`, request.url));
  // }

    if (pathname.endsWith('.html')) {
    return NextResponse.next();
  }
  
  if (pathnameIsMissingLocale) {
    return NextResponse.redirect(new URL(`/${locale}${pathname}`, request.url));
  }

  // Create response with headers
  const response = NextResponse.next();
  response.headers.set("x-url", request.url);
  response.headers.set("x-pathname", pathname);
  return response;
}

export const config = {
  matcher: [
    '/((?!api|_next|.*\\..*|.*\\.html$).*)',
  ],
}
