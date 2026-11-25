"use client";
import { customerText } from "@/lib/customer-text";
import { useEffect, useLayoutEffect, useState, useRef } from "react";
import { Locale } from "../../../../i18n.config";
import { PiMapPinLineFill } from "react-icons/pi";
import { toast } from "react-toastify";

export type PlaceSuggestion = {
  description: string;
  matched_substrings: { length: number; offset: number; }[];
  place_id: string;
  reference: string;
  coordinates?: { lat: number; lng: number; };
};

// London bounds for geographic restriction
const LONDON_BOUNDS = {
  northeast: { lat: 51.691874, lng: 0.3340155 },
  southwest: { lat: 51.28676, lng: -0.5103751 }
};

// UK bounds for geographic restriction
const UK_BOUNDS = {
  northeast: { lat: 60.856553, lng: 1.768960 },
  southwest: { lat: 49.162090, lng: -13.413930 }
};

const fetchPlaceDetails = async (placeId: string, signal: AbortSignal) => {
  const res = await fetch(`/api/place-details?place_id=${encodeURIComponent(placeId)}`, { signal });
  if (!res.ok) throw new Error("Failed to fetch place details");
  const data = await res.json();
  return data.result?.geometry?.location;
};

const hasValidCoordinates = (coordinates?: { lat: number; lng: number }) => {
  if (!coordinates) return false;

  return (
    Number.isFinite(coordinates.lat) &&
    Number.isFinite(coordinates.lng) &&
    !(coordinates.lat === 0 && coordinates.lng === 0)
  );
};

const emptyPlaceSuggestion: PlaceSuggestion = {
  description: "",
  place_id: "",
  matched_substrings: [],
  reference: "",
  coordinates: { lat: 0, lng: 0 },
};

const isInLondon = (coordinates: { lat: number; lng: number }) => {
  return (
    coordinates.lat >= LONDON_BOUNDS.southwest.lat &&
    coordinates.lat <= LONDON_BOUNDS.northeast.lat &&
    coordinates.lng >= LONDON_BOUNDS.southwest.lng &&
    coordinates.lng <= LONDON_BOUNDS.northeast.lng
  );
};

const isInUK = (coordinates: { lat: number; lng: number }) => {
  return (
    coordinates.lat >= UK_BOUNDS.southwest.lat &&
    coordinates.lat <= UK_BOUNDS.northeast.lat &&
    coordinates.lng >= UK_BOUNDS.southwest.lng &&
    coordinates.lng <= UK_BOUNDS.northeast.lng
  );
};

const isLondonRelated = (description: string) => {
  const londonKeywords = ["london", "uk", "england", "united kingdom"];
  const lowerDescription = description.toLowerCase();
  return londonKeywords.some((keyword) => lowerDescription.includes(keyword));
};

// Some key airports sit just outside the formal London bounds but should still be
// allowed for pickup (London-area airports).
const PICKUP_EXCEPTION_KEYWORDS = [
  "london gatwick airport",
  "gatwick airport",
  "london luton airport",
  "luton airport",
  "london stansted airport",
  "stansted airport",
    "guildford",
  "windsor",
  "slough",
  "woking",
  "bagshot",
];

const isPickupExceptionLocation = (description: string) => {
  const lower = description.toLowerCase();
  return PICKUP_EXCEPTION_KEYWORDS.some((k) => lower.includes(k));
};

const isUKRelated = (description: string) => {
  const ukKeywords = [
    "uk",
    "united kingdom",
    "england",
    "scotland",
    "wales",
    "northern ireland",
    "london",
    "manchester",
    "birmingham",
    "leeds",
    "glasgow",
    "liverpool",
    "edinburgh",
    "bristol",
    "cardiff",
    "belfast",
    "newcastle",
    "nottingham",
    "sheffield",
    "brighton",
    "plymouth",
    "southampton",
    "portsmouth",
    "leicester",
    "coventry",
    "hull",
    "bradford",
    "exeter",
    "oxford",
    "cambridge",
    "york",
    "bath",
    "chester",
    "canterbury",
    "durham",
    "lancashire",
    "yorkshire",
    "surrey",
    "kent",
    "essex",
    "hampshire",
    "devon",
    "cornwall",
    "dorset",
    "somerset",
    "gloucestershire",
    "hertfordshire",
    "buckinghamshire",
    "berkshire",
    "oxfordshire",
    "warwickshire",
    "staffordshire",
    "derbyshire",
    "nottinghamshire",
    "leicestershire",
    "lincolnshire",
    "norfolk",
    "suffolk",
    "cambridgeshire",
    "bedfordshire",
    "northamptonshire",
    "rutland",
    "cheshire",
    "shropshire",
    "herefordshire",
    "worcestershire",
    "west midlands",
    "east midlands",
    "north west",
    "north east",
    "south west",
    "south east",
    "greater london",

  ];
  const lowerDescription = description.toLowerCase();
  return ukKeywords.some((keyword) => lowerDescription.includes(keyword));
};

