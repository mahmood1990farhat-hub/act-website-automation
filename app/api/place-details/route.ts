import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const place_id = searchParams.get("place_id");

  if (!place_id) {
    console.log("here1")
    return NextResponse.json({ error: "Missing place_id" }, { status: 400 });
  }
  try {
    const apiUrl = `https://maps.googleapis.com/maps/api/place/details/json?place_id=${place_id}&key=${process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}`;
    const res = await fetch(apiUrl);
    const data = await res.json();
    console.log("here1")

    console.log(apiUrl)
    console.log(res)
    return NextResponse.json(data);
  } catch (error) {
    console.log("ss")
    console.log(error)
    return NextResponse.json(
      { message: "Failed to fetch place details", error },
      { status: 500 }
    );
  }
}
