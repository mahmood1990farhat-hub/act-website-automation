"use client";

import { useState } from "react";

// Convenience suggestions, not a complete catalogue or an eligibility list.
// The explicit not-listed path preserves support for every existing free-text value.
const MODELS: Record<string, readonly string[]> = {
  Audi: ["A3", "A4", "A6", "A8", "Q3", "Q5", "Q7", "Q8"],
  BMW: ["3 Series", "5 Series", "7 Series", "i4", "i5", "i7", "X3", "X5"],
  BYD: ["Atto 3", "Dolphin", "Seal", "Seal U"],
  Citroen: ["C4", "C5 Aircross", "Grand C4 SpaceTourer", "SpaceTourer"],
  Dacia: ["Duster", "Jogger", "Sandero"],
  Ford: ["Focus", "Galaxy", "Kuga", "Mondeo", "S-MAX", "Tourneo Custom"],
  Honda: ["Civic", "CR-V", "HR-V", "Jazz"],
  Hyundai: ["IONIQ", "IONIQ 5", "IONIQ 6", "Kona", "Santa Fe", "Tucson"],
  Jaguar: ["F-PACE", "I-PACE", "XE", "XF", "XJ"],
  Kia: ["Ceed", "EV6", "EV9", "Niro", "Optima", "Sorento", "Sportage"],
  "Land Rover": ["Discovery", "Discovery Sport", "Range Rover", "Range Rover Evoque", "Range Rover Sport"],
  Lexus: ["ES", "IS", "NX", "RX", "UX"],
  Mazda: ["3", "6", "CX-5", "CX-60"],
  "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "EQB", "EQE", "EQS", "EQV", "V-Class", "Vito"],
  MG: ["MG4", "MG5", "HS", "ZS"],
  Nissan: ["Ariya", "Juke", "Leaf", "Qashqai", "X-Trail"],
  Peugeot: ["308", "508", "2008", "3008", "5008", "Traveller"],
  Polestar: ["2", "3", "4"],
  Renault: ["Arkana", "Austral", "Captur", "Megane", "Scenic", "Trafic"],
  SEAT: ["Alhambra", "Ateca", "Leon", "Tarraco"],
  Skoda: ["Enyaq", "Kodiaq", "Octavia", "Superb"],
  Tesla: ["Model 3", "Model S", "Model X", "Model Y"],
  Toyota: ["Avensis", "bZ4X", "C-HR", "Camry", "Corolla", "Prius", "Prius+", "RAV4", "Proace Verso"],
  Vauxhall: ["Astra", "Combo Life", "Grandland", "Insignia", "Vivaro Life"],
  Volkswagen: ["Arteon", "Caddy", "Golf", "ID.3", "ID.4", "ID.5", "ID.7", "ID. Buzz", "Passat", "Sharan", "Tiguan", "Touran", "Transporter"],
  Volvo: ["S60", "S90", "V60", "V90", "XC40", "XC60", "XC90"],
};
const OTHER = "__other__";
export const VEHICLE_OWNERSHIP_LABELS: Record<string, string> = {
  phv_owner: "I own a licensed PHV",
  hiring_a_phv: "I rent / hire / lease a licensed PHV",
  do_not_have_a_phv: "I do not have a vehicle yet",
  other: "Other lawful arrangement",
};
export function vehicleYearOptions(year = new Date().getFullYear()): string[] {
  return Array.from({ length: Math.max(0, year - 2015 + 1) }, (_, i) => String(year - i));
}

type Value = { vehicle_make: string; vehicle_model: string; vehicle_year: string };
type Props = {
  value: Value;
  onChange: (patch: Partial<Value>) => void;
  fieldClass: string;
  labelClass: string;
};

export default function DriverVehicleFields({ value, onChange, fieldClass, labelClass }: Props) {
  const [otherMake, setOtherMake] = useState(!!value.vehicle_make && !Object.hasOwn(MODELS, value.vehicle_make));
  const [otherModel, setOtherModel] = useState(!!value.vehicle_model && !(MODELS[value.vehicle_make] || []).includes(value.vehicle_model));
  const models = MODELS[value.vehicle_make] || [];
  return <>
    <div className="min-w-0 space-y-2">
      <label className={labelClass}>Vehicle make *
        <select className={fieldClass} required value={otherMake ? OTHER : value.vehicle_make}
          onChange={e => {
            const custom = e.target.value === OTHER;
            setOtherMake(custom); setOtherModel(false);
            onChange({ vehicle_make: custom ? "" : e.target.value, vehicle_model: "" });
          }}>
          <option value="">Select make...</option>
          {Object.keys(MODELS).sort().map(make => <option key={make} value={make}>{make}</option>)}
          <option value={OTHER}>Other / make not listed</option>
        </select>
      </label>
      {otherMake && <label className={labelClass}>Enter vehicle make *
        <input className={fieldClass} required maxLength={80} value={value.vehicle_make}
          onChange={e => onChange({ vehicle_make: e.target.value, vehicle_model: "" })} />
      </label>}
    </div>
    <div className="min-w-0 space-y-2">
      {otherMake ? <label className={labelClass}>Enter vehicle model *
        <input className={fieldClass} required maxLength={80} value={value.vehicle_model}
          onChange={e => onChange({ vehicle_model: e.target.value })} />
      </label> : <>
        <label className={labelClass}>Vehicle model *
          <select className={fieldClass} required disabled={!value.vehicle_make}
            value={otherModel ? OTHER : value.vehicle_model}
            onChange={e => {
              const custom = e.target.value === OTHER;
              setOtherModel(custom);
              onChange({ vehicle_model: custom ? "" : e.target.value });
            }}>
            <option value="">{value.vehicle_make ? "Select model..." : "Choose a make first"}</option>
            {models.map(model => <option key={model} value={model}>{model}</option>)}
            <option value={OTHER}>Other / model not listed</option>
          </select>
        </label>
        {otherModel && <label className={labelClass}>Enter vehicle model *
          <input className={fieldClass} required maxLength={80} value={value.vehicle_model}
            onChange={e => onChange({ vehicle_model: e.target.value })} />
        </label>}
      </>}
    </div>
    <label className={labelClass}>Vehicle year (2015–present) *
      <select className={fieldClass} required value={value.vehicle_year}
        onChange={e => onChange({ vehicle_year: e.target.value })}>
        <option value="">Select year...</option>
        {vehicleYearOptions().map(year => <option key={year} value={year}>{year}</option>)}
      </select>
    </label>
    <p className="self-center text-xs leading-5 text-gray-300">Choose the details shown on your vehicle documents. Not listed? Use Other. ACT must still verify the vehicle before approval.</p>
  </>;
}