export default function LocationSelector({
  value = "",
  selectedPlace,
  setValue,
  locale,
  locationType
}: {
  value?: string;
  selectedPlace: PlaceSuggestion | null;
  setValue: (data: PlaceSuggestion, expectedPlace?: PlaceSuggestion) => void;
  locale: Locale;
  locationType: 'pickup' | 'dropoff' | 'stop';
}) {
  const isRTL = locale === 'ar';
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState<PlaceSuggestion[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const commitSelection = useRef(setValue);
  useLayoutEffect(() => { commitSelection.current = setValue; }, [setValue]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const dropdownRef = useRef<HTMLUListElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Determine if we're restricting to London or UK
  const isLondonOnly = locationType === 'pickup';
  const isUKWide = locationType === 'dropoff' || locationType === 'stop';

  useEffect(() => {
    if (selectedPlace?.place_id) {
      setOptions([]);
      setIsSearching(false);
      setError(null);
      return;
    }

    // Clear previous timeout
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    // Abort previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const fetchSuggestions = async () => {
      if (value.length <= 2) {
        setOptions([]);
        setIsSearching(false);
        setError(null);
        return;
      }

      setIsSearching(true);
      setError(null);
      abortControllerRef.current = new AbortController();

      try {
        let apiUrl;
        if (isLondonOnly) {
          // London-focused search with strict bounds
          apiUrl = `/api/places?input=${encodeURIComponent(value)}&language=${'en'}&loc=51.5074,-0.1278&radius=50000&strictbounds=true`;
        } else {
          // UK-wide search with location bias towards UK center and country restriction
          apiUrl = `/api/places?input=${encodeURIComponent(value)}&language=${'en'}&loc=54.7023545,-3.2765753&radius=500000&components=country:gb`;
        }

        const res = await fetch(apiUrl, {
          signal: abortControllerRef.current.signal,
        });
        const data = await res.json();

        if (data.status === "OK") {
          let filteredResults;
          if (isLondonOnly) {
            // Filter results to only show London-related places, plus key London-area airports
            filteredResults = data.predictions.filter(
              (pred: any) =>
                isLondonRelated(pred.description) ||
                isPickupExceptionLocation(pred.description)
            );
          } else {
            // Filter results to only show UK-related places
            filteredResults = data.predictions.filter((pred: any) =>
              isUKRelated(pred.description)
            );
          }

          if (filteredResults.length === 0) {
            const errorMessage = isLondonOnly
              ? (isRTL
                ? "لم يتم العثور على أي مواقع في لندن. يُرجى البحث عن مواقع داخل لندن فقط."
                : customerText(locale, "No locations found in London. Please search for locations within London only."))
              : (isRTL
                ? "لم يتم العثور على أي مواقع في المملكة المتحدة. يُرجى البحث عن مواقع داخل المملكة المتحدة فقط."
                : customerText(locale, "No locations found in the UK. Please search for locations within the UK only."));
            setError(errorMessage);
            setOptions([]);
          } else {
            setOptions(filteredResults);
          }
        } else if (data.status === "ZERO_RESULTS") {
          const errorMessage = isLondonOnly
            ? (isRTL
              ? "لم يتم العثور على أي مواقع في لندن. يُرجى استخدام مصطلح بحث آخر."
              : customerText(locale, "No locations found in London. Please try a different search term."))
            : (isRTL
              ? "لم يتم العثور على أي مواقع في المملكة المتحدة. يُرجى استخدام مصطلح بحث آخر."
              : customerText(locale, "No locations found in the UK. Please try a different search term."));
          setError(errorMessage);
          setOptions([]);
        } else {
          setError(`Search failed: ${data.status}`);
          setOptions([]);
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(
            isRTL
              ? "تعذر البحث عن المواقع. يُرجى المحاولة مرة أخرى."
              : customerText(locale, "Unable to search for locations. Please try again.")
          );
          console.error("Fetching suggestions failed:", err);
        }
      } finally {
        setIsSearching(false);
      }
    };

    // Debounce the search by 300ms
    debounceTimeoutRef.current = setTimeout(fetchSuggestions, 300);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [value, selectedPlace?.place_id, locale, locationType, isLondonOnly]);

  const handleLocationSelect = (location: PlaceSuggestion) => {
    setValue({ ...location, coordinates: undefined });
    setShowOptions(false);
  };

  // The selected object belongs to this field. Moving it to another field starts
  // validation there, and an old response cannot overwrite newer input.
  useEffect(() => {
    if (!selectedPlace?.place_id || hasValidCoordinates(selectedPlace.coordinates)) return;
    const controller = new AbortController();
    async function resolvePlace(selection: PlaceSuggestion) {
      try {
        const coordinates = await fetchPlaceDetails(selection.place_id, controller.signal);
        if (controller.signal.aborted) return;
        if (!hasValidCoordinates(coordinates)) throw new Error("Missing place coordinates");
        const valid = isLondonOnly
          ? isInLondon(coordinates) || isPickupExceptionLocation(selection.description)
          : isInUK(coordinates);
        if (valid) {
          commitSelection.current({ ...selection, coordinates }, selection);
        } else {
          const message = isLondonOnly
            ? (isRTL ? "الموقع المختار خارج لندن. يُرجى اختيار موقع داخل لندن فقط." : customerText(locale, "Selected location is outside London. Please choose a location within London only."))
            : (isRTL ? "الموقع المختار خارج المملكة المتحدة. يُرجى اختيار موقع داخل المملكة المتحدة فقط." : customerText(locale, "Selected location is outside the UK. Please choose a location within the UK only."));
          toast.error(message);
          commitSelection.current(emptyPlaceSuggestion, selection);
        }
      } catch {
        if (controller.signal.aborted) return;
        toast.error(isRTL ? "تعذّر الحصول على تفاصيل الموقع. يُرجى محاولة التحديد مرة أخرى." : customerText(locale, "Failed to get location details. Please try selecting again."));
        commitSelection.current(emptyPlaceSuggestion, selection);
      }
    }
    void resolvePlace(selectedPlace);
    return () => controller.abort();
  }, [selectedPlace, locale, isRTL, isLondonOnly]);

  const handleInputChange = (inputValue: string) => {
    setValue({
      description: inputValue,
      place_id: "",
      matched_substrings: [],
      reference: "",
      coordinates: { lat: 0, lng: 0 },
    });
    setOptions([]);
    setShowOptions(true);
    setError(null);
  };

  const showLoadingState = isSearching && value.length > 2;
  const showErrorState = error && !isSearching;
  const showOptionsState = showOptions && options.length > 0 && !isSearching;

  // Dynamic placeholder and restriction notice text
  const placeholderText = isLondonOnly
    ? (isRTL ? 'ابحث عن موقع في لندن...' : customerText(locale, "Search for a location in London..."))
    : (isRTL ? 'ابحث عن موقع في المملكة المتحدة...' : customerText(locale, "Search for a location in the UK..."));

  const restrictionNotice = isLondonOnly
    ? (isRTL ? 'البحث مقتصر على مواقع لندن فقط' : customerText(locale, "Search limited to London locations only"))
    : (isRTL ? 'البحث مقتصر على مواقع المملكة المتحدة فقط' : customerText(locale, "Search limited to UK locations only"));

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    // Check if the focus is moving to the dropdown
    const relatedTarget = e.relatedTarget as HTMLElement;
    if (dropdownRef.current && dropdownRef.current.contains(relatedTarget)) {
      return; // Don't close if clicking inside dropdown
    }
    // Delay closing to allow click events to fire
    setTimeout(() => {
      setShowOptions(false);
    }, 200);
  };

  return (
    <div className="relative w-full">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => handleInputChange(e.target.value)}
        onFocus={() => setShowOptions(true)}
        onBlur={handleBlur}
        className="w-full p-3 border-2 bg-white text-foreground font-semibold border-muted rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all duration-200 placeholder:text-gray-400"
        placeholder={placeholderText}
      />

      {/* Loading State */}
      {showLoadingState && (
        <div className="absolute z-10 w-full bg-white border border-muted rounded-md shadow-md mt-1 flex items-center p-4 gap-4">
          <div className="flex animate-pulse flex-col space-y-3 w-full">
            <div className="h-4 bg-gray-300 rounded w-3/4" />
            <div className="h-4 bg-gray-300 rounded w-1/2" />
          </div>
        </div>
      )}

      {/* Error State */}
      {showErrorState && (
        <div className="absolute z-10 w-full bg-white border border-red-200 rounded-md shadow-md mt-1 font-semibold text-slate-800 p-3 text-sm">
          {error}
        </div>
      )}

      {/* Options List */}
      {showOptionsState && (
        <ul 
          ref={dropdownRef}
          className="absolute z-10 w-full border border-muted rounded-md shadow-lg mt-1 bg-white max-h-60 overflow-y-auto"
          onMouseDown={(e) => e.preventDefault()} // Prevent input blur when clicking dropdown
        >
          {options.map((location, index) => (
            <li
              key={`${location.place_id}-${index}`}
              onMouseDown={(e) => {
                e.preventDefault();
                handleLocationSelect(location);
              }}
              className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 last:border-b-0 cursor-pointer transition-colors duration-150 hover:bg-primary/5 hover:text-primary"
            >
              <PiMapPinLineFill className="text-primary flex-shrink-0" />
              <span className="text-sm font-medium text-gray-800 hover:text-primary transition-colors">
                {location.description}
              </span>
            </li>
          ))}

          {/* Geographic restriction notice */}
          <li className="px-4 py-2 text-xs text-gray-500 bg-gray-50 border-t">
            <span className="flex items-center gap-1">
              {restrictionNotice}
            </span>
          </li>
        </ul>
      )}
    </div>
  );
}

