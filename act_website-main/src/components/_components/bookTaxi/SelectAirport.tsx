import React, { useState, useEffect, useRef } from "react";
import { Locale } from "../../../../i18n.config";
import { IoIosAirplane } from "react-icons/io";
import { useQuery } from "@tanstack/react-query";
import { fetchData } from "@/lib/api/fetchData";

type typeProps = {
  setValue: (data: any) => void;
  value: string;
  locale: Locale;
};

// const data = [
//   { id: 1, name_en: "airport 1", name_ar: "مطار 1" },
//   { id: 2, name_en: "airport 2", name_ar: "مطار 2" },
//   { id: 3, name_en: "airport 3", name_ar: "مطار 3" },
// ];

export default function SelectAirport({ setValue, value, locale }: typeProps) {
  const [showOptions, setShowOptions] = useState(false);
  const [inputValue, setInputValue] = useState(value);

  const containerRef = useRef<HTMLDivElement>(null);
  const [filteredAirports, setFilteredAirports] = useState<
    {
      id: number;
      name_en: string;
      name_ar: string;
    }[]
  >([]);




  const { data ,isLoading ,isError} = useQuery<
    {
      id: number;
      name_en: string;
      name_ar: string;
    }[]
  >({
    queryKey: ["airport"],
    queryFn: () => fetchData({ endpoint: "/api/trips/list-airports/" }),
  });






  useEffect(() => {
    if (data) {
      setFilteredAirports(data);
    }
  }, [data]);
  useEffect(() => {
  if (!inputValue) {
    if (data) setFilteredAirports(data);
    return;
  }

  if (data) {
    const filtered = data.filter((airport) =>
      airport[`name_${locale}`].toLowerCase().includes(inputValue.toLowerCase())
    );
    setFilteredAirports(filtered);
  }
}, [inputValue, locale, data]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setShowOptions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVal = e.target.value;
    setInputValue(newVal);
    setValue({ id: null, description: newVal });
    setShowOptions(true);
  };

  const handleSelect = (airport: (typeof filteredAirports)[0]) => {
    setInputValue(airport[`name_${locale}`]);
    setValue({
      id: airport.id,
      description: airport[`name_${locale}`],
    });
    setShowOptions(false);
  };

  if (isError) {
    return <div>error</div>
  }
  return (
    <div ref={containerRef} className="relative w-full">
      <input
        type="text"
        value={inputValue}
        className="w-full p-3 border-2 bg-white text-foreground font-semibold border-muted rounded-lg"
        onChange={handleChange}
        onClick={() => setShowOptions(true)}
        autoComplete="off"
      />

      {showOptions && filteredAirports.length > 0 && (
        <ul className="absolute z-10 w-full bg-white border border-muted rounded-md shadow-md max-h-60 overflow-auto  text-foreground font-semibold">
          {filteredAirports.map((airport) => (
            <li
              key={airport.id}
              onClick={() => handleSelect(airport)}
              className="flex items-center gap-2 px-4 py-3  border-b border-muted-foreground cursor-pointer rounded  duration-200 hover:bg-primary/20"
            >
              <IoIosAirplane className="text-primary text-2xl" />
              {airport[`name_${locale}`]}
            </li>
          ))}
        </ul>
      )}

      {showOptions && filteredAirports.length === 0 && (
        <div className="absolute z-10 w-full bg-foreground border border-muted rounded-md shadow-md p-4 text-center  text-muted">
There are no airports
        </div>
      )}
    </div>
  );
}
