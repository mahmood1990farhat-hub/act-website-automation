import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const input = searchParams.get("input");
  const language = searchParams.get("language")||'en'
  const radius = searchParams.get("radius");
  const strictbounds = searchParams.get("strictbounds");
  const loc = searchParams.get("loc");
  const res = await fetch(
    `https://maps.googleapis.com/maps/api/place/autocomplete/json?input=${input}&language=${language}&location=${loc}&radius=${radius}&strictbounds=${strictbounds}&key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}`
  );

  const data = await res.json();

  return NextResponse.json(data);
}
